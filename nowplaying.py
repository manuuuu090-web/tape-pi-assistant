#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lecture en cours + controle - detecte et pilote ce qui joue sur le reseau local :
 - Sonos        (bibliotheque 'soco')        -> lecture + controle
 - Google Cast  (bibliotheque 'pychromecast')-> lecture + controle

Tourne dans un thread de fond. Si une bibliotheque manque, la source est ignoree
(l'assistant continue de fonctionner). Aucun compte / identifiant requis :
tout passe par le reseau local (meme Wi-Fi).
"""
import threading, time

STATE = {"playing": False}
_ACTIVE = {"type": None}
_lock = threading.Lock()
_sonos_cache = {"zones": None, "ts": 0}
_cast = {"casts": None, "browser": None, "ts": 0}
_radio_now = {"title": None, "device": None, "ts": 0}


# ----------------------------------------------------------- SONOS
def _poll_sonos():
    try:
        import soco
    except Exception:
        return None
    try:
        now = time.time()
        if not _sonos_cache["zones"] or now - _sonos_cache["ts"] > 60:
            _sonos_cache["zones"] = list(soco.discover(timeout=3) or [])
            _sonos_cache["ts"] = now
        for z in _sonos_cache["zones"]:
            try:
                if z.get_current_transport_info().get("current_transport_state") == "PLAYING":
                    t = z.get_current_track_info()
                    if not (t.get("title") or t.get("artist")):
                        continue
                    _ACTIVE.clear(); _ACTIVE.update({"type": "sonos", "ip": z.ip_address})
                    return {"playing": True, "source": "Sonos", "device": z.player_name,
                            "title": t.get("title", ""), "artist": t.get("artist", ""),
                            "album": t.get("album", ""), "art": t.get("album_art", "")}
            except Exception:
                continue
    except Exception:
        return None
    return None


# ----------------------------------------------------------- GOOGLE CAST
def _ensure_cast():
    import pychromecast
    now = time.time()
    # (re)decouvre si jamais fait, si liste vide, ou toutes les 2 min
    if _cast["casts"] is None or not _cast["casts"] or now - _cast["ts"] > 120:
        try:
            if _cast["browser"]:
                pychromecast.discovery.stop_discovery(_cast["browser"])
        except Exception:
            pass
        _cast["casts"], _cast["browser"] = pychromecast.get_chromecasts(timeout=6)
        for c in _cast["casts"]:
            try:
                c.wait(timeout=3)
            except Exception:
                pass
        _cast["ts"] = now
    return _cast["casts"] or []


def _poll_cast():
    try:
        import pychromecast  # noqa
    except Exception:
        return None
    try:
        for c in _ensure_cast():
            try:
                st = c.media_controller.status
                state = st.player_state if st else None
                if state in ("PLAYING", "BUFFERING"):
                    name = getattr(getattr(c, "cast_info", None), "friendly_name", None) or getattr(c, "name", "")
                    art = st.images[0].url if st.images else ""
                    title = st.title or ""
                    artist = st.artist or ""
                    source = "Google Cast"
                    # radio lancee par nous : titre de secours si le flux n'envoie pas de metadonnees
                    if (not title) and _radio_now.get("title") and (time.time() - _radio_now.get("ts", 0) < 14400) \
                       and (not _radio_now.get("device") or _radio_now["device"].lower() == name.lower()):
                        title = _radio_now["title"]; source = "Radio"
                    _ACTIVE.clear(); _ACTIVE.update({"type": "cast", "obj": c})
                    return {"playing": True, "source": source, "device": name,
                            "title": title or "Lecture", "artist": artist,
                            "album": st.album_name or "", "art": art or ""}
            except Exception:
                continue
    except Exception:
        return None
    return None


# ----------------------------------------------------------- CONTROLE
def control(action):
    a = dict(_ACTIVE)
    try:
        if a.get("type") == "sonos":
            import soco
            z = soco.SoCo(a["ip"])
            if action == "playpause":
                playing = z.get_current_transport_info().get("current_transport_state") == "PLAYING"
                z.pause() if playing else z.play()
            elif action == "next":    z.next()
            elif action == "prev":    z.previous()
            elif action == "volup":   z.volume = min(100, z.volume + 5)
            elif action == "voldown": z.volume = max(0, z.volume - 5)
            return True
        if a.get("type") == "cast":
            c = a["obj"]; mc = c.media_controller
            if action == "playpause":
                st = mc.status
                mc.pause() if (st and st.player_state == "PLAYING") else mc.play()
            elif action == "next":    mc.skip()
            elif action == "prev":    mc.queue_prev()
            elif action == "volup":   c.set_volume_relative(0.08)
            elif action == "voldown": c.set_volume_relative(-0.08)
            return True
    except Exception as e:
        print("[nowplaying] controle echoue:", e)
    return False


def list_cast_names():
    """Noms des enceintes Google detectees."""
    try:
        out = []
        for c in _ensure_cast():
            out.append(getattr(getattr(c, "cast_info", None), "friendly_name", None) or getattr(c, "name", ""))
        return [n for n in out if n]
    except Exception:
        return []


def play_url(url, title, content_type="audio/mpeg", device_name=None):
    """Lance un flux (radio) sur une enceinte Google (par nom, sinon la premiere)."""
    try:
        import pychromecast  # noqa
    except Exception:
        return False
    try:
        casts = _ensure_cast()
        target = None
        if device_name:
            for c in casts:
                nm = getattr(getattr(c, "cast_info", None), "friendly_name", None) or getattr(c, "name", "")
                if nm and nm.lower() == device_name.lower():
                    target = c; break
        if not target and casts:
            target = casts[0]
        if not target:
            return False
        target.wait(timeout=5)
        mc = target.media_controller
        mc.play_media(url, content_type, title=title, stream_type="LIVE")
        try:
            mc.block_until_active(timeout=5)
        except Exception:
            pass
        tgt_name = getattr(getattr(target, "cast_info", None), "friendly_name", None) or getattr(target, "name", "")
        _radio_now.update({"title": title, "device": tgt_name, "ts": time.time()})
        global STATE
        with _lock:
            STATE = {"playing": True, "source": "Radio", "device": tgt_name,
                     "title": title, "artist": "", "album": "", "art": ""}
        return True
    except Exception as e:
        print("[radio] lecture echouee:", e)
        return False


def _loop():
    global STATE
    while True:
        try:
            res = _poll_sonos() or _poll_cast()
        except Exception:
            res = None
        with _lock:
            STATE = res or {"playing": False}
        time.sleep(10)


def start():
    threading.Thread(target=_loop, daemon=True).start()


def get():
    with _lock:
        return dict(STATE)
