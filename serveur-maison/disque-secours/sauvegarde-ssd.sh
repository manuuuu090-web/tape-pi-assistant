#!/bin/bash
# Copie le SSD (/mnt/ssd) sur le disque de secours (/mnt/secours).
# Seuls les fichiers nouveaux ou modifiés sont recopiés.
# Un fichier effacé ou remplacé sur le SSD part d'abord dans la corbeille
# du disque de secours (/mnt/secours/corbeille/<date>) et y reste 30 jours.
set -u
SRC=/mnt/ssd/
DST=/mnt/secours/copie/
CORB=/mnt/secours/corbeille
ETAT=/srv/homeassistant/config/secours.json
JOURS_CORBEILLE=30

ecrire() {  # ecrire <etat> <message> [duree]
  python3 - "$ETAT" "$1" "$2" "${3:-0}" <<'PY'
import json, os, shutil, sys, time
f, etat, msg, duree = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
try:
    old = json.load(open(f))
except Exception:
    old = {}
d = {"etat": etat, "message": msg, "maj": int(time.time()),
     "derniere_reussite": old.get("derniere_reussite", 0), "duree_min": old.get("duree_min", 0),
     "libre_go": None, "utilise_pct": None}
if etat == "ok":
    d["derniere_reussite"] = int(time.time()); d["duree_min"] = round(duree / 60)
if os.path.ismount("/mnt/secours"):
    u = shutil.disk_usage("/mnt/secours")
    d["libre_go"] = round(u.free / 1e9); d["utilise_pct"] = round(u.used * 100 / u.total)
tmp = f + ".tmp"; json.dump(d, open(tmp, "w")); os.replace(tmp, f)
PY
}

debut=$(date +%s)
mountpoint -q /mnt/secours || mount /mnt/secours 2>/dev/null
if ! mountpoint -q /mnt/secours; then ecrire erreur "Disque de secours absent ou débranché"; exit 1; fi
if ! mountpoint -q /mnt/ssd; then ecrire erreur "SSD principal absent : sauvegarde annulée"; exit 1; fi
if [ -z "$(ls -A /mnt/ssd 2>/dev/null)" ]; then ecrire erreur "SSD principal vide : sauvegarde annulée par sécurité"; exit 1; fi

ecrire en_cours "Sauvegarde en cours…"
mkdir -p "$DST" "$CORB"
nice -n 10 ionice -c3 rsync -a --delete --backup --backup-dir="$CORB/$(date +%F_%Hh%M)" \
  --exclude='$RECYCLE.BIN' --exclude='System Volume Information' "$SRC" "$DST"
rc=$?
find "$CORB" -mindepth 1 -maxdepth 1 -type d -mtime +$JOURS_CORBEILLE -exec rm -rf {} +
duree=$(( $(date +%s) - debut ))
case $rc in
  0|24) ecrire ok "Sauvegarde réussie" "$duree" ;;
  11)   ecrire erreur "Disque de secours plein" "$duree"; exit 1 ;;
  *)    ecrire erreur "Erreur de copie (code $rc)" "$duree"; exit 1 ;;
esac
