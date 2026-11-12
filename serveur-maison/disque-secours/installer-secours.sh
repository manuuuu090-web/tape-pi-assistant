#!/bin/bash
# Prépare le disque de secours (Fanxiang S101Q 512 Go) et la sauvegarde
# automatique du SSD chaque dimanche à 3 h.
#   sudo bash installer-secours.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Lancez avec : sudo bash $0"; exit 1; }
ICI="$(cd "$(dirname "$0")" && pwd)"
MODELE="Fanxiang"
etape(){ echo -e "\n\033[1;33m== $* ==\033[0m"; }

etape "1/5 Recherche du disque de secours"
DISQUE=$(lsblk -dn -o NAME,MODEL | awk -v m="$MODELE" 'index($0,m){print "/dev/"$1; exit}')
[ -n "$DISQUE" ] || { echo "Disque $MODELE introuvable. Est-il branché ?"; exit 1; }
if lsblk -n -o MOUNTPOINT "$DISQUE" | grep -q .; then echo "$DISQUE est en cours d'utilisation : arrêt."; exit 1; fi
if [ "$DISQUE" = "$(findmnt -n -o SOURCE /mnt/ssd | sed 's/[0-9]*$//')" ]; then echo "Sécurité : c'est le SSD principal !"; exit 1; fi
lsblk -o NAME,SIZE,FSTYPE,LABEL,MODEL "$DISQUE"

PART="${DISQUE}1"
if [ "$(blkid -s LABEL -o value "$PART" 2>/dev/null || true)" = "secours" ]; then
  echo "Le disque est déjà préparé : rien n'est effacé."
else
  echo
  echo "ATTENTION : tout le contenu de $DISQUE ($MODELE) va être EFFACÉ."
  read -rp "Tapez OUI en majuscules pour continuer : " R
  [ "$R" = "OUI" ] || { echo "Annulé."; exit 1; }
  etape "2/5 Formatage"
  wipefs -a "$DISQUE"
  parted -s "$DISQUE" mklabel gpt mkpart secours ext4 0% 100%
  sleep 2; partprobe "$DISQUE" || true; sleep 2
  mkfs.ext4 -F -L secours "$PART"
fi

etape "3/5 Montage automatique sur /mnt/secours"
UUID=$(blkid -s UUID -o value "$PART")
mkdir -p /mnt/secours
sed -i '\#[[:space:]]/mnt/secours[[:space:]]#d' /etc/fstab
echo "UUID=$UUID  /mnt/secours  ext4  defaults,noatime,nofail,x-systemd.device-timeout=10  0  2" >> /etc/fstab
systemctl daemon-reload
mount /mnt/secours
df -h /mnt/secours

etape "4/5 Sauvegarde chaque dimanche à 3 h"
DEBIAN_FRONTEND=noninteractive apt-get install -y rsync >/dev/null
install -m 755 "$ICI/sauvegarde-ssd.sh" /usr/local/bin/sauvegarde-ssd.sh
cat > /etc/systemd/system/sauvegarde-ssd.service <<'EOF'
[Unit]
Description=Copie du SSD sur le disque de secours
After=local-fs.target
[Service]
Type=oneshot
ExecStart=/usr/local/bin/sauvegarde-ssd.sh
EOF
cat > /etc/systemd/system/sauvegarde-ssd.timer <<'EOF'
[Unit]
Description=Sauvegarde du SSD chaque dimanche à 3 h
[Timer]
OnCalendar=Sun *-*-* 03:00:00
Persistent=true
[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now sauvegarde-ssd.timer

etape "5/5 Suivi dans Home Assistant"
CFG=/srv/homeassistant/config
[ -f "$CFG/secours.json" ] || echo '{"etat":"jamais","message":"Pas encore de sauvegarde","derniere_reussite":0}' > "$CFG/secours.json"
grep -q sauvegarde_etat "$CFG/capteurs_systeme.yaml" || cat "$ICI/capteurs_secours.yaml" >> "$CFG/capteurs_systeme.yaml"
grep -q alerte_sauvegarde "$CFG/automations.yaml" || cat "$ICI/alertes_secours.yaml" >> "$CFG/automations.yaml"
docker restart homeassistant >/dev/null

echo
echo "Première sauvegarde lancée maintenant (elle peut durer une à deux heures)."
systemctl start --no-block sauvegarde-ssd.service
echo "============================================================="
echo " Disque de secours prêt. Sauvegarde : chaque dimanche à 3 h."
echo " Suivi : Home Assistant → Panneau mural → Appareils."
echo " Lancer une sauvegarde à la main : sudo systemctl start sauvegarde-ssd"
echo "============================================================="
