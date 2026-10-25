#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Etat du systeme (sans dependance externe) + version git."""
import os, time, socket, subprocess


def _cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read()) / 1000)
    except Exception:
        return None


def _cpu_percent():
    try:
        def read():
            with open("/proc/stat") as f:
                vals = list(map(int, f.readline().split()[1:]))
            idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
            return idle, sum(vals)
        i1, t1 = read(); time.sleep(0.2); i2, t2 = read()
        dt, di = t2 - t1, i2 - i1
        return round(100 * (1 - di / dt)) if dt > 0 else None
    except Exception:
        return None


def _ram():
    try:
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":")
                info[k] = int(v.strip().split()[0])
        total = info["MemTotal"]
        avail = info.get("MemAvailable", info.get("MemFree", 0))
        return round(100 * (total - avail) / total) if total else None
    except Exception:
        return None


def _disk():
    try:
        import shutil
        u = shutil.disk_usage(os.path.expanduser("~"))
        return round(100 * u.used / u.total)
    except Exception:
        return None


def _uptime():
    try:
        with open("/proc/uptime") as f:
            s = float(f.read().split()[0])
        d, h, m = int(s // 86400), int((s % 86400) // 3600), int((s % 3600) // 60)
        if d:
            return f"{d} j {h} h"
        if h:
            return f"{h} h {m} min"
        return f"{m} min"
    except Exception:
        return None


def _ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
        return ip
    except Exception:
        return None


def version(base):
    try:
        return subprocess.check_output(["git", "-C", base, "rev-parse", "--short", "HEAD"],
                                       stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "dev"


def stats(base, ver):
    return {"cpu_temp": _cpu_temp(), "cpu": _cpu_percent(), "ram": _ram(),
            "disk": _disk(), "uptime": _uptime(), "ip": _ip(), "version": ver}
