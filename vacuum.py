#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aspirateur Xiaomi Robot Vacuum X20+ (xiaomi.vacuum.c102gl) - controle local MIoT.
IDs tires de la spec du modele :
  batterie       : siid 3 / piid 1
  etat de charge : siid 3 / piid 2
  statut         : siid 2 / piid 1
  actions        : start-sweep 2/1, stop-sweeping 2/2, start-charge 3/1, position 7/1
On passe par l'API Python de python-miio (le CLI 'miiocli' est casse sous Python 3.13).
"""

# actions MIoT : nom -> (siid, aiid)
ACTIONS = {
    "start":  (2, 1),   # start-sweep  : lancer le nettoyage
    "stop":   (2, 2),   # stop-sweeping: arreter
    "home":   (3, 1),   # start-charge : retour a la base
    "locate": (7, 1),   # position     : faire biper le robot
}

# statut (siid 2/1) - libelles usuels, avec repli si code inconnu
STATUS = {
    1: "En veille", 2: "Au repos", 3: "En pause", 4: "En nettoyage",
    5: "En déplacement", 6: "Retour base", 7: "En charge", 8: "En charge",
    9: "Erreur", 10: "Mise à jour", 11: "Lavage serpillère", 12: "Séchage",
}
CHARGING = {1: "En charge", 2: "Sur batterie", 4: "À la base", 5: "À la base"}


def _dev(cfg):
    from miio import MiotDevice
    return MiotDevice(cfg["ip"], cfg["token"])


def get_status(cfg):
    if not cfg or not cfg.get("enabled") or not cfg.get("ip"):
        return {"ok": False, "reason": "non configuré"}
    try:
        d = _dev(cfg)

        def gp(siid, piid):
            try:
                return d.get_property_by(siid, piid)[0].get("value")
            except Exception:
                return None

        bat = gp(3, 1)
        chg = gp(3, 2)
        st = gp(2, 1)
        charging = (chg == 1)
        if charging:
            label = "En charge"
        else:
            label = STATUS.get(st, CHARGING.get(chg, "Prêt"))
        return {"ok": True, "battery": bat, "charging": charging,
                "status_code": st, "label": label}
    except Exception as e:
        return {"ok": False, "reason": str(e)}


def control(cfg, action):
    if action not in ACTIONS or not cfg or not cfg.get("ip"):
        return False
    try:
        siid, aiid = ACTIONS[action]
        _dev(cfg).call_action_by(siid, aiid)
        return True
    except Exception as e:
        print("[vacuum] action échouée:", e)
        return False
