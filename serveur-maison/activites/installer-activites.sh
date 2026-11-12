#!/bin/bash
# Ajoute le capteur « Activités de la semaine » à Home Assistant.
#   sudo bash installer-activites.sh
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "Lancez avec : sudo bash $0"; exit 1; }
ICI="$(cd "$(dirname "$0")" && pwd)"
CFG=/srv/homeassistant/config
install -m 644 "$ICI/activites.py" "$CFG/activites.py"
grep -q activites_semaine "$CFG/capteurs_systeme.yaml" || cat "$ICI/capteur_activites.yaml" >> "$CFG/capteurs_systeme.yaml"
echo "Test de lecture de l'agenda…"
docker exec homeassistant python3 /config/activites.py | python3 -c "import json,sys; d=json.load(sys.stdin); print('OK :', d.get('total'), 'activités trouvées cette semaine' if d.get('ok') else '(site injoignable)')"
docker restart homeassistant >/dev/null
echo "Terminé : Home Assistant redémarre (1 minute)."
