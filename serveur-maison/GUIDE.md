# Serveur maison — guide de mise en route

## 1. Réinstaller le Pi (une fois)
1. Sauvegarde déjà faite sur le SSD : `/mnt/ssd/Sauvegarde-Pi`.
2. Raspberry Pi Imager sur le PC → **Raspberry Pi 5** → **Raspberry Pi OS (other) → Raspberry Pi OS Lite (64-bit)** → la carte SD.
3. Réglages (roue dentée) : nom d'hôte `MANU`, utilisateur `manu-82`, SSH activé, fuseau `Europe/Paris`, clavier `fr`. Le Wi-Fi n'est pas nécessaire (câble Ethernet).
4. Carte dans le Pi, câble Ethernet branché, SSD branché, démarrage. Le Pi reprend l'adresse fixe **192.168.1.199** (réservée sur la Freebox).
5. PuTTY → `192.168.1.199`, puis :
   ```
   git clone -b serveur-maison --depth 1 https://github.com/manuuuu090-web/tape-pi-assistant
   cd tape-pi-assistant/serveur-maison && sudo bash installer.sh
   ```
6. Console Tailscale : supprimer l'ancienne machine « manuel », puis sur la nouvelle : **⋯ → Disable key expiry**.

## 2. Premier lancement de Home Assistant
1. Ouvrir `http://192.168.1.199:8123` → créer le compte (nom, identifiant, mot de passe).
2. Lieu : Auriol. Les appareils détectés sur le réseau sont proposés automatiquement.
3. Téléphone : appli **Home Assistant** (App Store / Play Store) → elle trouve le serveur à la maison.
   Pour l'extérieur : Paramètres de l'appli → Serveur → **URL externe** = `http://<ip-tailscale>:8123`, avec Tailscale activé sur le téléphone.
4. Le tableau de bord **État du système** est dans le menu de gauche.

## 3. Ajouter les appareils (Paramètres → Appareils et services → Ajouter)
Appareils vus sur ton réseau le 11/11/2026 :

| Appareil | Intégration à ajouter | Ce qu'il faut |
|---|---|---|
| Pont Philips Hue (192.168.1.49) | Philips Hue (proposé automatiquement) | Appuyer sur le bouton du pont |
| Enceintes Sonos | Sonos (automatique) | Rien |
| Nest Audio, Google Home, Chromecast | Google Cast (automatique) | Rien |
| Freebox | Freebox (automatique) | Valider la demande sur l'écran de la Freebox |
| Alarme et caméras Ring | Ring | Compte Ring + code reçu par SMS/mail |
| Aspirateur X20+, distributeur de croquettes | Xiaomi Home (via HACS, voir §4) | Compte Mi Home |
| Détecteurs d'eau SwitchBot | SwitchBot Cloud | Jeton de l'appli SwitchBot (Profil → Préférences) |
| Prises TECKIN | Tuya | Appli Smart Life / Tuya |
| Purificateur Levoit | VeSync | Compte VeSync |
| TV LG | LG webOS TV (automatique) | Accepter sur la TV |
| Clé Zigbee Sonoff ZBDongle-P | Zigbee Home Automation (ZHA) | Brancher la clé (rallonge USB, port **noir** USB 2), puis `sudo docker restart homeassistant` |
| Capteurs Zigbee Sonoff | ZHA → Ajouter un appareil | Appui long sur le bouton du capteur |
| Panneau mural ESP32-S3 4" | ESPHome (voir §5) | — |

## 4. HACS (pour Xiaomi Home)
```
sudo docker exec -it homeassistant bash -c "wget -O - https://get.hacs.xyz | bash -"
sudo docker restart homeassistant
```
Puis Paramètres → Appareils et services → Ajouter → **HACS** (connexion GitHub), et dans HACS : chercher **Xiaomi Home** → Télécharger → redémarrer → ajouter l'intégration Xiaomi Home.

## 5. Panneau mural 4" (ESPHome)
ESPHome tourne sur `http://192.168.1.199:6052`. À la réception du panneau, on prépare ensemble sa configuration (écran 480×480, tactile GT911) et on le flashe en USB depuis le PC.

## 6. Ce que surveille le tableau « État du système »
- Placard : température et humidité (capteur I2C), alerte au-dessus de 40 °C.
- Raspberry Pi : processeur (alerte à 75 °C), mémoire, charge, carte SD.
- SSD : place utilisée (alerte à 90 %), branché ou non.
- Réseau : Internet, Freebox, pont Hue, Freebox Player.
Les alertes arrivent sur le téléphone dès que l'appli Home Assistant y est installée.
Adresses à modifier si besoin : `/srv/homeassistant/config/capteurs_systeme.yaml`.
