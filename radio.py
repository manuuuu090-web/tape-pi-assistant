#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Radios web - resout le flux a jour d'une station par son nom via l'annuaire
libre Radio-Browser (pas de cle), puis on la caste sur une enceinte Google.
Evite les URL de flux en dur qui tombent en panne.
"""

# stations par defaut (nom affiche -> terme de recherche)
DEFAULT_STATIONS = [
    {"name": "Fun Radio",    "query": "Fun Radio"},
    {"name": "NRJ",          "query": "NRJ"},
    {"name": "Nostalgie",    "query": "Nostalgie"},
    {"name": "Europe 2",     "query": "Europe 2"},
    {"name": "Radio Doudou", "query": "Radio Doudou"},
    {"name": "Pomme d'Api",  "query": "Radio Pomme d'Api"},
]

_SERVERS = [
    "https://de1.api.radio-browser.info",
    "https://nl1.api.radio-browser.info",
    "https://at1.api.radio-browser.info",
]
_cache = {}  # query -> (url, content_type)


def resolve(query, url_override=None):
    """Renvoie (url, content_type) du meilleur flux FRANCAIS pour cette station.
    Un 'url_override' (depuis la config) a priorite absolue."""
    if url_override:
        ct = "audio/aac" if ".aac" in url_override.lower() else "audio/mpeg"
        return (url_override, ct)
    if query in _cache:
        return _cache[query]
    import requests
    for base in _SERVERS:
        try:
            # recherche filtree sur la France, triee par popularite
            r = requests.get(base + "/json/stations/search",
                             params={"name": query, "countrycode": "FR",
                                     "order": "votes", "reverse": "true",
                                     "hidebroken": "true", "limit": 10},
                             headers={"User-Agent": "PiAssistant/1.0"}, timeout=10)
            r.raise_for_status()
            arr = r.json()
            if not arr:
                continue
            # prefere une station dont le nom contient bien la requete
            q = query.lower()
            arr.sort(key=lambda s: (q not in (s.get("name", "").lower()),
                                    -int(s.get("votes", 0) or 0)))
            best = arr[0]
            url = best.get("url_resolved") or best.get("url")
            codec = (best.get("codec") or "").upper()
            ctype = "audio/aac" if "AAC" in codec else "audio/mpeg"
            if url:
                _cache[query] = (url, ctype)
                return _cache[query]
        except Exception:
            continue
    return None
