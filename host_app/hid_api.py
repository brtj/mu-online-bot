import requests
import time

MOVE_URL    = "http://192.168.50.228:5000/mouse/move"
KEY_API     = "http://192.168.50.228:5000/keyboard/press"

def move(dx, dy):
    r = requests.post(MOVE_URL, json={"dx": int(dx), "dy": int(dy)}, timeout=30)
    r.raise_for_status()
    

def post(url, payload):
    print(f"POST with payload: {payload}")
    r = requests.post(url, json=payload, timeout=(60,120))
    r.raise_for_status()
    return r.json() if r.content else None


def press_enter():
    print("Sending Enter")
    time.sleep(0.2)
    post(KEY_API, {
        "keycode": 40,        # Enter (0x28)
        "press_time": 1
    })

def press_tab():
    print("Sending TAB")
    post(KEY_API, {
        "keycode": 43,        # TAB (0x2B)
        "press_time": 0.4
    })

def press_backspace():
    print("Sending BACKSPACE")
    post(KEY_API, {
        "keycode": 42,        # BACKSPACE (0x2A)
        "press_time": 0.4
    })