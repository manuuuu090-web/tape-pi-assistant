#!/bin/bash
# Serveur maison — installation complète sur Raspberry Pi OS Lite 64 bits (sans bureau)
#   git clone -b serveur-maison --depth 1 https://github.com/manuuuu090-web/tape-pi-assistant && cd tape-pi-assistant/serveur-maison && sudo bash installer.sh
# Installe : NAS (SSD + partage réseau), Tailscale, capteur du placard, Docker,
#            Home Assistant et ESPHome. Durée : 15 à 20 minutes.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Lancez avec : sudo bash $0"; exit 1; }
ICI="$(cd "$(dirname "$0")" && pwd)"
UTIL="${SUDO_USER:-manu-82}"
SSD_UUID="A854348E543460EC"          # partition « film » du SSD (NTFS)
etape(){ echo -e "\n\033[1;33m== $* ==\033[0m"; }

etape "0/8 Vérifications"
ARCH=$(dpkg --print-architecture)
if [ "$ARCH" != "arm64" ]; then
  echo "Ce système est en $ARCH : Home Assistant exige la version 64 bits (arm64)."
  echo "Réinstallez « Raspberry Pi OS Lite (64-bit) » avec Raspberry Pi Imager."; exit 1
fi
grep -q enable-bracketed-paste "/home/$UTIL/.inputrc" 2>/dev/null || \
  echo 'set enable-bracketed-paste off' >> "/home/$UTIL/.inputrc"
chown "$UTIL": "/home/$UTIL/.inputrc"

etape "1/8 Mise à jour et paquets"
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get -y full-upgrade
DEBIAN_FRONTEND=noninteractive apt-get install -y ntfs-3g samba i2c-tools python3-smbus2 git curl

etape "2/8 Bus I2C pour le capteur du placard"
raspi-config nonint do_i2c 0
modprobe i2c-dev || true
i2cdetect -y 1 | grep -Eq ' 44 | 45 ' && echo "Capteur trouvé sur le bus I2C." \
  || echo "ATTENTION : capteur non détecté (vérifiez le câblage SDA=GPIO2, SCL=GPIO3, 3,3 V, GND)."

etape "3/8 Réseau : Ethernet seul"
read -rp "Couper le Wi-Fi du Pi pour n'utiliser que le câble ? (O/n) " R
if [[ ! "$R" =~ ^[nN]$ ]]; then
  if ip -4 addr show eth0 | grep -q inet; then nmcli radio wifi off && echo "Wi-Fi coupé."
  else echo "Pas d'adresse sur eth0 : Wi-Fi laissé allumé par sécurité."; fi
fi

etape "4/8 SSD sur /mnt/ssd"
mkdir -p /mnt/ssd
sed -i '\#[[:space:]]/mnt/ssd[[:space:]]#d' /etc/fstab
echo "UUID=$SSD_UUID  /mnt/ssd  ntfs-3g  defaults,nofail,uid=$(id -u "$UTIL"),gid=$(id -g "$UTIL"),umask=002,x-systemd.device-timeout=10  0  0" >> /etc/fstab
systemctl daemon-reload
umount /media/*/film 2>/dev/null || true
mount -a && df -h /mnt/ssd || echo "ATTENTION : SSD non monté (est-il branché ?)."

etape "5/8 Partage réseau du SSD (Samba)"
if ! grep -q "^\[ssd\]" /etc/samba/smb.conf; then
  cat >> /etc/samba/smb.conf <<EOF

[ssd]
   comment = SSD du Pi
   path = /mnt/ssd
   read only = no
   valid users = $UTIL
   create mask = 0664
   directory mask = 0775
EOF
fi
echo "Mot de passe du partage pour « $UTIL » (le même qu'avant, Windows le connaît déjà) :"
smbpasswd -a "$UTIL"
systemctl restart smbd

etape "6/8 Tailscale (accès depuis l'extérieur)"
command -v tailscale >/dev/null || curl -fsSL https://tailscale.com/install.sh | sh
tailscale up || true
echo "Adresse Tailscale du Pi : $(tailscale ip -4 2>/dev/null || echo '?')"

etape "7/8 Docker"
command -v docker >/dev/null || curl -fsSL https://get.docker.com | sh
usermod -aG docker "$UTIL"

etape "8/8 Home Assistant, ESPHome et capteur du placard"
mkdir -p /opt/serveur-maison /srv/homeassistant/config /srv/esphome
cp -r "$ICI"/. /opt/serveur-maison/
# configuration Home Assistant : copiée seulement si elle n'existe pas déjà
for f in configuration.yaml capteurs_systeme.yaml automations.yaml scripts.yaml scenes.yaml; do
  [ -e "/srv/homeassistant/config/$f" ] || cp "$ICI/homeassistant/$f" /srv/homeassistant/config/
done
mkdir -p /srv/homeassistant/config/dashboards /srv/homeassistant/config/themes
cp -n "$ICI"/homeassistant/dashboards/*.yaml /srv/homeassistant/config/dashboards/
echo '{"temperature": null, "humidite": null, "ok": false, "maj": 0}' > /srv/homeassistant/config/placard.json
cp "$ICI/capteur-placard/capteur-placard.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now capteur-placard
cd /opt/serveur-maison && docker compose up -d

IP=$(hostname -I | awk '{print $1}')
TS=$(tailscale ip -4 2>/dev/null || true)
cat <<EOF

=============================================================
 Serveur prêt (Home Assistant démarre en 2 à 3 minutes).
 Home Assistant :  http://$IP:8123      (dehors : http://${TS:-<ip-tailscale>}:8123)
 ESPHome        :  http://$IP:6052      (panneau mural)
 NAS (Windows)  :  \\\\$IP\\ssd          (dehors : \\\\${TS:-<ip-tailscale>}\\ssd)
 Suite : ouvrez Home Assistant et suivez le GUIDE.md (création du compte, appareils).
=============================================================
EOF
