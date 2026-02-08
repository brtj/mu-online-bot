import base64
import mss
import numpy as np
import cv2
import pytesseract
import os

import time
import ctypes
from flask import Flask, request, Response, jsonify, send_file
import re
import requests

import win32gui
import win32api
import win32con
import win32process

import hid_api

from flask_cors import CORS

import vision_match

from PIL import Image, ImageChops

app = Flask(__name__)
CORS(app, resources={
    r"/ui/*": {"origins": [
        "http://192.168.50.200:5065",
        "http://100.67.68.58:5065",
        "http://localhost:5065"
        ]}
})

user32 = ctypes.windll.user32

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


BASE_DIR = os.path.dirname(__file__)
TEMP_DIR = os.path.join(BASE_DIR, "search_templates", "temp")
TPL_PAUSE = os.path.join(BASE_DIR, "search_templates", "autorun_pause.png")
TPL_PLAY  = os.path.join(BASE_DIR, "search_templates", "autorun_play.png")
TPL_MAP_ON = os.path.join(BASE_DIR, "search_templates", "map_on.png")
TPL_CHAT_ON = os.path.join(BASE_DIR, "search_templates", "chat_on.png")
TPL_SYSTEM_ON = os.path.join(BASE_DIR, "search_templates", "system_on.png")
TPL_INV_ON = os.path.join(BASE_DIR, "search_templates", "helper_inventory_opened.png")
TPL_HELPER_RUNS_ON = os.path.join(BASE_DIR, "search_templates", "helper_only_runs_in_filed.png")
TPL_INVENTORY_ON = os.path.join(BASE_DIR, "search_templates", "inventory_on.png")



TITLE_REGEX = re.compile(
    r"""
    Player:\s*(?P<player>[^|]+)\s*\|\|
    \s*Reset:\s*(?P<reset>\d+)\s*\|\|
    \s*Level:\s*(?P<level>\d+)
    """,
    re.IGNORECASE | re.VERBOSE
)

def parse_goldmu_title(title: str):
    m = TITLE_REGEX.search(title)
    if not m:
        return None

    return {
        "player": m.group("player").strip(),
        "reset": int(m.group("reset")),
        "level": int(m.group("level")),
        "raw": title
    }

def get_window_rect(hwnd: int):
    l, t, r, b = win32gui.GetWindowRect(hwnd)
    return {
        "left": int(l),
        "top": int(t),
        "right": int(r),
        "bottom": int(b),
        "width": int(r - l),
        "height": int(b - t),
    }

def _enum_windows():
    windows = []
    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return
        windows.append((hwnd, title))
    win32gui.EnumWindows(callback, None)
    return windows

def find_window_by_title_substring(partial_title: str):
    partial_title = (partial_title or "").strip().lower()
    if not partial_title:
        return None, "Missing 'title'"

    matches = [(hwnd, title) for hwnd, title in _enum_windows() if partial_title in title.lower()]
    if not matches:
        return None, f"No window contains title: {partial_title!r}"

    matches.sort(key=lambda x: len(x[1]), reverse=True)
    return matches[0][0], None

def force_foreground(hwnd: int):
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    else:
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

    fg = win32gui.GetForegroundWindow()
    fg_tid = win32process.GetWindowThreadProcessId(fg)[0] if fg else 0
    tgt_tid = win32process.GetWindowThreadProcessId(hwnd)[0]

    if fg_tid and fg_tid != tgt_tid:
        user32.AttachThreadInput(fg_tid, tgt_tid, True)

    win32gui.BringWindowToTop(hwnd)
    win32gui.SetForegroundWindow(hwnd)
    win32gui.SetActiveWindow(hwnd)

    if fg_tid and fg_tid != tgt_tid:
        user32.AttachThreadInput(fg_tid, tgt_tid, False)

def force_foreground_strong(hwnd):
    # 1) pokaż okno jeśli zminimalizowane
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    except Exception:
        pass

    # 2) trik "ALT" żeby Windows pozwolił na foreground
    try:
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)                 # ALT down
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)  # ALT up
    except Exception:
        pass

    # 3) foreground + focus
    win32gui.SetForegroundWindow(hwnd)
    win32gui.SetFocus(hwnd)

def set_topmost(hwnd: int, enabled: bool = True):
    insert_after = win32con.HWND_TOPMOST if enabled else win32con.HWND_NOTOPMOST
    win32gui.SetWindowPos(
        hwnd, insert_after,
        0, 0, 0, 0,
        win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
    )


def show_window_topmost(partial_title: str, keep_topmost: bool = False):
    """Bring window matching partial title above all others."""
    partial_title = (partial_title or "").strip()
    if not partial_title:
        raise ValueError("Missing 'partial_title'")

    hwnd, err = find_window_by_title_substring(partial_title)
    if err:
        raise RuntimeError(err)

    # make sure window is restored and focused before toggling topmost
    force_foreground_strong(hwnd)
    set_topmost(hwnd, True)

    if not keep_topmost:
        time.sleep(0.05)
        set_topmost(hwnd, False)

    return hwnd

def move_window_by_title(partial_title: str, x: int, y: int, w: int, h: int):
    hwnd, err = find_window_by_title_substring(partial_title)
    if err:
        raise RuntimeError(err)

    # WAŻNE: odmaksymalizuj (gry / DX)
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

    win32gui.SetWindowPos(
        hwnd,
        None,
        int(x),
        int(y),
        int(w),
        int(h),
        win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW
    )
    return hwnd

def post(url, payload):
    r = requests.post(url, json=payload, timeout=20)
    r.raise_for_status()
    return r.json() if r.content else None

def activate_window(title):
    WINDOW_API = "http://192.168.50.200:5055/window/activate-topmost"
    print("Activate window")
    post(WINDOW_API, {
    "title": title,
    "topmost": False
    })

@app.post("/window/activate-topmost")
def activate_topmost():
    data = request.get_json(force=True, silent=True) or {}
    title = data.get("title", "")
    topmost = bool(data.get("topmost", True))

    hwnd, err = find_window_by_title_substring(title)
    if err:
        return jsonify(ok=False, error=err), 400

    try:
        force_foreground(hwnd)
        time.sleep(0.05)
        set_topmost(hwnd, topmost)
        return jsonify(ok=True, hwnd=int(hwnd), topmost=topmost, title=win32gui.GetWindowText(hwnd))
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.post("/window/state")
def window_state():
    data = request.get_json(force=True, silent=True) or {}
    title = data.get("title", "")

    hwnd, err = find_window_by_title_substring(title)
    if err:
        return jsonify(ok=False, error=err), 400

    try:
        topmost = bool(win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST)
        return jsonify(
            ok=True,
            hwnd=int(hwnd),
            topmost=topmost,
            title=win32gui.GetWindowText(hwnd)
        )
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.post("/window/move")
def api_window_move():
    """
    JSON:
    {
      "title": "GoldMU || Player: AleElfisko",
      "x": 0,
      "y": 0,
      "w": 817,
      "h": 640
    }
    """
    data = request.get_json(force=True, silent=True) or {}

    title = data.get("title")
    if not title:
        return jsonify(ok=False, error="Missing 'title'"), 400

    try:
        hwnd = move_window_by_title(
            partial_title=title,
            x=data.get("x", 0),
            y=data.get("y", 0),
            w=data.get("w", 817),
            h=data.get("h", 640),
        )
        return jsonify(ok=True, hwnd=int(hwnd))
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.post("/window/resolve-title")
def api_window_resolve_title():
    """
    JSON:
    { "title": "GoldMU || Player: AleElfisko" }

    Zwraca:
    { "ok": true, "hwnd": 123456, "title_full": "..." }
    """
    data = request.get_json(force=True, silent=True) or {}
    partial = (data.get("title") or "").strip()
    if not partial:
        return jsonify(ok=False, error="Missing 'title'"), 400

    hwnd, err = find_window_by_title_substring(partial)
    if err:
        return jsonify(ok=False, error=err), 404

    full_title = win32gui.GetWindowText(hwnd)
    return jsonify(ok=True, hwnd=int(hwnd), title_full=full_title)

@app.post("/window/parse-title")
def api_window_parse_title():
    """
    JSON:
    { "title": "GoldMU || Player: AleElfisko" }

    Response:
    {
      "ok": true,
      "hwnd": 1376706,
      "player": "AleElfisko",
      "reset": 3,
      "level": 396,
      "raw": "...",
      "rect": {
        "left": 0,
        "top": 0,
        "right": 817,
        "bottom": 640,
        "width": 817,
        "height": 640
      }
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    partial = (data.get("title") or "").strip()

    if not partial:
        return jsonify(ok=False, error="Missing 'title'"), 400

    hwnd, err = find_window_by_title_substring(partial)
    if err:
        return jsonify(ok=False, error=err), 404

    full_title = win32gui.GetWindowText(hwnd)
    parsed = parse_goldmu_title(full_title)

    if not parsed:
        return jsonify(
            ok=False,
            error="Title format not recognized",
            raw=full_title
        ), 422

    rect = get_window_rect(hwnd)

    return jsonify(
        ok=True,
        hwnd=int(hwnd),
        rect=rect,
        **parsed
    )


def check_chat_on(title):
    SCREEN_MAP_URL = "http://192.168.50.200:5055/screen/chat"
    time.sleep(0.4)  
    payload = {
        "title": title,
        "rect": { "x": 268, "y": 536, "w": 26, "h": 26 },
        "thr": 0.88,
        "pad": 2
    }
    r = post(SCREEN_MAP_URL, payload)
    time.sleep(0.4)
    return r["state"]

@app.post("/keys/send-enter")
def api_send_enter():
    """
    JSON:
    {
      "title": "GoldMU || Player: AleElfisko",   // fragment tytułu okna
      "timeout": 3                              // opcjonalnie (sekundy)
    }
    """
    data = request.get_json(force=True, silent=True) or {}

    title = (data.get("title") or "").strip()
    url = (data.get("url") or "http://192.168.50.228:5000/keyboard/text").strip()
    timeout = float(data.get("timeout", 3))

    if not title:
        return jsonify(ok=False, error="Missing 'title'"), 400

    hwnd, err = find_window_by_title_substring(title)
    if err:
        return jsonify(ok=False, error=err), 404

    try:
        # aktywuj okno (ważne: czasem Windows blokuje bez admina / bez interakcji usera)
        force_foreground(hwnd)
        time.sleep(0.4)
        hid_api.press_enter()
        time.sleep(0.1)

        return jsonify(
            ok=True,
            hwnd=int(hwnd),
            activated_title=win32gui.GetWindowText(hwnd),
            sent_to=url,
            response="pressed",
        ), 200

    except requests.RequestException as e:
        return jsonify(ok=False, error=f"Request failed: {e}", hwnd=int(hwnd), sent_to=url), 502
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.post("/send_message")
def api_send_message():
    """
    JSON:
    {
      "title": "GoldMU || Player: AleElfisko",   // fragment tytułu okna
      "text": "hello world",                    // tekst do wysłania
      "url": "http://192.168.50.228:5000/keyboard/text",  // opcjonalnie, default jak niżej
      "timeout": 3                              // opcjonalnie (sekundy)
    }
    """
    data = request.get_json(force=True, silent=True) or {}

    title = (data.get("title") or "").strip()
    text = data.get("text")
    url = (data.get("url") or "http://192.168.50.228:5000/keyboard/text").strip()
    timeout = float(data.get("timeout", 40))

    print(data)

    if not title:
        return jsonify(ok=False, error="Missing 'title'"), 400
    if text is None:
        return jsonify(ok=False, error="Missing 'text'"), 400

    hwnd, err = find_window_by_title_substring(title)
    if err:
        return jsonify(ok=False, error=err), 404

    print(f"hwnd: {hwnd}, error: {err}")
    try:
        # aktywuj okno (ważne: czasem Windows blokuje bez admina / bez interakcji usera)
        force_foreground(hwnd)
        time.sleep(0.5)
        chat_on = check_chat_on(title)
        if chat_on == "CHAT ON":
            SGO_TO_XY_URL = "http://192.168.50.200:5055/mouse/goto_xy_relative"
            MOUSE_CLICK_URL = "http://192.168.50.228:5000/mouse/click"
            payload = {
                "title": title,
                "target_x": 534,
                "target_y": 571,
                "require_inside": False
            }
            r = post(SGO_TO_XY_URL, payload)
            time.sleep(0.25)
            payload = {
                "button": "left",
                "action": "click",
                "hold_time": 0.5
            }
            r = post(MOUSE_CLICK_URL,payload)
            time.sleep(0.3)
            hid_api.press_enter()
            time.sleep(0.3)

        hid_api.press_enter()
        time.sleep(0.3)
        hid_api.press_tab()
        time.sleep(0.3)
        hid_api.press_backspace()
        time.sleep(0.3)
        hid_api.press_tab()
        time.sleep(0.3)

        payload = {
            "text": text
        }
        try:
           r = post(url, payload)
           print("OK, response:", r)
        except Exception as e:
           print("POST FAILED:", repr(e))
           # tu możesz zdecydować co dalej:
           return {"ok": False, "error": str(e)}
        
        time.sleep(0.5)
        hid_api.press_enter()
        

        # spróbuj zdekodować JSON z odpowiedzi, jak się nie da to zwróć tekst
        try:
            payload = r
        except Exception:
            payload = {"raw": r}

        return jsonify(
            ok=True,
            hwnd=int(hwnd),
            activated_title=win32gui.GetWindowText(hwnd),
            sent_to=url,
            response=payload,
        ), 200

    except requests.RequestException as e:
        return jsonify(ok=False, error=f"Request failed: {e}", hwnd=int(hwnd), sent_to=url), 502
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.get("/mouse/position")
def api_mouse_position():
    try:
        x, y = win32api.GetCursorPos()
        return jsonify(ok=True, x=int(x), y=int(y))
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

def get_pos_relative_local(title: str) -> dict:
    title = (title or "").strip()
    if not title:
        return {"ok": False, "error": "Missing 'title'"}

    hwnd, err = find_window_by_title_substring(title)
    if err:
        return {"ok": False, "error": err}

    cx, cy = win32api.GetCursorPos()
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)

    rel_x = cx - left
    rel_y = cy - top
    inside = left <= cx <= right and top <= cy <= bottom

    return {
        "ok": True,
        "x": int(rel_x),
        "y": int(rel_y),
        "inside": inside,
        "window": {"left": left, "top": top, "right": right, "bottom": bottom},
        "cursor": {"x": cx, "y": cy},
    }


@app.post("/mouse/position-relative")
def api_mouse_position_relative():
    try:
        data = request.get_json(force=True, silent=True) or {}
        title = (data.get("title") or "").strip()
        res = get_pos_relative_local(title)
        code = 200 if res.get("ok") else 400
        return jsonify(**res), code
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

def get_pos():
    POS_URL = "http://192.168.50.200:5055/mouse/position"
    r = requests.get(POS_URL, timeout=3)
    r.raise_for_status()
    j = r.json()
    return int(j["x"]), int(j["y"])

def adaptive_step(err):
    a = abs(err)
    if a > 500:
        return 250
    if a > 250:
        return 150
    if a > 200:
        return 100
    if a > 150:
        return 75
    if a > 100:
        return 50
    if a > 80:
        return 40
    if a > 60:
        return 30
    if a > 40:
        return 20
    if a > 20:
        return 10
    if a > 10:
        return 5
    if a > 4:
        return 2
    return 1

@app.post("/mouse/goto_xy_relative")
def api_mouse_goto_xy_relative():
    """
    JSON:
    {
      "title": "GoldMU",          # wymagane: okno odniesienia
      "target_x": 1218,           # wymagane: X RELATYWNE do okna
      "target_y": 320,            # wymagane: Y RELATYWNE do okna
      "tolerance": 1,
      "max_iters": 600,
      "sleep_s": 0.012,
      "require_inside": true      # opcjonalnie: default true
    }
    """
    data = request.get_json(force=True, silent=True) or {}

    title = (data.get("title") or "").strip()
    if not title:
        return jsonify(ok=False, error="Missing title"), 400

    if "target_x" not in data or "target_y" not in data:
        return jsonify(ok=False, error="Missing target_x or target_y"), 400

    try:
        target_x = int(data.get("target_x"))
        target_y = int(data.get("target_y"))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="target_x/target_y must be integers"), 400

    try:
        tolerance = int(data.get("tolerance", 1))
        max_iters = int(data.get("max_iters", 600))
        sleep_s = float(data.get("sleep_s", 0.012))
        require_inside = bool(data.get("require_inside", True))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="tolerance/max_iters/sleep_s have invalid type"), 400

    tolerance = max(0, tolerance)
    max_iters = max(1, max_iters)
    sleep_s = max(0.0, sleep_s)

    for i in range(max_iters):
        pos = get_pos_relative_local(title)
        if not pos.get("ok"):
            return jsonify(ok=False, reason="position_error", error=pos.get("error")), 502

        if require_inside and not pos.get("inside", False):
            return jsonify(ok=False, reason="cursor_outside_window", pos=pos), 409

        x = int(pos["x"])
        y = int(pos["y"])

        ex = target_x - x
        ey = target_y - y

        if abs(ex) <= tolerance and abs(ey) <= tolerance:
            return jsonify(ok=True, iters=i, x=x, y=y, pos=pos)

        sx = adaptive_step(ex)
        sy = adaptive_step(ey)

        dx = 0 if ex == 0 else (sx if ex > 0 else -sx)
        dy = 0 if ey == 0 else (sy if ey > 0 else -sy)

        hid_api.move(dx, dy)
        time.sleep(sleep_s)

    pos = get_pos_relative_local(title)
    if pos.get("ok"):
        return jsonify(ok=False, reason="max_iters", x=pos["x"], y=pos["y"], pos=pos)
    return jsonify(ok=False, reason="max_iters", error=pos.get("error"))


@app.post("/mouse/goto_xy")
def api_mouse_goto_xy():
    """
    JSON:
    {
      "target_x": 1218,          # wymagane: docelowe X (ekran)
      "target_y": 320,           # wymagane: docelowe Y (ekran)
      "tolerance": 1,            # opcjonalnie: ile px tolerancji
      "max_iters": 600,          # opcjonalnie: limit kroków pętli
      "sleep_s": 0.012           # opcjonalnie: opóźnienie między mikro-ruchami
    }

    Response:
    {
      "ok": true,
      "iters": 123,
      "x": 1218,
      "y": 320
    }
    lub
    {
      "ok": false,
      "reason": "max_iters",
      "x": 1200,
      "y": 310
    }
    """
    data = request.get_json(force=True, silent=True) or {}

    # --- wymagane ---
    if "target_x" not in data or "target_y" not in data:
        return jsonify(ok=False, error="Missing target_x or target_y"), 400

    try:
        target_x = int(data.get("target_x"))
        target_y = int(data.get("target_y"))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="target_x/target_y must be integers"), 400

    # --- opcjonalne ---
    try:
        tolerance = int(data.get("tolerance", 1))
        max_iters = int(data.get("max_iters", 600))
        sleep_s = float(data.get("sleep_s", 0.012))
    except (TypeError, ValueError):
        return jsonify(ok=False, error="tolerance/max_iters/sleep_s have invalid type"), 400

    if tolerance < 0:
        tolerance = 0
    if max_iters < 1:
        max_iters = 1
    if sleep_s < 0:
        sleep_s = 0.0

    for i in range(max_iters):
        x, y = get_pos()
        ex = target_x - x
        ey = target_y - y

        if abs(ex) <= tolerance and abs(ey) <= tolerance:
            return jsonify(ok=True, iters=i, x=x, y=y)

        sx = adaptive_step(ex)
        sy = adaptive_step(ey)

        dx = 0 if ex == 0 else (sx if ex > 0 else -sx)
        dy = 0 if ey == 0 else (sy if ey > 0 else -sy)

        hid_api.move(dx, dy)
        time.sleep(sleep_s)

    x, y = get_pos()
    return jsonify(ok=False, reason="max_iters", x=x, y=y)


def ocr_text_from_bgr_generic(
    img_bgr,
    psm: int = 7,
    whitelist: str | None = None,
    upscale: float = 3.0,
    pad_border: int = 10,
    invert: bool = True,
    invert_stage: str = "pre",          # "pre" | "post"
    threshold_mode: str = "otsu",       # "otsu" | "adaptive" | "fixed"
    fixed_thr: int = 160,
    morph_close: bool = False,
    morph_kernel: tuple[int, int] = (2, 2),
    morph_iter: int = 1,
    save_debug: bool = True,
    debug_prefix: str = "ocr_generic",
    debug_dir: str | None = None,
):
    """
    Generyczny OCR pod małe ROI z gry / UI.

    Zwraca:
      (text: str, th: np.ndarray)  # th = finalny obraz wejściowy dla OCR (po preprocessie)

    Debug pliki (jeśli save_debug=True):
      <debug_prefix>_raw.png
      <debug_prefix>_gray.png
      <debug_prefix>_upscaled.png
      <debug_prefix>_blur.png
      <debug_prefix>_invert_pre.png
      <debug_prefix>_th.png
      <debug_prefix>_invert_post.png
      <debug_prefix>_morph.png
      <debug_prefix>_border.png
    """
    if debug_dir is None:
        debug_dir = TEMP_DIR

    def _dump(name: str, im):
        if not save_debug:
            return
        try:
            os.makedirs(debug_dir, exist_ok=True)
            cv2.imwrite(os.path.join(debug_dir, f"{debug_prefix}_{name}.png"), im)
        except Exception:
            pass

    inv_stage = (invert_stage or "pre").strip().lower()
    if inv_stage not in ("pre", "post"):
        inv_stage = "pre"

    # 0) raw
    _dump("raw", img_bgr)

    # 1) grayscale
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    _dump("gray", gray)

    # 2) upscale
    if upscale and upscale != 1.0:
        gray = cv2.resize(
            gray, None,
            fx=upscale, fy=upscale,
            interpolation=cv2.INTER_CUBIC
        )
        _dump("upscaled", gray)

    # 3) blur
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _dump("blur", gray)

    # 3.5) invert PRE (dla białego na czarnym, zanim zrobisz threshold)
    if invert and inv_stage == "pre":
        gray = cv2.bitwise_not(gray)
        _dump("invert_pre", gray)

    # 4) threshold
    tm = (threshold_mode or "otsu").strip().lower()
    if tm == "adaptive":
        th = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31, 5
        )
    elif tm == "fixed":
        _, th = cv2.threshold(gray, int(fixed_thr), 255, cv2.THRESH_BINARY)
    else:  # "otsu"
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    _dump("th", th)

    # 5) invert POST (klasycznie po threshold)
    if invert and inv_stage == "post":
        th = cv2.bitwise_not(th)
        _dump("invert_post", th)

    # 6) morph close
    if morph_close:
        kernel = np.ones(tuple(morph_kernel), np.uint8)
        th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=int(morph_iter))
        _dump("morph", th)

    # 7) border
    if pad_border and pad_border > 0:
        th = cv2.copyMakeBorder(
            th,
            int(pad_border), int(pad_border),
            int(pad_border), int(pad_border),
            cv2.BORDER_CONSTANT,
            value=255
        )
        _dump("border", th)

    # 8) tesseract
    cfg = f"--oem 1 --psm {int(psm)} -c preserve_interword_spaces=1"
    if whitelist:
        wl = str(whitelist).replace('"', "").replace("'", "")
        cfg += f' -c tessedit_char_whitelist="{wl}"'

    text = pytesseract.image_to_string(th, config=cfg).strip()
    return text, th


@app.post("/screen/ocr_generic")
def api_screen_ocr_generic():
    """
    JSON:
    {
      "rect": {"x": 330, "y": 440, "w": 50, "h": 25},
      "title": "GoldMU || Player: AleElfisko",    # opcjonalnie
      "psm": 7,                                   # opcjonalnie
      "whitelist": "xX0123456789(),",             # opcjonalnie
      "debug_image": false,                       # opcjonalnie (base64 PNG)

      # screenshot tuning
      "pad": 2,

      # preprocess tuning
      "upscale": 3.0,
      "invert": true,
      "invert_stage": "pre",                      # "pre" | "post" (domyślnie "pre")
      "threshold": "otsu",                        # "otsu" | "adaptive" | "fixed"
      "fixed_thr": 160,
      "morph_close": false,                       # domyślnie false
      "pad_border": 10                            # domyślnie 10 (biała ramka)
    }
    """

    data = request.get_json(force=True, silent=True) or {}
    rect = data.get("rect") or {}

    title = (data.get("title") or "").strip()
    psm = int(data.get("psm", 7))
    whitelist = (data.get("whitelist") or "").strip()
    debug_image = bool(data.get("debug_image", False))

    # screenshot padding
    pad = int(data.get("pad", 2))

    # preprocess params
    upscale = float(data.get("upscale", 3.0))
    invert = bool(data.get("invert", True))
    invert_stage = (data.get("invert_stage") or "pre").strip().lower()  # pre/post
    threshold_mode = (data.get("threshold") or "otsu").strip().lower()
    fixed_thr = int(data.get("fixed_thr", 160))
    morph_close = bool(data.get("morph_close", False))
    pad_border = int(data.get("pad_border", 10))

    # --- validate rect ---
    try:
        x = int(rect["x"])
        y = int(rect["y"])
        w = int(rect["w"])
        h = int(rect["h"])
        if w <= 0 or h <= 0:
            raise ValueError("w/h must be > 0")
    except Exception:
        return jsonify(ok=False, error="Invalid rect, expected {x,y,w,h}"), 400

    hwnd = None

    # --- relative to window if title ---
    if title:
        hwnd, err = find_window_by_title_substring(title)
        if err:
            return jsonify(ok=False, error=err), 404
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        abs_x = left + x
        abs_y = top + y
    else:
        abs_x, abs_y = x, y

    # --- padding ---
    abs_x_p = max(0, abs_x - pad)
    abs_y_p = max(0, abs_y - pad)
    w_p = w + 2 * pad
    h_p = h + 2 * pad

    monitor = {"left": abs_x_p, "top": abs_y_p, "width": w_p, "height": h_p}

    try:
        # --- screenshot ---
        with mss.mss() as sct:
            shot = sct.grab(monitor)
            img = np.array(shot)  # BGRA
            roi_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # --- OCR ---
        text, th = ocr_text_from_bgr_generic(
            roi_bgr,
            psm=psm,
            whitelist=whitelist,
            upscale=upscale,
            invert=invert,
            invert_stage=invert_stage,
            threshold_mode=threshold_mode,
            fixed_thr=fixed_thr,
            morph_close=morph_close,
            pad_border=pad_border,
            save_debug=True,
            debug_prefix="ocr_generic",
            debug_dir=TEMP_DIR,
        )

        text = re.sub(r"\s+", " ", (text or "")).strip()

        resp = {
            "ok": True,
            "hwnd": int(hwnd) if hwnd else None,
            "rect_used": {"x": abs_x_p, "y": abs_y_p, "w": w_p, "h": h_p},
            "raw_text": text,
            "ocr_cfg": {
                "psm": psm,
                "pad": pad,
                "upscale": upscale,
                "invert": invert,
                "invert_stage": invert_stage,
                "threshold": threshold_mode,
                "fixed_thr": fixed_thr,
                "morph_close": morph_close,
                "pad_border": pad_border,
                "whitelist": whitelist,
            },
        }

        if debug_image:
            ok, buf = cv2.imencode(".png", th)
            if ok:
                resp["debug_png_base64"] = base64.b64encode(buf).decode("ascii")

        return jsonify(resp), 200

    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


def ocr_text_from_bgr(img_bgr, psm=7, whitelist=None, upscale=3.0):
    # DEBUG 1: surowy ROI
    cv2.imwrite(os.path.join(TEMP_DIR, "location_roi_raw.png"), img_bgr)

    # 1) grayscale
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    cv2.imwrite(os.path.join(TEMP_DIR, "location_gray.png"), gray)

    # 2) upscale
    if upscale and upscale != 1.0:
        gray = cv2.resize(
            gray, None,
            fx=upscale, fy=upscale,
            interpolation=cv2.INTER_CUBIC
        )
        cv2.imwrite(os.path.join(TEMP_DIR, "location_gray_upscaled.png"), gray)

    # 3) blur
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    cv2.imwrite(os.path.join(TEMP_DIR, "location_blur.png"), gray)

    # 4) otsu
    th = cv2.threshold(
        gray, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )[1]
    cv2.imwrite(os.path.join(TEMP_DIR, "location_otsu.png"), th)

    # 5) invert
    th = cv2.bitwise_not(th)
    cv2.imwrite(os.path.join(TEMP_DIR, "location_invert.png"), th)

    # 6) morph close
    kernel = np.ones((2, 2), np.uint8)
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel, iterations=1)
    cv2.imwrite(os.path.join(TEMP_DIR, "location_morph.png"), th)

    # 7) border
    th = cv2.copyMakeBorder(
        th, 10, 10, 10, 10,
        cv2.BORDER_CONSTANT, value=255
    )
    cv2.imwrite(os.path.join(TEMP_DIR, "location_border.png"), th)

    # 8) tesseract
    cfg = f"--oem 1 --psm {psm} -c preserve_interword_spaces=1"
    if whitelist:
        cfg += f' -c tessedit_char_whitelist="{whitelist}"'

    text = pytesseract.image_to_string(th, config=cfg).strip()
    return text, th

@app.post("/screen/ocr")
def api_screen_ocr():
    """
    JSON:
    {
      "rect": {"x": 10, "y": 10, "w": 220, "h": 28},
      "title": "GoldMU",                   # opcjonalnie: rect liczony względem okna
      "psm": 7,                            # opcjonalnie
      "whitelist": "Kartan 0123456789(),", # opcjonalnie
      "debug_image": false,                # opcjonalnie: zwróci PNG base64 z preprocessu

      # (opcjonalne tuningi, jak chcesz):
      "pad": 2,                            # doda margines do rect (px) zanim zrobi screenshot
      "upscale": 3.0                       # skala powiększenia dla OCR
    }
    """
    LOCATION_ALIASES = {
        "Adlans": "Atlans",
        "Alans": "Atlans",
        "Aalans": "Atlans",
        "Salans": "Atlans",
        "Allans": "Atlans",
        "INCleon": "LaCleon"
    }
    data = request.get_json(force=True, silent=True) or {}
    rect = data.get("rect") or {}

    title = (data.get("title") or "").strip()
    psm = int(data.get("psm", 7))

    # lepszy default: zawiera spację
    whitelist = (data.get("whitelist") or "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789(),. ").strip()

    debug_image = bool(data.get("debug_image", False))

    # dodatkowe tuningi
    pad = int(data.get("pad", 2))           # margines do ROI (często ratuje nawiasy i cyfry)
    upscale = float(data.get("upscale", 3.0))

    # walidacja rect
    try:
        x = int(rect.get("x"))
        y = int(rect.get("y"))
        w = int(rect.get("w"))
        h = int(rect.get("h"))
        if w <= 0 or h <= 0:
            raise ValueError("w/h must be > 0")
    except Exception:
        return jsonify(ok=False, error="Missing/invalid rect. Expected rect: {x,y,w,h}"), 400

    hwnd = None

    # rect względny do okna (jeśli podano title)
    if title:
        hwnd, err = find_window_by_title_substring(title)
        if err:
            return jsonify(ok=False, error=err), 404
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        abs_x = left + x
        abs_y = top + y
    else:
        abs_x, abs_y = x, y

    # dodaj margines do screenshotu (żeby nie ucinać znaków)
    abs_x_p = max(0, abs_x - pad)
    abs_y_p = max(0, abs_y - pad)
    w_p = w + 2 * pad
    h_p = h + 2 * pad

    monitor = {"left": abs_x_p, "top": abs_y_p, "width": w_p, "height": h_p}

    try:
        # screenshot ROI
        with mss.mss() as sct:
            shot = sct.grab(monitor)
            img = np.array(shot)  # BGRA
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # OCR
        text, th = ocr_text_from_bgr(img_bgr, psm=psm, whitelist=whitelist, upscale=upscale)

        # parsowanie "Kartan (104, 116)" — bardziej tolerancyjne na OCR (przecinek/kropka, nawiasy)
        parsed = None
        m = re.search(
            r"^\s*([A-Za-z0-9_ ]+?)\s*[\(\[]\s*(-?\d+)\s*[,\.]+\s*(-?\d+)\s*[\)\]]\s*$",
            text
        )
        if m:
            raw_name = m.group(1).strip()
            fixed_name = LOCATION_ALIASES.get(raw_name, raw_name)
            parsed = {"name": fixed_name, "x": int(m.group(2)), "y": int(m.group(3))}

        resp = {
            "ok": True,
            "hwnd": int(hwnd) if hwnd else None,
            "rect_used": {"x": abs_x_p, "y": abs_y_p, "w": w_p, "h": h_p},
            "raw_text": text,
            "parsed": parsed,
            "ocr_cfg": {"psm": psm, "upscale": upscale, "pad": pad},
        }

        if debug_image:
            ok, buf = cv2.imencode(".png", th)
            if ok:
                resp["debug_png_base64"] = base64.b64encode(buf.tobytes()).decode("ascii")

        return jsonify(resp), 200

    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.post("/screen/capture.png")
def api_screen_capture_png():
    """
    JSON:
    {
      "rect": {"x": 10, "y": 10, "w": 220, "h": 28},
      "title": "GoldMU"   // opcjonalnie: rect liczony względem okna
    }

    Response:
      Content-Type: image/png
    """
    data = request.get_json(force=True, silent=True) or {}
    rect = data.get("rect") or {}
    title = (data.get("title") or "").strip()

    try:
        x = int(rect.get("x"))
        y = int(rect.get("y"))
        w = int(rect.get("w"))
        h = int(rect.get("h"))
        if w <= 0 or h <= 0:
            raise ValueError()
    except Exception:
        return Response("Invalid rect", status=400)

    abs_x, abs_y = x, y
    hwnd = None

    if title:
        hwnd, err = find_window_by_title_substring(title)
        if err:
            return Response(err, status=404)
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        abs_x = left + x
        abs_y = top + y

    monitor = {
        "left": abs_x,
        "top": abs_y,
        "width": w,
        "height": h,
    }

    try:
        with mss.mss() as sct:
            shot = sct.grab(monitor)
            img = np.array(shot)  # BGRA
            img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        ok, buf = cv2.imencode(".png", img_bgr)
        if not ok:
            return Response("PNG encode failed", status=500)

        return Response(
            buf.tobytes(),
            mimetype="image/png",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
            },
        )

    except Exception as e:
        return Response(str(e), status=500)


def _match_icon(roi_bgr, template_path):
    tpl = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
    if tpl is None:
        raise RuntimeError(f"Template not found: {template_path}")

    if tpl.shape[2] == 4:  # alpha
        tpl_bgr = tpl[:, :, :3]
        mask = cv2.threshold(tpl[:, :, 3], 0, 255, cv2.THRESH_BINARY)[1]
        res = cv2.matchTemplate(
            roi_bgr, tpl_bgr, cv2.TM_CCORR_NORMED, mask=mask
        )
    else:
        tpl_bgr = tpl
        res = cv2.matchTemplate(
            roi_bgr, tpl_bgr, cv2.TM_CCOEFF_NORMED
        )

    _, score, _, loc = cv2.minMaxLoc(res)
    return float(score), loc, tpl_bgr.shape[:2]





@app.post("/screen/helper_box_in_filed")
def api_screen_helper_box_state():
    """
    JSON:
    {
      "rect": {"x": 295, "y": 228, "w": 225, "h": 116},
      "title": "GoldMU",      # opcjonalnie
      "thr": 0.88,            # opcjonalnie
      "pad": 2,               # opcjonalnie
      "debug_image": false    # opcjonalnie
    }

    Response:
    {
      "ok": true,
      "state": "BOX ON" | "BOX OFF",
      "score": 0.93,
      "thr": 0.88,
      "rect_used": {...},
      "hwnd": 123456,
      "icon": {...}           # opcjonalnie gdy BOX ON
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    rect = data.get("rect") or {}

    title = (data.get("title") or "").strip()
    thr = float(data.get("thr") or 0.88)
    pad = int(data.get("pad") or 2)
    debug_image = bool(data.get("debug_image") or False)

    # walidacja rect
    try:
        x = int(rect.get("x"))
        y = int(rect.get("y"))
        w = int(rect.get("w"))
        h = int(rect.get("h"))
        if w <= 0 or h <= 0:
            raise ValueError
    except Exception:
        return jsonify(ok=False, error="Invalid rect {x,y,w,h}"), 400

    if not os.path.exists(TPL_HELPER_RUNS_ON):
        return jsonify(ok=False, error=f"Missing template file: {TPL_HELPER_RUNS_ON}"), 500

    hwnd = None
    if title:
        hwnd, err = find_window_by_title_substring(title)
        if err:
            return jsonify(ok=False, error=err), 404
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        abs_x = left + x
        abs_y = top + y
    else:
        abs_x, abs_y = x, y

    # padding
    abs_x_p = max(0, abs_x - pad)
    abs_y_p = max(0, abs_y - pad)
    w_p = w + 2 * pad
    h_p = h + 2 * pad

    monitor = {"left": abs_x_p, "top": abs_y_p, "width": w_p, "height": h_p}

    try:
        # screenshot ROI
        with mss.mss() as sct:
            shot = sct.grab(monitor)
            roi = np.array(shot)  # BGRA
            roi_bgr = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)

        # DEBUG: surowy ROI
        cv2.imwrite(os.path.join(TEMP_DIR, "helper_box_filed_raw.png"), roi_bgr)

        # match template
        score_map, loc_map, size_map = _match_icon(roi_bgr, TPL_HELPER_RUNS_ON)

        state = "BOX ON" if score_map >= thr else "BOX OFF"

        resp = {
            "ok": True,
            "state": state,
            "score": float(score_map),
            "thr": float(thr),
            "rect_used": {"x": abs_x_p, "y": abs_y_p, "w": w_p, "h": h_p},
            "hwnd": int(hwnd) if hwnd else None,
        }

        # opcjonalnie: gdzie wykryto ikonę (tylko jeśli ON)
        if state == "BOX ON":
            thh, tww = size_map  # (h, w)
            resp["icon"] = {
                "screen_x": int(abs_x_p + loc_map[0]),
                "screen_y": int(abs_y_p + loc_map[1]),
                "w": int(tww),
                "h": int(thh),
            }

        if debug_image:
            ok, buf = cv2.imencode(".png", roi_bgr)
            if ok:
                resp["debug_roi_png_base64"] = base64.b64encode(buf.tobytes()).decode("ascii")

        return jsonify(resp), 200

    except Exception as e:
        return jsonify(ok=False, error=f"{type(e).__name__}: {e}"), 500

@app.post("/screen/helper_inventory")
def api_screen_helper_inventory_state():
    """
    JSON:
    {
      "rect": {"x": 295, "y": 228, "w": 225, "h": 116},
      "title": "GoldMU",      # opcjonalnie
      "thr": 0.88,            # opcjonalnie
      "pad": 2,               # opcjonalnie
      "debug_image": false    # opcjonalnie
    }

    Response:
    {
      "ok": true,
      "state": "INV ON" | "INV OFF",
      "score": 0.93,
      "thr": 0.88,
      "rect_used": {...},
      "hwnd": 123456,
      "icon": {...}           # opcjonalnie gdy INV ON
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    rect = data.get("rect") or {}

    title = (data.get("title") or "").strip()
    thr = float(data.get("thr") or 0.88)
    pad = int(data.get("pad") or 2)
    debug_image = bool(data.get("debug_image") or False)

    # walidacja rect
    try:
        x = int(rect.get("x"))
        y = int(rect.get("y"))
        w = int(rect.get("w"))
        h = int(rect.get("h"))
        if w <= 0 or h <= 0:
            raise ValueError
    except Exception:
        return jsonify(ok=False, error="Invalid rect {x,y,w,h}"), 400

    if not os.path.exists(TPL_INV_ON):
        return jsonify(ok=False, error=f"Missing template file: {TPL_INV_ON}"), 500

    hwnd = None
    if title:
        hwnd, err = find_window_by_title_substring(title)
        if err:
            return jsonify(ok=False, error=err), 404
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        abs_x = left + x
        abs_y = top + y
    else:
        abs_x, abs_y = x, y

    # padding
    abs_x_p = max(0, abs_x - pad)
    abs_y_p = max(0, abs_y - pad)
    w_p = w + 2 * pad
    h_p = h + 2 * pad

    monitor = {"left": abs_x_p, "top": abs_y_p, "width": w_p, "height": h_p}

    try:
        # screenshot ROI
        with mss.mss() as sct:
            shot = sct.grab(monitor)
            roi = np.array(shot)  # BGRA
            roi_bgr = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)

        # DEBUG: surowy ROI
        cv2.imwrite(os.path.join(TEMP_DIR, "helper_inv_raw.png"), roi_bgr)

        # match template
        score_map, loc_map, size_map = _match_icon(roi_bgr, TPL_INV_ON)

        state = "INV ON" if score_map >= thr else "INV OFF"

        resp = {
            "ok": True,
            "state": state,
            "score": float(score_map),
            "thr": float(thr),
            "rect_used": {"x": abs_x_p, "y": abs_y_p, "w": w_p, "h": h_p},
            "hwnd": int(hwnd) if hwnd else None,
        }

        # opcjonalnie: gdzie wykryto ikonę (tylko jeśli ON)
        if state == "INV ON":
            thh, tww = size_map  # (h, w)
            resp["icon"] = {
                "screen_x": int(abs_x_p + loc_map[0]),
                "screen_y": int(abs_y_p + loc_map[1]),
                "w": int(tww),
                "h": int(thh),
            }

        if debug_image:
            ok, buf = cv2.imencode(".png", roi_bgr)
            if ok:
                resp["debug_roi_png_base64"] = base64.b64encode(buf.tobytes()).decode("ascii")

        return jsonify(resp), 200

    except Exception as e:
        return jsonify(ok=False, error=f"{type(e).__name__}: {e}"), 500


@app.post("/screen/inventory_state")
def api_screen_inventory_state():
    """
    JSON:
    {
      "rect": {"x": 630, "y": 496, "w": 100, "h": 40},
      "title": "GoldMU",      # opcjonalnie
      "thr": 0.88,            # opcjonalnie
      "pad": 2,               # opcjonalnie
      "debug_image": false    # opcjonalnie
    }

    Response:
    {
      "ok": true,
      "state": "INV ON" | "INV OFF",
      "score": 0.93,
      "thr": 0.88,
      "rect_used": {...},
      "hwnd": 123456,
      "icon": {...}           # opcjonalnie gdy INV ON
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    rect = data.get("rect") or {}

    title = (data.get("title") or "").strip()
    thr = float(data.get("thr") or 0.88)
    pad = int(data.get("pad") or 2)
    debug_image = bool(data.get("debug_image") or False)

    # walidacja rect
    try:
        x = int(rect.get("x"))
        y = int(rect.get("y"))
        w = int(rect.get("w"))
        h = int(rect.get("h"))
        if w <= 0 or h <= 0:
            raise ValueError
    except Exception:
        return jsonify(ok=False, error="Invalid rect {x,y,w,h}"), 400

    if not os.path.exists(TPL_INVENTORY_ON):
        return jsonify(ok=False, error=f"Missing template file: {TPL_INVENTORY_ON}"), 500

    hwnd = None
    if title:
        hwnd, err = find_window_by_title_substring(title)
        if err:
            return jsonify(ok=False, error=err), 404
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        abs_x = left + x
        abs_y = top + y
    else:
        abs_x, abs_y = x, y

    # padding
    abs_x_p = max(0, abs_x - pad)
    abs_y_p = max(0, abs_y - pad)
    w_p = w + 2 * pad
    h_p = h + 2 * pad

    monitor = {"left": abs_x_p, "top": abs_y_p, "width": w_p, "height": h_p}

    try:
        # screenshot ROI
        with mss.mss() as sct:
            shot = sct.grab(monitor)
            roi = np.array(shot)  # BGRA
            roi_bgr = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)

        # DEBUG: surowy ROI
        cv2.imwrite(os.path.join(TEMP_DIR, "inventory_raw.png"), roi_bgr)

        # match template
        score_map, loc_map, size_map = _match_icon(roi_bgr, TPL_INVENTORY_ON)

        state = "INV ON" if score_map >= thr else "INV OFF"

        resp = {
            "ok": True,
            "state": state,
            "score": float(score_map),
            "thr": float(thr),
            "rect_used": {"x": abs_x_p, "y": abs_y_p, "w": w_p, "h": h_p},
            "hwnd": int(hwnd) if hwnd else None,
        }

        # opcjonalnie: gdzie wykryto ikonę (tylko jeśli ON)
        if state == "INV ON":
            thh, tww = size_map  # (h, w)
            resp["icon"] = {
                "screen_x": int(abs_x_p + loc_map[0]),
                "screen_y": int(abs_y_p + loc_map[1]),
                "w": int(tww),
                "h": int(thh),
            }

        if debug_image:
            ok, buf = cv2.imencode(".png", roi_bgr)
            if ok:
                resp["debug_roi_png_base64"] = base64.b64encode(buf.tobytes()).decode("ascii")

        return jsonify(resp), 200

    except Exception as e:
        return jsonify(ok=False, error=f"{type(e).__name__}: {e}"), 500



@app.post("/screen/chat")
def api_screen_chat_box_state():
    """
    JSON:
    {
      "rect": {"x": 268, "y": 536, "w": 26, "h": 26},
      "title": "GoldMU",      # opcjonalnie
      "thr": 0.88,            # opcjonalnie
      "pad": 2,               # opcjonalnie
      "debug_image": false    # opcjonalnie
    }

    Response:
    {
      "ok": true,
      "state": "CHAT ON" | "CHAT OFF",
      "score": 0.93,
      "thr": 0.88,
      "rect_used": {...},
      "hwnd": 123456,
      "icon": {...}           # opcjonalnie gdy BOX ON
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    rect = data.get("rect") or {}

    title = (data.get("title") or "").strip()
    thr = float(data.get("thr") or 0.88)
    pad = int(data.get("pad") or 2)
    debug_image = bool(data.get("debug_image") or False)

    # walidacja rect
    try:
        x = int(rect.get("x"))
        y = int(rect.get("y"))
        w = int(rect.get("w"))
        h = int(rect.get("h"))
        if w <= 0 or h <= 0:
            raise ValueError
    except Exception:
        return jsonify(ok=False, error="Invalid rect {x,y,w,h}"), 400

    if not os.path.exists(TPL_CHAT_ON):
        return jsonify(ok=False, error=f"Missing template file: {TPL_CHAT_ON}"), 500

    hwnd = None
    if title:
        hwnd, err = find_window_by_title_substring(title)
        if err:
            return jsonify(ok=False, error=err), 404
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        abs_x = left + x
        abs_y = top + y
    else:
        abs_x, abs_y = x, y

    # padding
    abs_x_p = max(0, abs_x - pad)
    abs_y_p = max(0, abs_y - pad)
    w_p = w + 2 * pad
    h_p = h + 2 * pad

    monitor = {"left": abs_x_p, "top": abs_y_p, "width": w_p, "height": h_p}

    try:
        # screenshot ROI
        with mss.mss() as sct:
            shot = sct.grab(monitor)
            roi = np.array(shot)  # BGRA
            roi_bgr = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)

        # DEBUG: surowy ROI
        cv2.imwrite(os.path.join(TEMP_DIR, "chat_on_test.png"), roi_bgr)

        # match template
        score_map, loc_map, size_map = _match_icon(roi_bgr, TPL_CHAT_ON)

        state = "CHAT ON" if score_map >= thr else "CHAT OFF"

        resp = {
            "ok": True,
            "state": state,
            "score": float(score_map),
            "thr": float(thr),
            "rect_used": {"x": abs_x_p, "y": abs_y_p, "w": w_p, "h": h_p},
            "hwnd": int(hwnd) if hwnd else None,
        }

        # opcjonalnie: gdzie wykryto ikonę (tylko jeśli ON)
        if state == "BOX ON":
            thh, tww = size_map  # (h, w)
            resp["icon"] = {
                "screen_x": int(abs_x_p + loc_map[0]),
                "screen_y": int(abs_y_p + loc_map[1]),
                "w": int(tww),
                "h": int(thh),
            }

        if debug_image:
            ok, buf = cv2.imencode(".png", roi_bgr)
            if ok:
                resp["debug_roi_png_base64"] = base64.b64encode(buf.tobytes()).decode("ascii")

        return jsonify(resp), 200

    except Exception as e:
        return jsonify(ok=False, error=f"{type(e).__name__}: {e}"), 500


@app.post("/screen/system")
def api_screen_system_box_state():
    """
    JSON:
    {
      "rect": {"x": 268, "y": 536, "w": 26, "h": 26},
      "title": "GoldMU",      # opcjonalnie
      "thr": 0.88,            # opcjonalnie
      "pad": 2,               # opcjonalnie
      "debug_image": false    # opcjonalnie
    }

    Response:
    {
      "ok": true,
      "state": "CHAT ON" | "CHAT OFF",
      "score": 0.93,
      "thr": 0.88,
      "rect_used": {...},
      "hwnd": 123456,
      "icon": {...}           # opcjonalnie gdy BOX ON
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    rect = data.get("rect") or {}

    title = (data.get("title") or "").strip()
    thr = float(data.get("thr") or 0.88)
    pad = int(data.get("pad") or 2)
    debug_image = bool(data.get("debug_image") or False)

    # walidacja rect
    try:
        x = int(rect.get("x"))
        y = int(rect.get("y"))
        w = int(rect.get("w"))
        h = int(rect.get("h"))
        if w <= 0 or h <= 0:
            raise ValueError
    except Exception:
        return jsonify(ok=False, error="Invalid rect {x,y,w,h}"), 400

    if not os.path.exists(TPL_SYSTEM_ON):
        return jsonify(ok=False, error=f"Missing template file: {TPL_SYSTEM_ON}"), 500

    hwnd = None
    if title:
        hwnd, err = find_window_by_title_substring(title)
        if err:
            return jsonify(ok=False, error=err), 404
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        abs_x = left + x
        abs_y = top + y
    else:
        abs_x, abs_y = x, y

    # padding
    abs_x_p = max(0, abs_x - pad)
    abs_y_p = max(0, abs_y - pad)
    w_p = w + 2 * pad
    h_p = h + 2 * pad

    monitor = {"left": abs_x_p, "top": abs_y_p, "width": w_p, "height": h_p}

    try:
        # screenshot ROI
        with mss.mss() as sct:
            shot = sct.grab(monitor)
            roi = np.array(shot)  # BGRA
            roi_bgr = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)

        # DEBUG: surowy ROI
        cv2.imwrite(os.path.join(TEMP_DIR, "system_on_test.png"), roi_bgr)

        # match template
        score_map, loc_map, size_map = _match_icon(roi_bgr, TPL_SYSTEM_ON)

        state = "SYSTEM ON" if score_map >= thr else "SYSTEM OFF"

        resp = {
            "ok": True,
            "state": state,
            "score": float(score_map),
            "thr": float(thr),
            "rect_used": {"x": abs_x_p, "y": abs_y_p, "w": w_p, "h": h_p},
            "hwnd": int(hwnd) if hwnd else None,
        }

        # opcjonalnie: gdzie wykryto ikonę (tylko jeśli ON)
        if state == "SYSTEM ON":
            thh, tww = size_map  # (h, w)
            resp["icon"] = {
                "screen_x": int(abs_x_p + loc_map[0]),
                "screen_y": int(abs_y_p + loc_map[1]),
                "w": int(tww),
                "h": int(thh),
            }

        if debug_image:
            ok, buf = cv2.imencode(".png", roi_bgr)
            if ok:
                resp["debug_roi_png_base64"] = base64.b64encode(buf.tobytes()).decode("ascii")

        return jsonify(resp), 200

    except Exception as e:
        return jsonify(ok=False, error=f"{type(e).__name__}: {e}"), 500


@app.post("/screen/map")
def api_screen_map_state():
    data = request.get_json(force=True, silent=True) or {}
    rect = data.get("rect") or {}

    title = (data.get("title") or "").strip()
    pad = int(data.get("pad") or 2)
    debug_image = bool(data.get("debug_image") or False)

    # detekcja "białego punktu"
    white_thr = int(data.get("white_thr") or 245)              # 0..255
    min_white_pixels = int(data.get("min_white_pixels") or 6)  # np. 6-12 dla małego ROI
    min_white_ratio = float(data.get("min_white_ratio") or 0.0)

    # walidacja rect
    try:
        x = int(rect.get("x"))
        y = int(rect.get("y"))
        w = int(rect.get("w"))
        h = int(rect.get("h"))
        if w <= 0 or h <= 0:
            raise ValueError
    except Exception:
        return jsonify(ok=False, error="Invalid rect {x,y,w,h}"), 400

    hwnd = None
    if title:
        hwnd, err = find_window_by_title_substring(title)
        if err:
            return jsonify(ok=False, error=err), 404
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        abs_x = left + x
        abs_y = top + y
    else:
        abs_x, abs_y = x, y

    # padding
    abs_x_p = max(0, abs_x - pad)
    abs_y_p = max(0, abs_y - pad)
    w_p = w + 2 * pad
    h_p = h + 2 * pad

    monitor = {"left": abs_x_p, "top": abs_y_p, "width": w_p, "height": h_p}

    try:
        with mss.mss() as sct:
            shot = sct.grab(monitor)
            roi = np.array(shot)  # BGRA
            roi_bgr = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)

        # ✅ ZAWSZE NADPISUJ TEN SAM PLIK
        raw_path = os.path.join(TEMP_DIR, "map_roi_raw.png")
        cv2.imwrite(raw_path, roi_bgr)

        # maska "prawie białych" pikseli
        # roi_bgr jest BGR: [B,G,R]
        mask = (
            (roi_bgr[:, :, 0] >= white_thr) &
            (roi_bgr[:, :, 1] >= white_thr) &
            (roi_bgr[:, :, 2] >= white_thr)
        )
        white_pixels = int(mask.sum())
        total_pixels = int(mask.size)
        white_ratio = float(white_pixels / max(1, total_pixels))

        is_on = (white_pixels >= min_white_pixels) and (white_ratio >= min_white_ratio)
        state = "MAP ON" if is_on else "MAP OFF"

        resp = {
            "ok": True,
            "state": state,
            "white_thr": int(white_thr),
            "min_white_pixels": int(min_white_pixels),
            "min_white_ratio": float(min_white_ratio),
            "white_pixels": white_pixels,
            "white_ratio": white_ratio,
            "rect_used": {"x": abs_x_p, "y": abs_y_p, "w": w_p, "h": h_p},
            "hwnd": int(hwnd) if hwnd else None,
            "raw_roi_path": raw_path,
        }

        if debug_image:
            ok, buf = cv2.imencode(".png", roi_bgr)
            if ok:
                resp["debug_roi_png_base64"] = base64.b64encode(buf.tobytes()).decode("ascii")

        return jsonify(resp), 200

    except Exception as e:
        return jsonify(ok=False, error=f"{type(e).__name__}: {e}"), 500



@app.post("/screen/autorun-state")
def api_screen_autorun_state():
    """
    JSON:
    {
      "rect": {"x": 950, "y": 20, "w": 60, "h": 40},
      "title": "GoldMU",      # opcjonalnie
      "thr": 0.88,            # opcjonalnie
      "pad": 2,               # opcjonalnie
      "debug_image": false    # opcjonalnie
    }

    Response:
    {
      "ok": true,
      "state": "PLAY" | "PAUSE" | "UNKNOWN",
      "scores": {
        "play": 0.97,
        "pause": 0.41
      },
      "rect_used": {...},
      "hwnd": 123456
    }
    """

    data = request.get_json(force=True, silent=True) or {}
    rect = data.get("rect") or {}

    title = (data.get("title") or "").strip()
    thr = float(data.get("thr") or 0.88)
    pad = int(data.get("pad") or 2)
    debug_image = bool(data.get("debug_image") or False)

    # walidacja rect
    try:
        x = int(rect.get("x"))
        y = int(rect.get("y"))
        w = int(rect.get("w"))
        h = int(rect.get("h"))
        if w <= 0 or h <= 0:
            raise ValueError
    except Exception:
        return jsonify(ok=False, error="Invalid rect {x,y,w,h}"), 400

    if not os.path.exists(TPL_PAUSE) or not os.path.exists(TPL_PLAY):
        return jsonify(
            ok=False,
            error="Missing autorun_pause.png or autorun_play.png next to app.py"
        ), 500

    hwnd = None
    if title:
        hwnd, err = find_window_by_title_substring(title)
        if err:
            return jsonify(ok=False, error=err), 404
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        abs_x = left + x
        abs_y = top + y
    else:
        abs_x, abs_y = x, y

    abs_x_p = max(0, abs_x - pad)
    abs_y_p = max(0, abs_y - pad)
    w_p = w + 2 * pad
    h_p = h + 2 * pad

    monitor = {"left": abs_x_p, "top": abs_y_p, "width": w_p, "height": h_p}

    try:
        with mss.mss() as sct:
            shot = sct.grab(monitor)
            roi = np.array(shot)  # BGRA
            roi_bgr = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR)

        score_pause, loc_pause, size_pause = _match_icon(roi_bgr, TPL_PAUSE)
        score_play,  loc_play,  size_play  = _match_icon(roi_bgr, TPL_PLAY)

        # decyzja
        if score_pause >= thr and score_pause > score_play + 0.02:
            state = "PAUSE"
            best = ("pause", score_pause, loc_pause, size_pause)
        elif score_play >= thr and score_play > score_pause + 0.02:
            state = "PLAY"
            best = ("play", score_play, loc_play, size_play)
        else:
            state = "UNKNOWN"
            best = None

        resp = {
            "ok": True,
            "state": state,
            "state_info": "PLAY means is not running, PAUSE means is running",
            "scores": {
                "pause": score_pause,
                "play": score_play
            },
            "rect_used": {
                "x": abs_x_p,
                "y": abs_y_p,
                "w": w_p,
                "h": h_p
            },
            "hwnd": int(hwnd) if hwnd else None,
            "thr": thr
        }

        # opcjonalnie: dokładna pozycja ikony na ekranie
        if best:
            kind, score, loc, (th, tw) = best
            resp["icon"] = {
                "type": kind,
                "screen_x": abs_x_p + loc[0],
                "screen_y": abs_y_p + loc[1],
                "w": tw,
                "h": th
            }

        if debug_image:
            ok, buf = cv2.imencode(".png", roi_bgr)
            if ok:
                resp["debug_roi_png_base64"] = base64.b64encode(buf.tobytes()).decode("ascii")

        return jsonify(resp), 200

    except Exception as e:
        return jsonify(ok=False, error=f"{type(e).__name__}: {e}"), 500


def ocr_zen_digits(img_bgr: "np.ndarray") -> dict:
    import re
    import os
    import cv2
    import numpy as np
    import pytesseract

    cfgs = [
        "--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789,",
        "--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789,",
        "--oem 3 --psm 13 -c tessedit_char_whitelist=0123456789,",
    ]

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    TEMP_DIR = os.path.join(BASE_DIR, "temp")
    os.makedirs(TEMP_DIR, exist_ok=True)

    # 1) upscale
    up = cv2.resize(img_bgr, None, fx=10, fy=10, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(os.path.join(TEMP_DIR, "zen_raw.png"), up)

    # 2) grayscale + lekki blur
    gray = cv2.cvtColor(up, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    cv2.imwrite(os.path.join(TEMP_DIR, "zen_gray.png"), gray)

    # 3A) OTSU -> czarne cyfry na białym tle (to u Ciebie działa najlepiej)
    _, bin_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cv2.imwrite(os.path.join(TEMP_DIR, "zen_bin_otsu.png"), bin_otsu)

    # 3B) HSV V-mask (fallback) -> też daje czarne cyfry na białym tle
    hsv = cv2.cvtColor(up, cv2.COLOR_BGR2HSV)
    v = hsv[:, :, 2]
    bin_v = np.where(v < 140, 0, 255).astype(np.uint8)  # ciemne -> 0 (czarne), reszta -> 255 (białe)
    cv2.imwrite(os.path.join(TEMP_DIR, "zen_bin_v.png"), bin_v)

    # 4) delikatna morfologia (opcjonalnie, ale pomaga na poszarpane krawędzie)
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    bin_otsu_m = cv2.morphologyEx(bin_otsu, cv2.MORPH_OPEN, k, iterations=1)
    bin_v_m = cv2.morphologyEx(bin_v, cv2.MORPH_OPEN, k, iterations=1)
    cv2.imwrite(os.path.join(TEMP_DIR, "zen_bin_otsu_m.png"), bin_otsu_m)
    cv2.imwrite(os.path.join(TEMP_DIR, "zen_bin_v_m.png"), bin_v_m)

    # 5) OCR na kilku wariantach, wybierz najlepszy (najwięcej cyfr)
    candidates = [
        ("otsu", bin_otsu),
        ("otsu_m", bin_otsu_m),
        ("v", bin_v),
        ("v_m", bin_v_m),
    ]

    best = {"name": None, "raw": "", "digits": ""}

    for name, img in candidates:
        for cfg in cfgs:
            raw = (pytesseract.image_to_string(img, config=cfg) or "").strip()
            digits = "".join(re.findall(r"\d+", raw))
            if len(digits) > len(best["digits"]):
                best = {"name": name, "raw": raw, "digits": digits}

    # zapisz najlepszy input OCR do debugu
    if best["name"] is not None:
        best_img = dict(candidates)[best["name"]]
        cv2.imwrite(os.path.join(TEMP_DIR, "zen_best.png"), best_img)

    value = int(best["digits"]) if best["digits"] else None
    return {"raw": best["raw"], "digits": best["digits"], "value": value}


def ocr_health_digits(img_bgr: "np.ndarray") -> dict:
    import re
    import os
    import cv2
    import numpy as np
    import pytesseract

    # lokalnie, nie globalnie
    cfgs = [
        "--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789",
        "--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789",
        "--oem 3 --psm 13 -c tessedit_char_whitelist=0123456789",
    ]

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    TEMP_DIR = os.path.join(BASE_DIR, "temp")
    os.makedirs(TEMP_DIR, exist_ok=True)

    # 1) upscale umiarkowany
    up = cv2.resize(img_bgr, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
    # DEBUG TEMP/IMAGE
    cv2.imwrite(os.path.join(TEMP_DIR, "hp_roi_raw.png"), up)

    H, W = up.shape[:2]

    # 2) crop: weź dolny pasek (tam są cyfry) i wytnij lewy fragment z ikoną
    y1 = int(H * 0.01)          # dolne ~45% obrazu
    x1 = int(W * 0.01)          # utnij ikonę z lewej
    roi = up[y1:H, x1:W]
    # DEBUG TEMP/IMAGE
    cv2.imwrite(os.path.join(TEMP_DIR, "hp_roi_digits.png"), roi)

    # 3) maska "jasnego tekstu" (cyfry mają jasny fill, outline jest ciemny)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]

    # jasne + mało nasycone (białe/kremawe cyfry)
    mask = ((v > 165) & (s < 140)).astype(np.uint8) * 255
    # DEBUG TEMP/IMAGE
    cv2.imwrite(os.path.join(TEMP_DIR, "hp_mask_bright.png"), mask)

    # 4) morfologia: domknij cyfry i wywal drobny syf
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)

    # DEBUG TEMP/IMAGE
    cv2.imwrite(os.path.join(TEMP_DIR, "hp_bin.png"), mask)

    # 5) komponenty: zostaw tylko sensowne "cyfrowe" kawałki
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)

    clean = np.zeros_like(mask)
    h2, w2 = mask.shape[:2]

    for i in range(1, num_labels):
        x, y, w, h, area = stats[i]

        # odfiltruj śmieci/ornamenty
        if area < 120:
            continue
        if h < int(0.35 * h2) or h > int(0.95 * h2):
            continue
        if w < 6 or w > int(0.55 * w2):
            continue

        clean[labels == i] = 255

    # lekkie domknięcie, żeby cyfry były spójne
    clean = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, k, iterations=1)

    # DEBUG TEMP/IMAGE
    cv2.imwrite(os.path.join(TEMP_DIR, "hp_clean.png"), clean)
    cv2.imwrite(os.path.join(TEMP_DIR, "hp_bin_inv.png"), clean)

    # 6) OCR: spróbuj kilka psm i wybierz najdłuższy ciąg cyfr
    best_digits = ""
    best_raw = ""

    for cfg in cfgs:
        raw = (pytesseract.image_to_string(clean, config=cfg) or "").strip()
        digits = "".join(re.findall(r"\d+", raw))
        if len(digits) > len(best_digits):
            best_digits = digits
            best_raw = raw

    value = int(best_digits) if best_digits else None
    return {"raw": best_raw, "digits": best_digits, "value": value}

@app.post("/ui/capture")
def ui_capture():
    CAPTURE_PATH = "temp/mu_fwin.png"
    CAPTURE_URL = "http://192.168.50.200:5055/screen/capture.png"
    payload = {
        "title": "GoldMU || Player: CoZaBzdura",
        "rect": {"x": 3, "y": 1, "w": 806, "h": 632}
    }

    r = requests.post(CAPTURE_URL, json=payload, timeout=3)
    r.raise_for_status()

    with open(CAPTURE_PATH, "wb") as f:
        f.write(r.content)

    return jsonify(ok=True)


@app.get("/ui/capture.png")
def ui_capture_png():
    return send_file("temp/mu_fwin.png", mimetype="image/png")

@app.post("/screen/ocr/exp_per_minute")
def api_screen_ocr_exp_per_minute():
    """
    JSON:
    {
      "rect": {"x": 10, "y": 10, "w": 220, "h": 28},
      "title": "GoldMU",      # opcjonalnie: jeśli podane, rect jest RELATYWNY do okna
      "pad": 0                # opcjonalnie: margines px
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    rect = data.get("rect") or {}
    title = (data.get("title") or "").strip()
    pad = int(data.get("pad", 0))

    # walidacja rect
    try:
        x = int(rect["x"])
        y = int(rect["y"])
        w = int(rect["w"])
        h = int(rect["h"])
        if w <= 0 or h <= 0:
            raise ValueError
    except Exception:
        return jsonify(ok=False, error="Missing/invalid rect. Expected rect: {x,y,w,h}"), 400

    hwnd = None

    # jeśli title podane -> rect relatywny do okna
    if title:
        hwnd, err = find_window_by_title_substring(title)
        if err:
            return jsonify(ok=False, error=err), 404
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        abs_x = left + x
        abs_y = top + y
    else:
        abs_x, abs_y = x, y

    # pad (opcjonalnie)
    abs_x_p = max(0, abs_x - pad)
    abs_y_p = max(0, abs_y - pad)
    w_p = w + 2 * pad
    h_p = h + 2 * pad

    try:
        with mss.mss() as sct:
            monitor = {"left": abs_x_p, "top": abs_y_p, "width": w_p, "height": h_p}
            img = np.array(sct.grab(monitor))  # BGRA

        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        res = ocr_health_digits(img_bgr)

        return jsonify(
            ok=True,
            hwnd=int(hwnd) if hwnd else None,
            raw_text=res["raw"],
            digits=res["digits"],
            value=res["value"],
            rect_used={"x": abs_x_p, "y": abs_y_p, "w": w_p, "h": h_p},
            rect_input={"x": x, "y": y, "w": w, "h": h},
            title=title or None
        )

    except Exception as e:
        return jsonify(ok=False, error=f"{type(e).__name__}: {e}"), 500

@app.post("/screen/ocr/health")
def api_screen_ocr_health():
    """
    JSON:
    {
      "rect": {"x": 10, "y": 10, "w": 220, "h": 28},
      "title": "GoldMU",      # opcjonalnie: jeśli podane, rect jest RELATYWNY do okna
      "pad": 0                # opcjonalnie: margines px
    }
    """
    data = request.get_json(force=True, silent=True) or {}
    rect = data.get("rect") or {}
    title = (data.get("title") or "").strip()
    pad = int(data.get("pad", 0))

    # walidacja rect
    try:
        x = int(rect["x"])
        y = int(rect["y"])
        w = int(rect["w"])
        h = int(rect["h"])
        if w <= 0 or h <= 0:
            raise ValueError
    except Exception:
        return jsonify(ok=False, error="Missing/invalid rect. Expected rect: {x,y,w,h}"), 400

    hwnd = None

    # jeśli title podane -> rect relatywny do okna
    if title:
        hwnd, err = find_window_by_title_substring(title)
        if err:
            return jsonify(ok=False, error=err), 404
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        abs_x = left + x
        abs_y = top + y
    else:
        abs_x, abs_y = x, y

    # pad (opcjonalnie)
    abs_x_p = max(0, abs_x - pad)
    abs_y_p = max(0, abs_y - pad)
    w_p = w + 2 * pad
    h_p = h + 2 * pad

    try:
        with mss.mss() as sct:
            monitor = {"left": abs_x_p, "top": abs_y_p, "width": w_p, "height": h_p}
            img = np.array(sct.grab(monitor))  # BGRA

        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        res = ocr_health_digits(img_bgr)

        return jsonify(
            ok=True,
            hwnd=int(hwnd) if hwnd else None,
            raw_text=res["raw"],
            digits=res["digits"],
            value=res["value"],
            rect_used={"x": abs_x_p, "y": abs_y_p, "w": w_p, "h": h_p},
            rect_input={"x": x, "y": y, "w": w, "h": h},
            title=title or None
        )

    except Exception as e:
        return jsonify(ok=False, error=f"{type(e).__name__}: {e}"), 500


@app.post("/screen/ocr/zen")
def api_screen_ocr_zen():
    """
    JSON:
    {
      "rect": {"x": 688, "y": 478, "w": 100, "h": 16},
      "title": "PlayerName",
      "pad": 0
    }
    """
    import os
    import time

    data = request.get_json(force=True, silent=True) or {}
    rect = data.get("rect") or {}
    title = (data.get("title") or "").strip()
    pad = int(data.get("pad", 0))

    # --- walidacja rect ---
    try:
        x = int(rect["x"])
        y = int(rect["y"])
        w = int(rect["w"])
        h = int(rect["h"])
        if w <= 0 or h <= 0:
            raise ValueError
    except Exception:
        return jsonify(ok=False, error="Missing/invalid rect. Expected rect: {x,y,w,h}"), 400

    hwnd = None

    # --- rect relatywny do okna ---
    if title:
        hwnd, err = find_window_by_title_substring(title)
        if err:
            return jsonify(ok=False, error=err), 404
        left, top, _, _ = win32gui.GetWindowRect(hwnd)
        abs_x = left + x
        abs_y = top + y
    else:
        abs_x, abs_y = x, y

    # --- pad ---
    abs_x_p = max(0, abs_x - pad)
    abs_y_p = max(0, abs_y - pad)
    w_p = w + 2 * pad
    h_p = h + 2 * pad

    try:
        # --- screen grab ---
        with mss.mss() as sct:
            monitor = {
                "left": abs_x_p,
                "top": abs_y_p,
                "width": w_p,
                "height": h_p
            }
            img = np.array(sct.grab(monitor))  # BGRA

        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # ===== ZAPIS RAW (JEDEN PLIK) =====
        os.makedirs("temp", exist_ok=True)
        raw_path = "temp/zen_raw.png"
        cv2.imwrite(raw_path, img_bgr)
        # =================================

        # --- OCR ---
        res = ocr_zen_digits(img_bgr)

        return jsonify(
            ok=True,
            hwnd=int(hwnd) if hwnd else None,
            raw_text=res["raw"],
            digits=res["digits"],
            value=res["value"],
            raw_image=raw_path,
            rect_used={"x": abs_x_p, "y": abs_y_p, "w": w_p, "h": h_p},
            rect_input={"x": x, "y": y, "w": w, "h": h},
            title=title or None
        )

    except Exception as e:
        return jsonify(ok=False, error=f"{type(e).__name__}: {e}"), 500


@app.post("/screen/find-templates")
def api_screen_find_templates():
    data = request.get_json(force=True, silent=True) or {}

    title = (data.get("title") or "").strip()
    rect = data.get("rect") or {}
    templates = data.get("templates") or []

    thr = float(data.get("thr", 0.88))
    pad = int(data.get("pad", 0))
    max_results = int(data.get("max_results", 30))
    nms_radius = int(data.get("nms_radius", 10))
    debug_save = bool(data.get("debug_save", False))

    if not title:
        return jsonify(ok=False, error="Missing 'title'"), 400
    if not isinstance(templates, list) or not templates:
        return jsonify(ok=False, error="Missing 'templates' list"), 400

    try:
        resp = vision_match.find_templates_in_window_roi(
            find_window_by_title_substring=find_window_by_title_substring,
            base_dir=BASE_DIR,
            temp_dir=TEMP_DIR,
            title=title,
            rect=rect,
            templates=templates,
            thr=thr,
            pad=pad,
            max_results=max_results,
            nms_radius=nms_radius,
            debug_save=debug_save,
            templates_dir_name="search_templates",
        )
        return jsonify(resp), 200

    except Exception as e:
        return jsonify(ok=False, error=f"{type(e).__name__}: {e}"), 500


@app.post("/screen/find-and-hover")
def api_screen_find_and_hover():
    """
    JSON:
    {
      "title": "GoldMU || Player: CoZaBzdura",
      "rect": {"x": 0, "y": 0, "w": 800, "h": 600},
      "templates": ["kundun_map.png", "foo.png"],

      "thr": 0.88,
      "pad": 0,
      "max_results": 30,
      "nms_radius": 10,
      "debug_save": false,

      "pick": "best",               # best|leftmost|rightmost|topmost|bottommost
      "hover": {
        "tolerance": 1,
        "max_iters": 600,
        "sleep_s": 0.012,
        "require_inside": false
      }
    }

    Response:
    {
      "ok": true,
      "picked": {...},              # template + hit
      "hover_result": {...},        # response z /mouse/goto_xy_relative
      "find_result": {...}          # surowy wynik find
    }
    """
    data = request.get_json(force=True, silent=True) or {}

    title = (data.get("title") or "").strip()
    rect = data.get("rect") or {}
    templates = data.get("templates") or []

    thr = float(data.get("thr", 0.88))
    pad = int(data.get("pad", 0))
    max_results = int(data.get("max_results", 30))
    nms_radius = int(data.get("nms_radius", 10))
    debug_save = bool(data.get("debug_save", False))

    pick = (data.get("pick") or "best").strip().lower()
    hover_cfg = data.get("hover") or {}

    if not title:
        return jsonify(ok=False, error="Missing 'title'"), 400
    if not isinstance(templates, list) or not templates:
        return jsonify(ok=False, error="Missing 'templates' list"), 400

    # 1) FIND
    try:
        # lokalnie wołamy funkcję endpointu (bez HTTP), jeśli wolisz HTTP to też dam wariant
        find_resp = vision_match.find_templates_in_window_roi(
            find_window_by_title_substring=find_window_by_title_substring,
            base_dir=BASE_DIR,
            temp_dir=TEMP_DIR,
            title=title,
            rect=rect,
            templates=templates,
            thr=thr,
            pad=pad,
            max_results=max_results,
            nms_radius=nms_radius,
            debug_save=debug_save,
            templates_dir_name="search_templates",
        )
    except Exception as e:
        return jsonify(ok=False, error=f"find_failed: {type(e).__name__}: {e}"), 500

    # spłaszcz wszystkie trafienia do jednej listy
    all_hits = []
    for m in (find_resp.get("matches") or []):
        tname = m.get("template")
        for h in (m.get("hits") or []):
            all_hits.append({
                "template": tname,
                "score": float(h.get("score", 0.0)),
                "window": h.get("window") or {},
                "roi": h.get("roi") or {}
            })

    if not all_hits:
        return jsonify(ok=False, reason="no_matches", find_result=find_resp), 200

    # 2) PICK
    def key_best(h):      return h["score"]
    def key_left(h):      return -int(h["window"].get("cx", 10**9))   # max neg -> min cx
    def key_right(h):     return int(h["window"].get("cx", -1))
    def key_top(h):       return -int(h["window"].get("cy", 10**9))
    def key_bottom(h):    return int(h["window"].get("cy", -1))

    if pick == "leftmost":
        chosen = max(all_hits, key=key_left)
    elif pick == "rightmost":
        chosen = max(all_hits, key=key_right)
    elif pick == "topmost":
        chosen = max(all_hits, key=key_top)
    elif pick == "bottommost":
        chosen = max(all_hits, key=key_bottom)
    else:
        chosen = max(all_hits, key=key_best)

    cx = int(chosen["window"].get("cx", -1))
    cy = int(chosen["window"].get("cy", -1))
    if cx < 0 or cy < 0:
        return jsonify(ok=False, error="chosen_hit_missing_window_coords", chosen=chosen, find_result=find_resp), 500

    # 3) HOVER (najechanie)
    try:
        goto_payload = {
            "title": title,
            "target_x": cx,
            "target_y": cy,
            "tolerance": int(hover_cfg.get("tolerance", 1)),
            "max_iters": int(hover_cfg.get("max_iters", 600)),
            "sleep_s": float(hover_cfg.get("sleep_s", 0.012)),
            "require_inside": bool(hover_cfg.get("require_inside", False)),
        }

        # ważne: żeby nie wpadło na error typu max_iters/sleep
        if goto_payload["tolerance"] < 0:
            goto_payload["tolerance"] = 0
        if goto_payload["max_iters"] < 1:
            goto_payload["max_iters"] = 1
        if goto_payload["sleep_s"] < 0:
            goto_payload["sleep_s"] = 0.0

        # Wołamy lokalnie funkcję API (bez HTTP) – szybciej, bez timeoutów
        # Ale ponieważ masz już logikę w api_mouse_goto_xy_relative jako endpoint,
        # to najprościej użyć Twojego helpera post() na loopback.
        #
        # Jeśli host_api i /mouse/goto_xy_relative są w tym samym Flasku na 5055:
        hover_url = "http://127.0.0.1:5055/mouse/goto_xy_relative"
        hover_result = post(hover_url, goto_payload)

        return jsonify(
            ok=True,
            picked={
                "template": chosen["template"],
                "score": chosen["score"],
                "target_x": cx,
                "target_y": cy,
                "pick": pick,
            },
            hover_payload=goto_payload,
            hover_result=hover_result,
            find_result=find_resp
        ), 200

    except Exception as e:
        return jsonify(
            ok=False,
            error=f"hover_failed: {type(e).__name__}: {e}",
            picked=chosen,
            find_result=find_resp
        ), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5055, use_reloader=False)
