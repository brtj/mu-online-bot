#!/usr/bin/env python3
import time
import random
from flask import Flask, request, jsonify
import socket, json, threading

app = Flask(__name__)

KEYBOARD_PATH = "/dev/hidg1"
MOUSE_PATH = "/dev/hidg0" 

DIGITS = {
    '1': 0x1E, '2': 0x1F, '3': 0x20, '4': 0x21, '5': 0x22,
    '6': 0x23, '7': 0x24, '8': 0x25, '9': 0x26, '0': 0x27,
}

MOUSE_BUTTONS = {
    "left":  0x01,
    "right": 0x02,
    "middle": 0x04,
}

def clamp_int8(v: int) -> int:
    # signed 8-bit range
    return max(-127, min(127, int(v)))

def udp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 5001))
    while True:
        data, addr = sock.recvfrom(1024)
        try:
            msg = json.loads(data.decode("utf-8"))
            dx = int(msg.get("dx", 0))
            dy = int(msg.get("dy", 0))
            step_delay = float(msg.get("step_delay", 0.0))
            move_mouse(dx, dy, step_delay=step_delay)
        except Exception:
            pass

def send_keyboard_event(modifier: int, keycode: int, press_time=0.1):
    report = bytearray(8)
    report[0] = modifier
    report[2] = keycode

    with open(KEYBOARD_PATH, "wb", buffering=0) as keyboard:
        keyboard.write(bytearray(8))   # clear
        time.sleep(0.02)

        keyboard.write(report)         # press
        time.sleep(press_time)

        keyboard.write(bytearray(8))   # release
        time.sleep(0.02)

@app.post("/keyboard/press")
def keyboard_press():
    """
    JSON:
    {
      "keycode": 4,
      "modifier": 0,
      "press_time": 0.1
    }
    """
    data = request.get_json(force=True, silent=True) or {}

    if "keycode" not in data:
        return jsonify(ok=False, error="Missing keycode"), 400

    keycode = int(data["keycode"])
    modifier = int(data.get("modifier", 0))
    press_time = int(data.get("press_time",0)) 

    send_keyboard_event(modifier, keycode, press_time)

    return jsonify(
        ok=True,
        keycode=keycode,
        modifier=modifier,
	press_time=press_time
    )


@app.post("/keyboard/text")
def keyboard_text():
    """
    JSON:
    {
      "text": "abc"
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "")

    if not text:
        return jsonify(ok=False, error="Empty text"), 400

    for ch in text.lower():
        if 'a' <= ch <= 'z':
            keycode = ord(ch) - ord('a') + 4
            send_keyboard_event(0x00, keycode)
        elif ch == ' ':
            send_keyboard_event(0x00, 0x2C)  # SPACE
        elif ch == '/':
            send_keyboard_event(0x00, 0x38)  # SLASH
        elif ch in DIGITS:
            send_keyboard_event(0x00, DIGITS[ch])
        time.sleep(random.uniform(0.03, 0.12))

    return jsonify(ok=True, text=text)

# =========================
# Mouse (boot mouse report: 4 bytes)
# report[0] = buttons bitmask
# report[1] = X delta (int8)
# report[2] = Y delta (int8)
# report[3] = wheel (int8)
# =========================
def send_mouse_report(buttons: int = 0, dx: int = 0, dy: int = 0, wheel: int = 0):
    report = bytearray(4)
    report[0] = buttons & 0xFF
    report[1] = (dx & 0xFF)  # int8 encoded as two's complement
    report[2] = (dy & 0xFF)
    report[3] = (wheel & 0xFF)

    with open(MOUSE_PATH, "wb", buffering=0) as mouse:
        mouse.write(report)

def move_mouse(dx: int, dy: int, step_delay: float = 0.005):
    """
    Move mouse by dx/dy (can be larger than 127). We split into int8 steps.
    """
    dx = int(dx)
    dy = int(dy)

    while dx != 0 or dy != 0:
        sx = clamp_int8(dx)
        sy = clamp_int8(dy)

        # convert signed to two's complement via & 0xFF in send_mouse_report
        send_mouse_report(buttons=0, dx=sx, dy=sy, wheel=0)

        dx -= sx
        dy -= sy

        if step_delay:
            time.sleep(float(step_delay))

@app.post("/mouse/move")
def mouse_move():
    """
    JSON:
    {
      "dx": 50,
      "dy": -20,
      "step_delay": 0.005   # optional
    }
    """
    data = request.get_json(force=True, silent=True) or {}

    if "dx" not in data or "dy" not in data:
        return jsonify(ok=False, error="Missing dx or dy"), 400

    dx = int(data["dx"])
    dy = int(data["dy"])
    step_delay = float(data.get("step_delay", 0.005))

    move_mouse(dx, dy, step_delay=step_delay)
    return jsonify(ok=True, dx=dx, dy=dy, step_delay=step_delay)

@app.post("/mouse/click")
def mouse_click():
    """
    JSON:
    {
      "button": "left" | "right" | "middle",
      "action": "click" | "down" | "up",   # default: click
      "hold_time": 0.05                   # only for click
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    button = (data.get("button") or "left").lower()
    action = (data.get("action") or "click").lower()
    hold_time = float(data.get("hold_time", 0.05))

    if button not in MOUSE_BUTTONS:
        return jsonify(ok=False, error="Invalid button (left/right/middle)"), 400

    mask = MOUSE_BUTTONS[button]

    if action == "down":
        send_mouse_report(buttons=mask, dx=0, dy=0, wheel=0)
    elif action == "up":
        send_mouse_report(buttons=0, dx=0, dy=0, wheel=0)
    else:  # click
        send_mouse_report(buttons=mask, dx=0, dy=0, wheel=0)
        time.sleep(hold_time)
        send_mouse_report(buttons=0, dx=0, dy=0, wheel=0)

    return jsonify(ok=True, button=button, action=action, hold_time=hold_time)

if __name__ == "__main__":
    threading.Thread(target=udp_server, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
