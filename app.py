#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assistant mural - Raspberry Pi  (serveur Flask)
Pages : Meteo+Temperature maison / Planning / Bourse / Trajets.
Donnees via API (Open-Meteo, Yahoo Finance, iCal Google Agenda, OpenRouteService)
+ capteur SHT31 en I2C (temperature/humidite de la maison).

Lancement :  python3 app.py    puis ouvrir http://localhost:5000 en plein ecran.
"""
import json, os, time, subprocess, uuid, datetime as dt
from pathlib import Path
from flask import Flask, jsonify, render_template, request

BASE = Path(__file__).parent
LOCAL_EVENTS_FILE = BASE / "local_events.json"   # evenements ajoutes a l'ecran (jamais ecrases)
CONFIG = {}


def load_local_events():
    try:
        return json.loads(LOCAL_EVENTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_local_events(evs):
    try:
        LOCAL_EVENTS_FILE.write_text(json.dumps(evs, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print("[local_events] erreur:", e)
        return False

def load_config():
    global CONFIG
    try:
        CONFIG = json.loads((BASE / "config.json").read_text(encoding="utf-8"))
    except Exception as e:
        print("[config] erreur:", e); CONFIG = {}
    return CONFIG

load_config()
app = Flask(__name__)

# detection "lecture en cours" (Sonos / Google Cast) en tache de fond
try:
    import nowplaying
    nowplaying.start()
except Exception as e:
    print("[nowplaying] desactive:", e)
    nowplaying = None

import system as sysinfo
VERSION = sysinfo.version(str(BASE))   # hash git court, capture au demarrage

# ---- petit cache pour ne pas spammer les API ----
_cache = {}
def cached(key, ttl, fn):
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    try:
        val = fn()
    except Exception as e:
        print(f"[{key}] erreur:", e)
        val = hit[1] if hit else {"error": str(e)}
    _cache[key] = (now, val)
    return val

# =========================================================================
#  CAPTEUR SHT31 (I2C) - temperature + humidite de la maison
# =========================================================================
def read_sht31():
    s = CONFIG.get("sensor", {})
    if not s.get("enabled"): return {"ok": False, "reason": "desactive"}
    try:
        from smbus2 import SMBus, i2c_msg
        addr = int(str(s.get("address", "0x44")), 16)
        bus = SMBus(int(s.get("i2c_bus", 1)))
        # mesure haute repetabilite, clock stretch off : 0x2400
        bus.write_i2c_block_data(addr, 0x24, [0x00])
        time.sleep(0.02)
        read = i2c_msg.read(addr, 6)
        bus.i2c_rdwr(read)
        data = list(read)
        bus.close()
        t_raw = data[0] << 8 | data[1]
        h_raw = data[3] << 8 | data[4]
        temp = -45 + (175 * t_raw / 65535.0)
        hum = 100 * h_raw / 65535.0
        return {"ok": True, "temp": round(temp, 1), "hum": round(hum, 0)}
    except Exception as e:
        return {"ok": False, "reason": str(e)}

# =========================================================================
#  METEO (Open-Meteo, gratuit, sans cle)
# =========================================================================
WMO = {0:"Ciel degage",1:"Plutot clair",2:"Partiellement nuageux",3:"Couvert",
       45:"Brouillard",48:"Brouillard givrant",51:"Bruine faible",53:"Bruine",55:"Bruine forte",
       61:"Pluie faible",63:"Pluie",65:"Pluie forte",66:"Pluie verglacante",67:"Pluie verglacante",
       71:"Neige faible",73:"Neige",75:"Neige forte",77:"Grains de neige",
       80:"Averses faibles",81:"Averses",82:"Averses fortes",85:"Averses de neige",86:"Averses de neige",
       95:"Orage",96:"Orage + grele",99:"Orage violent"}
WICON = {0:"☀️",1:"🌤️",2:"⛅",3:"☁️",45:"🌫️",48:"🌫️",51:"🌦️",53:"🌦️",55:"🌦️",
         61:"🌧️",63:"🌧️",65:"🌧️",66:"🌧️",67:"🌧️",71:"🌨️",73:"🌨️",75:"🌨️",77:"🌨️",
         80:"🌦️",81:"🌧️",82:"⛈️",85:"🌨️",86:"🌨️",95:"⛈️",96:"⛈️",99:"⛈️"}

def _rnd(v):
    try:
        return round(v)
    except Exception:
        return None

def _open_meteo(lat, lon, tz, model):
    import requests
    url = ("https://api.open-meteo.com/v1/forecast"
           f"?latitude={lat}&longitude={lon}&timezone={tz}"
           "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
           "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
           "&forecast_days=5")
    if model:
        url += f"&models={model}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    j = r.json()
    cur = j.get("current") or {}
    dy = j.get("daily") or {}
    # valide : on a bien un code meteo courant ET des jours
    if cur.get("weather_code") is None or not dy.get("time"):
        raise ValueError("reponse incomplete")
    return j

def fetch_weather():
    loc = CONFIG.get("location", {})
    lat, lon = loc.get("lat", 43.37), loc.get("lon", 5.64)
    tz = loc.get("timezone", "Europe/Paris")
    model = loc.get("model", "meteofrance_seamless")
    # essaie Meteo-France d'abord, repli sur le modele par defaut si incomplet
    d = None
    for m in [model, None]:
        try:
            d = _open_meteo(lat, lon, tz, m)
            break
        except Exception as e:
            print(f"[weather] modele={m or 'defaut'} echec: {e}")
            d = None
    if not d:
        raise RuntimeError("météo indisponible")
    cur = d.get("current", {})
    wc = int(cur.get("weather_code") or 0)
    out = {
        "name": loc.get("name", ""),
        "temp": _rnd(cur.get("temperature_2m")),
        "feels": _rnd(cur.get("apparent_temperature")),
        "hum": _rnd(cur.get("relative_humidity_2m")),
        "wind": _rnd(cur.get("wind_speed_10m")),
        "code": wc, "desc": WMO.get(wc, ""), "icon": WICON.get(wc, "❓"),
        "days": []
    }
    dy = d.get("daily", {})
    jours = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"]
    for i, date in enumerate(dy.get("time", [])):
        try:
            c = int(dy["weather_code"][i])
        except Exception:
            c = 0
        day = dt.date.fromisoformat(date)
        out["days"].append({
            "label": "Auj." if i == 0 else jours[day.weekday()],
            "code": c,
            "icon": WICON.get(c, "❓"),
            "tmax": _rnd(dy.get("temperature_2m_max", [None]*9)[i]),
            "tmin": _rnd(dy.get("temperature_2m_min", [None]*9)[i]),
            "rain": dy.get("precipitation_probability_max", [None]*9)[i]
        })
    return out

# =========================================================================
#  PLANNING (iCal Google Agenda)
# =========================================================================
def fetch_calendar():
    import requests
    from icalendar import Calendar
    c = CONFIG.get("calendar", {})
    url = c.get("ical_url", "").strip()
    if not url:
        return {"configured": False, "events": []}
    r = requests.get(url, timeout=12); r.raise_for_status()
    cal = Calendar.from_ical(r.content)
    now = dt.datetime.now().astimezone()
    # fenetre : du 1er du mois courant jusqu'a ~60 jours plus tard
    # (le mois complet pour les pastilles du calendrier + les evenements a venir)
    start_window = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_window = now + dt.timedelta(days=60)
    evs = []
    for comp in cal.walk("VEVENT"):
        start = comp.get("DTSTART").dt
        if isinstance(start, dt.date) and not isinstance(start, dt.datetime):
            start_dt = dt.datetime(start.year, start.month, start.day).astimezone()
            allday = True
        else:
            start_dt = start.astimezone() if start.tzinfo else start.astimezone()
            allday = False
        if start_dt < start_window or start_dt > end_window:
            continue
        evs.append({
            "title": str(comp.get("SUMMARY", "(sans titre)")),
            "start": start_dt.isoformat(),
            "allday": allday,
            "location": str(comp.get("LOCATION", "")),
        })
    evs.sort(key=lambda e: e["start"])
    return {"configured": True, "events": evs[: int(c.get("max_events", 60))]}

def calendar_data():
    """Agenda Google (en cache) + evenements locaux ajoutes a l'ecran (toujours frais)."""
    try:
        base = cached("calendar", 300, fetch_calendar)
    except Exception:
        base = {"configured": False, "events": []}
    evs = list(base.get("events", []))
    configured = base.get("configured", False)
    for e in load_local_events():
        evs.append({"title": e.get("title", ""), "start": e.get("start", ""),
                    "allday": e.get("allday", True), "location": e.get("location", ""),
                    "local": True, "id": e.get("id", "")})
        configured = True
    evs.sort(key=lambda x: x.get("start", ""))
    return {"configured": configured, "events": evs}

# =========================================================================
#  BOURSE (Yahoo Finance via yfinance)
# =========================================================================
def yahoo_price(ticker):
    """Cours actuel via l'API publique Yahoo (JSON, sans cle, sans yfinance/pandas)."""
    import requests
    u = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
    r = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    r.raise_for_status()
    meta = r.json()["chart"]["result"][0]["meta"]
    return float(meta.get("regularMarketPrice") or meta.get("previousClose") or 0)

def fetch_portfolio():
    p = CONFIG.get("portfolio", {})
    cur = p.get("currency", "EUR")
    cash = float(p.get("cash", 0))
    rows, titres_val, total_cost = [], 0.0, 0.0
    for h in p.get("holdings", []):
        tk = h.get("ticker", "").strip()
        price = 0.0
        if tk:
            try:
                price = yahoo_price(tk)
            except Exception:
                price = 0.0
        if price == 0 and h.get("manual_price"):   # secours si ticker absent/inconnu
            price = float(h["manual_price"])
        qty = float(h.get("qty", 0)); buy = float(h.get("buy_price", 0))
        val = price * qty; cost = buy * qty
        titres_val += val; total_cost += cost
        rows.append({
            "ticker": tk or "—", "name": h.get("name", tk), "qty": qty,
            "price": round(price, 2), "value": round(val, 2),
            "pl": round(val - cost, 2),
            "pl_pct": round((val - cost) / cost * 100, 1) if cost else 0.0
        })
    total_val = titres_val + cash
    return {
        "currency": cur, "rows": rows, "cash": round(cash, 2),
        "titres_value": round(titres_val, 2),
        "total_value": round(total_val, 2),
        "total_pl": round(titres_val - total_cost, 2),
        "total_pl_pct": round((titres_val - total_cost) / total_cost * 100, 1) if total_cost else 0.0
    }

# =========================================================================
#  TRAJETS (OpenRouteService)
# =========================================================================
_geo_cache = {}

def _tomtom_geocode(addr, key):
    """Adresse -> (lat, lon) via TomTom, avec cache (les adresses ne bougent pas)."""
    if addr in _geo_cache:
        return _geo_cache[addr]
    import requests
    u = "https://api.tomtom.com/search/2/geocode/" + requests.utils.quote(addr) + ".json"
    r = requests.get(u, params={"key": key, "countrySet": "FR", "limit": 1}, timeout=12)
    r.raise_for_status()
    res = r.json().get("results") or []
    if not res:
        return None
    p = res[0]["position"]
    _geo_cache[addr] = (p["lat"], p["lon"])
    return _geo_cache[addr]

def fetch_travel():
    import requests
    t = CONFIG.get("travel", {})
    key = t.get("tomtom_api_key", "").strip()
    home = t.get("home")
    dests = t.get("destinations", [])
    if not key or not home or not dests:
        return {"configured": bool(key), "rows": [], "reason": "clé ou destinations manquantes"}
    try:
        h = _tomtom_geocode(home, key)
    except Exception as e:
        return {"configured": True, "rows": [], "reason": "géocodage domicile: " + str(e)}
    if not h:
        return {"configured": True, "rows": [], "reason": "domicile introuvable"}
    rows = []
    for d in dests:
        try:
            pos = _tomtom_geocode(d.get("address", ""), key)
            if not pos:
                raise ValueError("adresse introuvable")
            u = (f"https://api.tomtom.com/routing/1/calculateRoute/"
                 f"{h[0]},{h[1]}:{pos[0]},{pos[1]}/json")
            r = requests.get(u, params={"key": key, "traffic": "true",
                                        "travelMode": "car", "routeType": "fastest"}, timeout=12)
            r.raise_for_status()
            s = r.json()["routes"][0]["summary"]
            rows.append({"name": d.get("name", "?"),
                         "minutes": round(s["travelTimeInSeconds"] / 60),
                         "km": round(s["lengthInMeters"] / 1000, 1),
                         "delay": round(s.get("trafficDelayInSeconds", 0) / 60)})
        except Exception as e:
            rows.append({"name": d.get("name", "?"), "minutes": None, "km": None, "error": str(e)})
    return {"configured": True, "rows": rows}

# =========================================================================
#  ROUTES
# =========================================================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/all")
def api_all():
    return jsonify({
        "time": dt.datetime.now().isoformat(),
        "sensor": read_sht31(),
        "weather": cached("weather", 600, fetch_weather),
        "calendar": calendar_data(),
        "portfolio": cached("portfolio", 120, fetch_portfolio),
        "travel": cached("travel", 300, fetch_travel),
        "nowplaying": nowplaying.get() if nowplaying else {"playing": False},
        "vacuum": cached("vacuum", 20, lambda: __import__("vacuum").get_status(CONFIG.get("vacuum", {}))),
        "system": cached("system", 10, lambda: sysinfo.stats(str(BASE), VERSION)),
        "version": VERSION,
        "sleep": CONFIG.get("sleep", {}),
    })

@app.route("/api/version")
def api_version():
    return jsonify({"version": VERSION})

@app.route("/api/system")
def api_system():
    return jsonify(cached("system", 10, lambda: sysinfo.stats(str(BASE), VERSION)))

@app.route("/api/update", methods=["POST"])
def api_update():
    # lance le script de mise a jour en tache detachee (git pull + relance)
    try:
        # start_new_session : le script survit a l'arret de l'app pendant la relance
        subprocess.Popen(["bash", str(BASE / "update.sh")],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/nowplaying")
def api_nowplaying():
    return jsonify(nowplaying.get() if nowplaying else {"playing": False})

@app.route("/api/vacuum")
def api_vacuum():
    import vacuum
    return jsonify(cached("vacuum", 20, lambda: vacuum.get_status(CONFIG.get("vacuum", {}))))

@app.route("/api/vacuum/<action>", methods=["POST"])
def api_vacuum_action(action):
    import vacuum
    ok = vacuum.control(CONFIG.get("vacuum", {}), action)
    _cache.pop("vacuum", None)
    return jsonify({"ok": bool(ok)})

@app.route("/api/music/<action>", methods=["POST"])
def api_music(action):
    if not nowplaying:
        return jsonify({"ok": False, "reason": "module absent"})
    ok = nowplaying.control(action)
    return jsonify({"ok": bool(ok)})

def _radio_stations():
    import radio
    return CONFIG.get("radio", {}).get("stations") or radio.DEFAULT_STATIONS

@app.route("/api/radio/list")
def api_radio_list():
    return jsonify({"stations": [s.get("name", "") for s in _radio_stations()]})

@app.route("/api/radio/<int:idx>", methods=["POST"])
def api_radio_play(idx):
    import radio
    if not nowplaying:
        return jsonify({"ok": False, "reason": "module absent"})
    stations = _radio_stations()
    if idx < 0 or idx >= len(stations):
        return jsonify({"ok": False, "reason": "station inconnue"})
    st = stations[idx]
    try:
        found = radio.resolve(st.get("query") or st.get("name"), st.get("url"))
        if not found:
            return jsonify({"ok": False, "reason": "flux introuvable"})
        url, ctype = found
        device = CONFIG.get("radio", {}).get("device") or None
        ok = nowplaying.play_url(url, st.get("name", "Radio"), ctype, device)
        return jsonify({"ok": bool(ok)})
    except Exception as e:
        return jsonify({"ok": False, "reason": str(e)})

@app.route("/api/weather")
def api_weather():  return jsonify(cached("weather", 600, fetch_weather))
@app.route("/api/sensor")
def api_sensor():   return jsonify(read_sht31())
@app.route("/api/calendar")
def api_calendar(): return jsonify(calendar_data())

@app.route("/api/event", methods=["POST"])
def api_event_add():
    d = request.get_json(force=True, silent=True) or {}
    date = (d.get("date") or "").strip()      # "YYYY-MM-DD"
    title = (d.get("title") or "").strip()
    tm = (d.get("time") or "").strip()        # "HH:MM" optionnel
    if not date or not title:
        return jsonify({"ok": False, "reason": "date ou titre manquant"})
    allday = not tm
    start = f"{date}T{tm}:00" if tm else f"{date}T00:00:00"
    evs = load_local_events()
    evs.append({"id": uuid.uuid4().hex[:8], "title": title, "start": start,
                "allday": allday, "location": ""})
    save_local_events(evs)
    _cache.pop("calendar", None)
    return jsonify({"ok": True})

@app.route("/api/event/delete", methods=["POST"])
def api_event_del():
    d = request.get_json(force=True, silent=True) or {}
    eid = (d.get("id") or "").strip()
    evs = [e for e in load_local_events() if e.get("id") != eid]
    save_local_events(evs)
    _cache.pop("calendar", None)
    return jsonify({"ok": True})
@app.route("/api/portfolio")
def api_portfolio():return jsonify(cached("portfolio", 120, fetch_portfolio))
@app.route("/api/travel")
def api_travel():   return jsonify(cached("travel", 300, fetch_travel))

@app.route("/api/display/<state>", methods=["POST"])
def api_display(state):
    # coupe/rallume le signal HDMI (ecran HDMI). Best-effort.
    try:
        subprocess.run(["vcgencmd", "display_power", "1" if state == "on" else "0"],
                       check=False, timeout=5)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/reload", methods=["POST"])
def api_reload():
    load_config(); _cache.clear(); return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)
