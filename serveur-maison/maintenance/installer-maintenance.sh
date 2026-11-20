#!/bin/bash
# Installe la mise à jour automatique du serveur (chaque dimanche à 4 h 30).
#   sudo bash installer-maintenance.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Lancez avec : sudo bash $0"; exit 1; }
ICI="$(cd "$(dirname "$0")" && pwd)"
CFG=/srv/homeassistant/config
install -m 755 "$ICI/maj-auto.sh" /usr/local/bin/maj-auto.sh
cp "$ICI/../docker-compose.yml" /opt/serveur-maison/docker-compose.yml
cat > /etc/systemd/system/maj-auto.service <<'S'
[Unit]
Description=Mise à jour automatique du serveur maison
After=network-online.target sauvegarde-ssd.service
Wants=network-online.target
[Service]
Type=oneshot
ExecStart=/usr/local/bin/maj-auto.sh
TimeoutStartSec=2h
S
cat > /etc/systemd/system/maj-auto.timer <<'S'
[Unit]
Description=Mise à jour automatique chaque dimanche à 4 h 30
[Timer]
OnCalendar=Sun *-*-* 04:30:00
Persistent=true
RandomizedDelaySec=10min
[Install]
WantedBy=timers.target
S
systemctl daemon-reload
systemctl enable --now maj-auto.timer
grep -q maj_etat "$CFG/capteurs_systeme.yaml" || cat "$ICI/capteurs_maj.yaml" >> "$CFG/capteurs_systeme.yaml"
[ -f "$CFG/maj.json" ] || echo '{"etat":"jamais","message":"Première mise à jour dimanche à 4 h 30","derniere_reussite":0}' > "$CFG/maj.json"
docker restart homeassistant >/dev/null
echo "============================================================="
echo " Mise à jour automatique installée : chaque dimanche à 4 h 30."
echo " Prochaine : $(systemctl list-timers maj-auto.timer --no-legend | awk '{print $1, $2, $3}')"
echo " Lancer à la main : sudo systemctl start maj-auto"
echo "============================================================="
