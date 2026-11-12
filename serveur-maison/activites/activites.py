#!/usr/bin/env python3
"""Activités de la semaine à Auriol, Cassis, La Ciotat et Roquevaire.

Lit l'agenda de MyProvence (département des Bouches-du-Rhône) et affiche
un JSON pour le capteur « Activités de la semaine » de Home Assistant.
Uniquement la bibliothèque standard : tourne tel quel dans le conteneur.
"""
import datetime as dt
import html
import json
import re
import sys
import urllib.request

VILLES = {"auriol": "Auriol", "cassis": "Cassis", "la_ciotat": "La Ciotat", "roquevaire": "Roquevaire"}
BASE = "https://www.myprovence.fr"
JOURS = 7          # fenêtre affichée : aujourd'hui + 6 jours
MAX_PAR_VILLE = 6
PAGES = 4
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux aarch64) HomeAssistant-Activites/1.0",
      "Accept-Language": "fr-FR,fr;q=0.9"}
CACHE = "/config/activites_cache.json"


def lire(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def tags_villes():
    page = lire(BASE + "/agenda")
    ids = {}
    for m in re.finditer(r'data-drupal-facet-item-value="(\d+)"[^>]*>\s*<span class="facet-item__value">([^<]+)<', page):
        nom = html.unescape(m.group(2)).strip().lower()
        for cle, ville in VILLES.items():
            if nom == ville.lower():
                ids[cle] = m.group(1)
    return ids


def evenements(tag):
    vus, liste = set(), []
    for p in range(PAGES):
        url = f"{BASE}/agenda?f%5B0%5D=agendatags%3A{tag}" + (f"&page={p}" if p else "")
        try:
            page = lire(url)
        except Exception:
            break
        morceaux = re.split(r'class="field-group-link"', page)
        nouveaux = 0
        for i in range(1, len(morceaux)):
            avant, c = morceaux[i - 1], morceaux[i]
            lien = re.findall(r'<a href="(/agenda/[^"]+)"[^>]*$', avant)
            titre = re.search(r'class="title">([^<]+)<', c)
            bloc_dates = c.split("teaser-city")[0]
            dates = re.findall(r'datetime="(\d{4}-\d{2}-\d{2})', bloc_dates)
            cat = re.search(r'/agenda/([a-z0-9-]+)/', lien[-1]) if lien else None
            if not titre or not dates:
                continue
            cle = (titre.group(1), dates[0])
            if cle in vus:
                continue
            vus.add(cle)
            nouveaux += 1
            liste.append({
                "titre": html.unescape(titre.group(1)).strip(),
                "debut": dates[0],
                "fin": dates[-1],
                "type": cat.group(1).replace("-", " ").capitalize() if cat else "",
                "lien": BASE + lien[-1] if lien else "",
            })
        if nouveaux == 0 or len(morceaux) < 13:
            break
    return liste


def semaine(liste, aujourdhui):
    fin_sem = aujourdhui + dt.timedelta(days=JOURS - 1)
    garde = []
    for e in liste:
        d, f = dt.date.fromisoformat(e["debut"]), dt.date.fromisoformat(e["fin"])
        if f < aujourdhui or d > fin_sem:
            continue
        e["long"] = (f - d).days > 7          # expo, marché permanent…
        e["jour"] = max(d, aujourdhui).isoformat()
        garde.append(e)
    garde.sort(key=lambda e: (e["long"], e["jour"], e["titre"]))
    return garde[:MAX_PAR_VILLE]


def main():
    aujourdhui = dt.date.today()
    out = {"maj": dt.datetime.now().isoformat(timespec="minutes"), "ok": True, "total": 0}
    try:
        ids = tags_villes()
        for cle in VILLES:
            out[cle] = semaine(evenements(ids[cle]), aujourdhui) if cle in ids else []
            out["total"] += len(out[cle])
        json.dump(out, open(CACHE, "w"), ensure_ascii=False)
    except Exception as e:  # site injoignable : on garde la dernière liste connue
        try:
            out = json.load(open(CACHE))
            out["ok"] = False
        except Exception:
            out = {"ok": False, "total": 0, "erreur": str(e), **{c: [] for c in VILLES}}
    json.dump(out, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
