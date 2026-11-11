#!/usr/bin/env python3
"""Lit le capteur I2C du placard (SHT31, adresse 0x44 ou 0x45) toutes les 30 s
et écrit la mesure dans un fichier JSON que Home Assistant lit.
Aucun réseau, aucun mot de passe : simple fichier partagé."""
import json, os, time
from smbus2 import SMBus, i2c_msg

SORTIE = os.environ.get("SORTIE", "/srv/homeassistant/config/placard.json")
PERIODE = 30

def crc8(data):
    crc = 0xFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc << 1) ^ 0x31) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc

def lire(bus, adr):
    bus.i2c_rdwr(i2c_msg.write(adr, [0x24, 0x00]))   # mesure, haute répétabilité
    time.sleep(0.02)
    lecture = i2c_msg.read(adr, 6)
    bus.i2c_rdwr(lecture)
    d = list(lecture)
    if crc8(d[0:2]) != d[2] or crc8(d[3:5]) != d[5]:
        raise ValueError("CRC invalide")
    t = -45 + 175 * ((d[0] << 8) | d[1]) / 65535
    h = 100 * ((d[3] << 8) | d[4]) / 65535
    return round(t, 1), round(h, 1)

def ecrire(donnees):
    tmp = SORTIE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(donnees, f)
    os.replace(tmp, SORTIE)

def main():
    adr = None
    with SMBus(1) as bus:
        while True:
            try:
                if adr is None:
                    for a in (0x44, 0x45):
                        try:
                            lire(bus, a); adr = a; break
                        except OSError:
                            pass
                    if adr is None:
                        raise OSError("capteur introuvable en 0x44/0x45")
                t, h = lire(bus, adr)
                ecrire({"temperature": t, "humidite": h, "ok": True, "maj": int(time.time())})
            except Exception as e:
                adr = None
                ecrire({"temperature": None, "humidite": None, "ok": False, "erreur": str(e), "maj": int(time.time())})
            time.sleep(PERIODE)

if __name__ == "__main__":
    main()
