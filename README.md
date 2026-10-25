# Assistant mural — Raspberry Pi

Tableau de bord tactile plein écran : **Météo (Auriol) + température maison (SHT31)**, **Planning (Google Agenda)**, **Bourse (portefeuille)**, **Trajets**.
Veille horloge après 3 min, écran noir la nuit (23h→6h), réveil au toucher.

## 1. Préparer le Raspberry Pi
```bash
sudo raspi-config        # Interface Options > I2C > activer (pour le capteur SHT31)
sudo apt update
sudo apt install -y python3-pip python3-venv chromium-browser unclutter
```

## 2. Installer l'app
```bash
cd ~/pi_assistant
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 3. Brancher le capteur SHT31 (I²C)
| SHT31 | Raspberry Pi |
|---|---|
| VIN | 3V3 (pin 1) |
| GND | GND (pin 6) |
| SCL/T | GPIO3 / SCL (pin 5) |
| SDA/RH | GPIO2 / SDA (pin 3) |

Vérifier qu'il est vu : `i2cdetect -y 1` → doit montrer **44**.

## 4. Remplir `config.json`
- **calendar.ical_url** : dans Google Agenda → *Paramètres de l'agenda* → *Intégrer l'agenda* → **Adresse secrète au format iCal** (…/basic.ics). Colle-la.
- **portfolio.holdings** : tes lignes `{ticker, name, qty, buy_price}`. Tickers Yahoo Finance (ex : `AAPL`, `MC.PA` = LVMH, `BTC-EUR`).
- **travel.ors_api_key** : clé gratuite sur openrouteservice.org ; `destinations` = tes lieux `{name, lon, lat}`.
- **sleep** : `idle_seconds` (veille horloge), `night_start/end`, `hdmi_power_off`.

## 5. Lancer
```bash
source venv/bin/activate
python3 app.py
```
Puis ouvre **http://localhost:5000** dans Chromium.

## 6. Démarrage auto en plein écran (kiosk)
Crée `~/.config/autostart/assistant.desktop` :
```ini
[Desktop Entry]
Type=Application
Name=Assistant
Exec=/bin/bash -c "cd /home/pi/pi_assistant && source venv/bin/activate && python3 app.py & sleep 6 && xset s off && xset -dpms && unclutter -idle 0.1 & chromium-browser --kiosk --incognito --disable-restore-session-state http://localhost:5000"
```
(adapte le chemin `/home/pi/…` si besoin)

## Notes écran HDMI
- La nuit, l'app noircit l'écran **et** tente de couper le signal HDMI (`vcgencmd display_power 0`). Un toucher le rallume.
- Si `vcgencmd` ne coupe pas ton écran, l'écran reste **noir** (rétroéclairage allumé) — c'est le comportement de secours.

## Faire évoluer
Tout est modulaire dans `app.py` (une fonction `fetch_*` par source) et `static/app.js` (une fonction `render*` par page). Dis-moi ce que tu veux ajouter (capteur PIR pour réveil à l'approche, autre page, etc.).
