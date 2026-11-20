#!/bin/bash
# Mise à jour automatique du serveur maison — chaque dimanche à 4 h 30
# (après la sauvegarde du SSD de 3 h).
#  1. copie de sécurité de la configuration Home Assistant sur le disque de secours
#  2. mise à jour du système (paquets Raspberry Pi OS)
#  3. mise à jour de Home Assistant et ESPHome (images Docker)
#  4. vérification que Home Assistant redémarre ; sinon retour à l'ancienne version
#  5. redémarrage du Pi si le système le demande
# Le résultat est écrit dans /srv/homeassistant/config/maj.json (affiché dans Home Assistant).
set -u
CFG=/srv/homeassistant/config
ETAT=$CFG/maj.json
DOSSIER=/opt/serveur-maison
COPIES=/mnt/secours/config-home-assistant
HA_IMG=ghcr.io/home-assistant/home-assistant:stable
journal=()
note(){ journal+=("$1"); echo "$1"; }

ecrire(){  # ecrire <ok|erreur|en_cours> <message>
  python3 - "$ETAT" "$1" "$2" "$(printf '%s\n' "${journal[@]:-}")" <<'PY'
import json, os, sys, time
f, etat, msg, j = sys.argv[1:5]
try: old = json.load(open(f))
except Exception: old = {}
d = {"etat": etat, "message": msg, "maj": int(time.time()), "journal": j.strip().splitlines()[-8:],
     "derniere_reussite": old.get("derniere_reussite", 0), "version_ha": old.get("version_ha", "")}
try: d["version_ha"] = open("/srv/homeassistant/config/.HA_VERSION").read().strip()
except Exception: pass
if etat == "ok": d["derniere_reussite"] = int(time.time())
tmp = f + ".tmp"; json.dump(d, open(tmp, "w")); os.replace(tmp, f)
PY
}

ha_repond(){  # Home Assistant répond-il ? (401 = démarré, juste pas connecté)
  for _ in $(seq 1 36); do
    code=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8123/api/ || true)
    [ "$code" = "401" ] || [ "$code" = "200" ] && return 0
    sleep 10
  done
  return 1
}

ecrire en_cours "Mise à jour en cours…"

# 1. Copie de sécurité de la configuration
if mountpoint -q /mnt/secours; then
  mkdir -p "$COPIES"
  tar --exclude='*.db*' --exclude='*.log*' -czf "$COPIES/config-$(date +%F).tar.gz" -C "$CFG" . \
    && note "Copie de la configuration : OK" || note "Copie de la configuration : ÉCHEC"
  ls -1t "$COPIES"/config-*.tar.gz 2>/dev/null | tail -n +9 | xargs -r rm -f   # garde 8 semaines
else
  note "Disque de secours absent : pas de copie de la configuration"
fi

# 2. Système
export DEBIAN_FRONTEND=noninteractive
if apt-get update -q >/dev/null && apt-get -y -q -o Dpkg::Options::=--force-confold full-upgrade >/tmp/maj-apt.log 2>&1; then
  n=$(grep -c '^Setting up\|^Paramétrage' /tmp/maj-apt.log || true)
  note "Système : à jour ($n paquets mis à jour)"
  apt-get -y -q autoremove >/dev/null 2>&1
else
  note "Système : ÉCHEC de la mise à jour (voir /tmp/maj-apt.log)"
fi

# 3. Home Assistant et ESPHome
ancienne=$(docker image inspect -f '{{.Id}}' "$HA_IMG" 2>/dev/null || true)
cd "$DOSSIER" || { ecrire erreur "Dossier $DOSSIER introuvable"; exit 1; }
if docker compose pull -q; then
  nouvelle=$(docker image inspect -f '{{.Id}}' "$HA_IMG" 2>/dev/null || true)
  docker compose up -d >/dev/null 2>&1
  if [ "$ancienne" != "$nouvelle" ]; then
    note "Home Assistant : nouvelle version installée, vérification…"
    if ha_repond; then
      note "Home Assistant : redémarré correctement"
    else
      note "Home Assistant ne répond pas : retour à l'ancienne version"
      docker tag "$ancienne" "$HA_IMG" && docker compose up -d --force-recreate homeassistant >/dev/null 2>&1
      ha_repond && note "Ancienne version rétablie" || note "ATTENTION : Home Assistant ne répond toujours pas"
      ecrire erreur "Mise à jour annulée : Home Assistant ne redémarrait pas"; exit 1
    fi
  else
    note "Home Assistant : déjà à jour"
  fi
  docker image prune -f >/dev/null 2>&1
else
  note "Home Assistant : téléchargement impossible (Internet ?)"
fi

# 4. Redémarrage si nécessaire
if [ -f /var/run/reboot-required ]; then
  note "Redémarrage du Pi pour terminer la mise à jour"
  ecrire ok "Mise à jour réussie (redémarrage du Pi)"
  sync; sleep 5; systemctl reboot
  exit 0
fi
ecrire ok "Mise à jour réussie"
