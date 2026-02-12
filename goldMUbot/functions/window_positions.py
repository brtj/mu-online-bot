#!/usr/bin/env python3
import requests

URL = "http://192.168.50.200:5055/window/move"
HEADERS = {"Content-Type": "application/json"}


def move_window(title, x, y, w, h):
    payload = {"title": title, "x": x, "y": y, "w": w, "h": h}
    r = requests.post(URL, json=payload, headers=HEADERS, timeout=3)
    r.raise_for_status()
    return r.json() if r.content else None


# === usage ===

# move_window(
#     title="AleElfisko",
#     x=0, y=0, w=817, h=640
# )

move_window(title="CoZaBzdura", x=810, y=0, w=817, h=640)
