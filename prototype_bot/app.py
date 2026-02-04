import threading
from collections import deque
import time
from flask import Flask, render_template, jsonify, request, send_from_directory
from datetime import datetime, date
import requests
import logging
import json
import os
from typing import Any, Dict
import random
from logging.handlers import RotatingFileHandler
import psutil
import functools

from locations import AIDA_LOCATIONS, KALIMA_LOCATIONS, LACLEON_LOCATIONS, ATLANS_LOCATIONS
from hud_coords import HUD_COORDS
from hud_coords import get_rect

PLAYER = "CoZaBzdura"
#PLAYER = "AleElfisko"

state_lock = threading.Lock()
STATE_SNAPSHOT = {"ts": 0, "state": None}
stop_event = threading.Event()
controller_ready = threading.Event()

app = Flask(__name__)

psutil.cpu_percent(None)

def get_system_usage():
    vm = psutil.virtual_memory()
    return {
        "cpu": psutil.cpu_percent(None),   # % całego systemu
        "ram_percent": vm.percent,
        "ram_used_mb": vm.used / 1024**2,
        "ram_total_mb": vm.total / 1024**2,
    }

#----------- config

PARTY_PLAYER = "AleElfisko"
LEVEL_LOG_FILE = "level_log.csv"
MIN_TARGET_LEVEL = 300
TARGET_LEVEL = 400
LOG_FILE = "ocr_api.log"

CHECK_INTERVAL = 2  # seconds
# ---- RPI keyboard host
KEY_API    = "http://192.168.50.228:5000/keyboard/press"
TEXT_API   = "http://192.168.50.228:5000/keyboard/text"
#-----------------------
# ---- WINDOWS host
TITLE_API = "http://192.168.50.200:5055/window/parse-title"
SCREEN_API = "http://192.168.50.200:5055/screen/ocr"
WINDOW_API = "http://192.168.50.200:5055/window/activate-topmost"
WINDOW_MOVE_API = "http://192.168.50.200:5055/window/move"
HELPER_API = "http://192.168.50.200:5055/screen/autorun-state"
HEALTH_API = "http://192.168.50.200:5055/screen/ocr/health"
ZEN_API = "http://192.168.50.200:5055/screen/ocr/zen"
EXP_PER_MINUTE_API = "http://192.168.50.200:5055/screen/ocr/exp_per_minute"
MOUSE_REL_API = "http://192.168.50.200:5055/mouse/position-relative"
MOUSE_POS_API = "http://192.168.50.200:5055/mouse/position"
SEND_MESSAGE_URL = "http://192.168.50.200:5055/send_message"
HEADERS = {"Content-Type": "application/json"}


formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s"
)

file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8"
)

file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

root = logging.getLogger()
root.setLevel(logging.INFO)
root.handlers.clear()
root.addHandler(file_handler)
root.addHandler(console_handler)

logging.getLogger("werkzeug").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(BASE_DIR, f"bot_{PLAYER}_state.json")

LEVEL_STATE = {
    "current_level": None,
    "level_start_ts": None
}

if not os.path.exists(LEVEL_LOG_FILE):
    with open(LEVEL_LOG_FILE, "w", encoding="utf-8") as f:
        f.write("timestamp,event,from_level,to_level,elapsed_seconds\n")

def clear_level_log():
    with open(LEVEL_LOG_FILE, "w", encoding="utf-8") as f:
        f.write("timestamp,event,from_level,to_level,elapsed_seconds\n")

def append_level_log(event, from_level=None, to_level=None, elapsed=None):
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    line = f"{ts},{event},{from_level},{to_level},{elapsed}\n"

    with open(LEVEL_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)

@app.get("/maps/<path:filename>")
def serve_maps(filename):
    return send_from_directory(os.path.join(BASE_DIR, "maps"), filename)

def update_level_timer(level: int):
    now = time.time()

    # pierwszy level
    if LEVEL_STATE["current_level"] is None:
        LEVEL_STATE["current_level"] = level
        LEVEL_STATE["level_start_ts"] = now
        append_level_log("init", None, level, None)
        return {"event": "init", "level": level}

    curr = LEVEL_STATE["current_level"]

    # brak zmiany
    if level == curr:
        return {
            "event": "same_level",
            "level": level,
            "elapsed": round(now - LEVEL_STATE["level_start_ts"], 2)
        }

    # normalny level up
    if level == curr + 1:
        elapsed = round(now - LEVEL_STATE["level_start_ts"], 2)

        append_level_log("level_up", curr, level, elapsed)

        LEVEL_STATE["current_level"] = level
        LEVEL_STATE["level_start_ts"] = now

        return {
            "event": "level_up",
            "from": curr,
            "to": level,
            "elapsed_seconds": elapsed
        }

    # skok / reset / błąd OCR
    append_level_log("level_jump", curr, level, None)

    LEVEL_STATE["current_level"] = level
    LEVEL_STATE["level_start_ts"] = now

    return {
        "event": "level_jump",
        "level": level
    }

def load_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_PATH):
        return {}
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except (json.JSONDecodeError, OSError) as e:
        logger.exception(f"load_state failed: {e}")
    return {}

def save_state(state: Dict[str, Any]) -> None:
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, STATE_PATH)

# =======================
# SAFE STATE ACCESS (ONE PATH)
# =======================
def state_get(key: str, default=None):
    with state_lock:
        st = load_state()
        return st.get(key, default)

def state_set(key: str, value):
    with state_lock:
        st = load_state()
        st[key] = value
        save_state(st)
        return st

def state_update(patch: dict):
    with state_lock:
        st = load_state()
        st.update(patch)
        save_state(st)
        return st

def state_mutate(mutator):
    with state_lock:
        st = load_state()
        mutator(st)
        save_state(st)
        return st

def post(url, payload):
    r = requests.post(url, json=payload, timeout=160)
    r.raise_for_status()
    return r.json() if r.content else None

def request_get(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json() if r.content else None

def move_window(x, y, w, h):
    title=f"GoldMU || Player: {PLAYER}"
    payload = {
        "title": title,
        "x": x,
        "y": y,
        "w": w,
        "h": h
    }
    r = requests.post(WINDOW_MOVE_API, json=payload, headers=HEADERS, timeout=3)
    r.raise_for_status()
    return r.json() if r.content else None

def check_conditions():
    title_request = post(TITLE_API, {
        "title": f"GoldMU || Player: {PLAYER}",
        "topmost": False
    })

    location_request = post(SCREEN_API, {
        "title": f"GoldMU || Player: {PLAYER}",
        "rect": get_rect("location_box"),
        "psm": 7,
        "whitelist": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789(),"
    })

    helper_request = post(HELPER_API, {
        "title": f"GoldMU || Player: {PLAYER}",
        "rect": get_rect("helper_state"),
        "debug_image": False
    })

    health_request = post(HEALTH_API, {
        "title": f"GoldMU || Player: {PLAYER}",
        "rect": {"x": 245, "y": 595, "w": 45, "h": 20}
    })

    exppm_request = post(EXP_PER_MINUTE_API, {
        "title": f"GoldMU || Player: {PLAYER}",
        "rect": {"x": 125, "y": 220, "w": 80, "h": 15}
    })

    mouse_rel_request = post(MOUSE_REL_API, {"title": f"GoldMU || Player: {PLAYER}"})
    mouse_position = request_get(MOUSE_POS_API)

    conn_status = True if "Connected" in title_request.get("raw", "") else False

    try:
        location_name = location_request["parsed"]["name"]
        location_x    = location_request["parsed"]["x"]
        location_y    = location_request["parsed"]["y"]
        # f-string bug zostawiam jak kazałeś - nie ruszam
        logger.debug(f"Location debug: {location_request["parsed"]["name"]}, {location_request["parsed"]["x"]}, {location_request["parsed"]["y"]}")
    except (TypeError, KeyError):
        logger.debug(f"Location raw ERROR: {location_request}")
        location_name = "not_available"
        location_x    = 0
        location_y    = 0

    now = datetime.now().strftime("%H:%M:%S")

    st = load_state()

    return {
        "time": now,
        "player": title_request.get("player"),
        "level": title_request.get("level"),
        "exp_per_minute": exppm_request.get("digits"),
        "reset": title_request.get("reset"),
        "rect": title_request.get("rect"),
        "location_name": location_name,
        "location_coord_x": location_x,
        "location_coord_y": location_y,
        "mouse_position": mouse_position,
        "mouse_relative_pos": mouse_rel_request,
        "helper_status": helper_request.get("state"),
        "health": health_request.get("value"),
        "zen": st.get("zen", 0),
        "connected": conn_status,
        "resets_disabled": st.get("resets_disabled", False),
        "start_kalima": st.get("start_kalima", False),
        "minimum_zen_in_inventory": st.get("minimum_zen_in_inventory", 120000000),
        "run_speedrun": st.get("run_speedrun", False),
        "stats_added": st.get("stats_added", False),
        "speedrun_reset_date": st.get("speedrun_reset_date")
    }

def send_message(text: str):
    payload = {
        "title": f"GoldMU || Player: {PLAYER}",
        "text": text
    }
    return post(SEND_MESSAGE_URL, payload)

def add_stats():
    logger.info("Adding stats...")
    send_message("/addcom 975"); time.sleep(1)
    send_message("/addstr 29974"); time.sleep(1)
    send_message("/addagi 29980"); time.sleep(1)
    send_message("/addvit 29980"); time.sleep(1)
    send_message("/addene 9985"); time.sleep(1)
    send_message("/re auto")
    return "Stats added"

def check_map_on():
    SCREEN_MAP_URL = "http://192.168.50.200:5055/screen/map"
    time.sleep(0.4)
    payload = {
        "title": f"GoldMU || Player: {PLAYER}",
        "rect": {"x": 400, "y": 560, "w": 250, "h": 25},
        "thr": 0.88,
        "pad": 2
    }
    r = post(SCREEN_MAP_URL, payload)
    time.sleep(0.4)
    return r["state"]

def check_zen():
    SCREEN_ZEN_URL = "http://192.168.50.200:5055/screen/ocr/zen"
    time.sleep(0.2)
    payload = {
        "title": f"GoldMU || Player: {PLAYER}",
        "rect": {"x": 688, "y": 478, "w": 100, "h": 16}
    }
    r = post(SCREEN_ZEN_URL, payload)
    time.sleep(1)
    st = state_set("zen", int(r["value"]))
    return r["value"]

def check_chat_on():
    SCREEN_MAP_URL = "http://192.168.50.200:5055/screen/chat"
    time.sleep(0.4)
    payload = {
        "title": f"GoldMU || Player: {PLAYER}",
        "rect": {"x": 268, "y": 536, "w": 26, "h": 26},
        "thr": 0.88,
        "pad": 2
    }
    r = post(SCREEN_MAP_URL, payload)
    time.sleep(0.4)
    return r["state"]

def save_checker():
    chat_on = check_chat_on()
    SGO_TO_XY_URL = "http://192.168.50.200:5055/mouse/goto_xy_relative"
    MOUSE_CLICK_URL = "http://192.168.50.228:5000/mouse/click"
    if chat_on == "CHAT ON":
        logger.info("Some error with chat need to disable it")
        activate_window()
        post(SGO_TO_XY_URL, {
            "title": f"GoldMU || Player: {PLAYER}",
            "target_x": 534,
            "target_y": 571,
            "require_inside": False
        })
        time.sleep(0.3)
        post(MOUSE_CLICK_URL, {"button": "left", "action": "click", "hold_time": 0.5})
        time.sleep(0.2)

def go_to_point(mouse_x, mouse_y, print_txt="..."):
    logger.info(f"going to point: {print_txt}")

    SGO_TO_XY_URL = "http://192.168.50.200:5055/mouse/goto_xy_relative"
    MOUSE_CLICK_URL = "http://192.168.50.228:5000/mouse/click"

    post(KEY_API, {"keycode": 30, "press_time": 1})
    time.sleep(0.2)

    map_on = check_map_on()
    if map_on == "MAP OFF":
        post(KEY_API, {"keycode": 43, "press_time": 1})
        time.sleep(0.3)

    post(SGO_TO_XY_URL, {
        "title": f"GoldMU || Player: {PLAYER}",
        "target_x": mouse_x,
        "target_y": mouse_y,
        "require_inside": False
    })
    time.sleep(0.5)

    post(MOUSE_CLICK_URL, {"button": "left", "action": "click", "hold_time": 0.30})

    map_on = check_map_on()
    if map_on == "MAP ON":
        post(KEY_API, {"keycode": 43, "press_time": 1})
        time.sleep(0.3)

def start_speedrun():
    logger.info("Starting speedrun")
    activate_window()
    SGO_TO_XY_URL = "http://192.168.50.200:5055/mouse/goto_xy_relative"
    MOUSE_CLICK_URL = "http://192.168.50.228:5000/mouse/click"

    post(SGO_TO_XY_URL, {
        "title": f"GoldMU || Player: {PLAYER}",
        "target_x": 299,
        "target_y": 39,
        "require_inside": False
    })
    time.sleep(0.3)
    post(MOUSE_CLICK_URL, {"button": "left", "action": "click", "hold_time": 0.5})
    time.sleep(0.2)

def is_at_position(x, y, tx, ty, tol=4):
    return abs(x - tx) <= tol and abs(y - ty) <= tol

def mouse_up_right():
    MOUSE_CLICK_URL = "http://192.168.50.228:5000/mouse/click"
    return post(MOUSE_CLICK_URL, {"button": "right", "action": "up"})

def mouse_down_right():
    MOUSE_CLICK_URL = "http://192.168.50.228:5000/mouse/click"
    return post(MOUSE_CLICK_URL, {"button": "right", "action": "down"})

def mouse_move(dx, dy, step_delay=0.5):
    MOUSE_MOVE_URL  = "http://192.168.50.228:5000/mouse/move"
    return post(MOUSE_MOVE_URL, {"dx": int(dx), "dy": int(dy), "step_delay": float(step_delay)})

def sleep_interruptible(seconds: float):
    stop_event.wait(seconds)

def round_attack(deltas, step_delay=0.005, pause_range=(0.5, 2), hold_time=1):
    logger.info("Attacking...")
    SGO_TO_XY_URL = "http://192.168.50.200:5055/mouse/goto_xy_relative"
    MOUSE_CLICK_URL = "http://192.168.50.228:5000/mouse/click"
    INVENTORY_STATE_URL = "http://192.168.50.200:5055/screen/inventory_state"

    payload_click = {"button": "right", "action": "click", "hold_time": hold_time}
    payload_inventory_state = {
        "title": "GoldMU || Player: CoZaBzdura",
        "rect": {"x": 630, "y": 496, "w": 30, "h": 40},
        "thr": 0.88,
        "pad": 2
    }
    inventory_state = post(INVENTORY_STATE_URL, payload_inventory_state)
    logger.info(f"{inventory_state}")
    if inventory_state["state"] == "INV ON":
        logger.info("inventory is open I need to close it and then round attack...")
        time.sleep(0.3)
        close_inventory()

    try:
        for dx, dy in deltas:
            post(SGO_TO_XY_URL, {
                "title": f"GoldMU || Player: {PLAYER}",
                "target_x": dx,
                "target_y": dy,
                "require_inside": False
            })
            post(MOUSE_CLICK_URL, payload_click)
            sleep_interruptible(random.uniform(*pause_range))
    finally:
        sleep_interruptible(random.uniform(0.05, 0.12))
        mouse_up_right()

def wait_for_location_name_change(before, timeout=30, interval=0.5):
    start = time.time()
    before_name = before.get("location_name")
    before_loc_x = before.get("location_coord_x")

    while True:
        after = check_conditions()
        after_name = after.get("location_name")
        after_loc_x = after.get("location_coord_x")

        if after_name != before_name and after_loc_x != before_loc_x:
            return after

        if after_name == "Atlans":
            sleep = 2
            random_max = sleep + 1
            random_range = random.uniform(sleep, random_max)
            logger.info(f"Its Atlans so need to exit within {random_range} seconds...")
            time.sleep(random_range)
            return after

        if time.time() - start >= timeout:
            return None

        time.sleep(interval)
        logger.info(f"Warp process... waiting..., before: {before_name}, after: {after_name}, before x: {before_loc_x}, after x: {after_loc_x}")

def warp_to(location, sleep=0.1):
    activate_window()
    logger.info(f"warping to {location}")
    before_warp = check_conditions()
    send_message(f"/warp {location}")
    random_max = sleep + 1
    random_range = random.uniform(sleep, random_max)
    wait_for_location_name_change(before_warp)
    logger.info(f"After warp sleep: {random_range}")
    sleep_interruptible(random_range)

def set_flag_in_state(flag: str, value: bool) -> dict:
    return state_set(flag, bool(value))

def set_int_in_state(key: str, value: int) -> dict:
    return state_set(key, int(value))

@app.get("/bot/map-level-limits")
def api_get_map_level_limits():
    limits = state_get("map_level_limits", {})
    return jsonify(ok=True, map_level_limits=limits)

@app.post("/bot/set-minimum-zen")
def api_minimum_zen():
    data = request.get_json(force=True, silent=True) or {}
    val = data.get("minimum_zen_in_inventory")

    if val is None:
        return jsonify(ok=False, error="Missing 'minimum_zen_in_inventory'"), 400

    try:
        num = int(val)
    except Exception:
        return jsonify(ok=False, error="Invalid number"), 400

    if num < 120_000_000:
        return jsonify(ok=False, error="Minimum is 120000000"), 400

    st = set_int_in_state("minimum_zen_in_inventory", num)
    return jsonify(ok=True, minimum_zen_in_inventory=st.get("minimum_zen_in_inventory", num))

@app.post("/bot/resets-stop")
def api_resets_stop():
    st = set_flag_in_state("resets_disabled", True)
    return jsonify(ok=True, resets_disabled=st.get("resets_disabled", False))

@app.post("/bot/resets-start")
def api_resets_start():
    st = set_flag_in_state("resets_disabled", False)
    return jsonify(ok=True, resets_disabled=st.get("resets_disabled", False))

@app.post("/bot/next-speedrun")
def api_next_speedrun():
    st = set_flag_in_state("run_speedrun", True)
    return jsonify(ok=True, run_speedrun=st.get("run_speedrun", False))

@app.post("/bot/stop-speedrun")
def api_stop_speedrun():
    st = set_flag_in_state("run_speedrun", False)
    return jsonify(ok=True, run_speedrun=st.get("run_speedrun", False))

@app.post("/bot/start-kalima")
def api_start_kalima():
    st = set_flag_in_state("start_kalima", True)
    return jsonify(ok=True, start_kalima=st.get("start_kalima", False))

@app.post("/bot/clear-kalima")
def api_clear_kalima():
    st = set_flag_in_state("start_kalima", False)
    return jsonify(ok=True, start_kalima=st.get("start_kalima", False))

@app.get("/bot/state")
def api_bot_state():
    with state_lock:
        st = load_state()
    return jsonify(ok=True, state=st)

def mouse_move_click():
    MOUSE_CLICK_URL = "http://192.168.50.228:5000/mouse/click"
    SGO_TO_XY_URL = "http://192.168.50.200:5055/mouse/goto_xy"
    random_x = random.uniform(900,1300)
    post(SGO_TO_XY_URL, {"target_x": random_x, "target_y": 291})
    time.sleep(0.5)
    post(MOUSE_CLICK_URL, {"button": "left", "action": "click", "hold_time": 0.4})

def activate_window(player_info=PLAYER):
    MOUSE_CLICK_URL = "http://192.168.50.228:5000/mouse/click"
    SGO_TO_XY_URL = "http://192.168.50.200:5055/mouse/goto_xy_relative"

    x, y = get_hud_xy(HUD_COORDS, "safe_spot")
    post(SGO_TO_XY_URL, {
        "title": f"GoldMU || Player: {player_info}",
        "target_x": x,
        "target_y": y,
        "require_inside": False
    })
    time.sleep(0.2)
    post(MOUSE_CLICK_URL, {"button": "left", "action": "click", "hold_time": 0.5})
    time.sleep(0.35)
    return "Mouse clicked"

def go_to_kalima():
    logger.info("Going to Kalima, will open inventory and find Kalima Ticket")
    MOUSE_CLICK_URL = "http://192.168.50.228:5000/mouse/click"
    SGO_TO_XY_URL = "http://192.168.50.200:5055/mouse/goto_xy_relative"
    FIND_AND_HOVER_URL = "http://192.168.50.200:5055/screen/find-and-hover"

    warp_to("devias3")
    time.sleep(5)

    post(SGO_TO_XY_URL, {"title": "GoldMU || Player: CoZaBzdura", "target_x": 654, "target_y": 600, "require_inside": False})
    time.sleep(0.3)
    post(MOUSE_CLICK_URL, {"button": "left", "action": "click", "hold_time": 0.5})
    time.sleep(0.5)

    kalima_map = post(FIND_AND_HOVER_URL, {
        "title": "GoldMU || Player: CoZaBzdura",
        "rect": {"x": 630, "y": 230, "w": 165, "h": 246},
        "templates": ["kundun_map.png"],
        "thr": 0.85,
        "nms_radius": 25,
        "pick": "best",
        "hover": {"require_inside": False}
    })
    print(f"testing kalima: {kalima_map}")
    time.sleep(0.5)

    post(MOUSE_CLICK_URL, {"button": "left", "action": "click", "hold_time": 0.5})
    post(SGO_TO_XY_URL, {"title": "GoldMU || Player: CoZaBzdura", "target_x": 550, "target_y": 300, "require_inside": False})
    post(MOUSE_CLICK_URL, {"button": "left", "action": "click", "hold_time": 0.5})
    state_set("went_to_kalima", True)
    time.sleep(4)

def close_inventory():
    MOUSE_CLICK_URL = "http://192.168.50.228:5000/mouse/click"
    SGO_TO_XY_URL = "http://192.168.50.200:5055/mouse/goto_xy_relative"
    post(SGO_TO_XY_URL, {
        "title": f"GoldMU || Player: {PLAYER}",
        "target_x": 648,
        "target_y": 519,
        "require_inside": False
    })
    time.sleep(0.4)
    post(MOUSE_CLICK_URL, {"button": "left", "action": "click", "hold_time": 0.5})

def close_helper_popup():
    MOUSE_CLICK_URL = "http://192.168.50.228:5000/mouse/click"
    SGO_TO_XY_URL = "http://192.168.50.200:5055/mouse/goto_xy_relative"
    post(SGO_TO_XY_URL, {
        "title": f"GoldMU || Player: {PLAYER}",
        "target_x": 411,
        "target_y": 314,
        "require_inside": False
    })
    time.sleep(0.4)
    post(MOUSE_CLICK_URL, {"button": "left", "action": "click", "hold_time": 0.5})

def close_helper_popu_and_inventory():
    close_helper_popup()
    time.sleep(0.4)
    close_inventory()

def click_on_helper():
    MOUSE_CLICK_URL = "http://192.168.50.228:5000/mouse/click"
    SGO_TO_XY_URL = "http://192.168.50.200:5055/mouse/goto_xy_relative"
    CHECK_HELPER_ERROR_URL = "http://192.168.50.200:5055/screen/helper_inventory"
    activate_window()

    check_inv = post(CHECK_HELPER_ERROR_URL, {
        "title": f"GoldMU || Player: {PLAYER}",
        "rect": {"x": 295, "y": 228, "w": 225, "h": 116},
        "thr": 0.88,
        "pad": 2
    })
    if check_inv["state"] == "INV ON":
        logger.info("Closing popup and inventory...")
        close_helper_popu_and_inventory()

    post(SGO_TO_XY_URL, {"title": f"GoldMU || Player: {PLAYER}", "target_x": 190, "target_y": 41, "require_inside": False})
    time.sleep(0.4)
    post(MOUSE_CLICK_URL, {"button": "left", "action": "click", "hold_time": 0.5})
    time.sleep(0.4)
    post(SGO_TO_XY_URL, {"title": f"GoldMU || Player: {PLAYER}", "target_x": 240, "target_y": 41, "require_inside": False})
    return "Mouse clicked"

def run_ocr_for_debug():
    post(SCREEN_API, {
        "title": f"GoldMU || Player: {PLAYER}",
        "rect": {"x":29,"y":35,"w":110,"h":12},
        "psm": 7,
        "whitelist": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789(),"
    })

def full_reset():
    sleep_interruptible(1)
    send_message("/reset")
    clear_level_log()
    state_set("went_to_kalima", False)
    sleep_interruptible(4)

def find_aida_location(x: int, y: int, tol: int = 15):
    for loc in AIDA_LOCATIONS:
        if abs(loc["x"] - x) <= tol and abs(loc["y"] - y) <= tol:
            return loc
    return None

def find_atlans_location_by_id(loc_id: str):
    loc_id = (loc_id or "").strip()
    for loc in ATLANS_LOCATIONS:
        if loc.get("id") == loc_id:
            return loc
    return None

def find_aida_location_by_id(loc_id: str):
    loc_id = (loc_id or "").strip()
    for loc in AIDA_LOCATIONS:
        if loc.get("id") == loc_id:
            return loc
    return None

def find_kalima_location_by_id(loc_id: str):
    loc_id = (loc_id or "").strip()
    for loc in KALIMA_LOCATIONS:
        if loc.get("id") == loc_id:
            return loc
    return None

def find_lacleon_location_by_id(loc_id: str):
    loc_id = (loc_id or "").strip()
    for loc in LACLEON_LOCATIONS:
        if loc.get("id") == loc_id:
            return loc
    return None

@app.post("/bot/set-aida-location-by-id")
def api_set_aida_location_by_id():
    data = request.get_json(force=True, silent=True) or {}
    loc_id = data.get("id")
    if not loc_id:
        return jsonify(ok=False, error="Missing id"), 400

    loc = find_aida_location_by_id(loc_id)
    if not loc:
        return jsonify(ok=False, error="No matching Aida location", provided={"id": loc_id}), 404

    def _mut(st):
        st["map_change_position"] = True
        st["aida_map_loc"] = {
            "x": int(loc["x"]),
            "y": int(loc["y"]),
            "loc_x": int(loc["loc_x"]),
            "loc_y": int(loc["loc_y"]),
            "tolerance": int(loc.get("tolerance", 10)),
            "moobs": loc["moobs"]
        }

    state = state_mutate(_mut)
    return jsonify(ok=True, matched_id=loc["id"], aida_map_loc=state.get("aida_map_loc"))

@app.post("/bot/set-lacleon-location-by-id")
def api_set_lacleon_location_by_id():
    data = request.get_json(force=True, silent=True) or {}
    loc_id = data.get("id")
    if not loc_id:
        return jsonify(ok=False, error="Missing id"), 400

    loc = find_lacleon_location_by_id(loc_id)
    if not loc:
        return jsonify(ok=False, error="No matching LaCleon location", provided={"id": loc_id}), 404

    def _mut(st):
        st["map_change_position"] = True
        st["lacleon_map_loc"] = {
            "x": int(loc["x"]),
            "y": int(loc["y"]),
            "loc_x": int(loc["loc_x"]),
            "loc_y": int(loc["loc_y"]),
            "tolerance": int(loc.get("tolerance", 10)),
            "moobs": loc["moobs"]
        }

    state = state_mutate(_mut)
    return jsonify(ok=True, matched_id=loc["id"], lacleon_map_loc=state.get("lacleon_map_loc"))

@app.post("/bot/set-kalima-location-by-id")
def api_set_kalima_location_by_id():
    data = request.get_json(force=True, silent=True) or {}
    loc_id = data.get("id")
    if not loc_id:
        return jsonify(ok=False, error="Missing id"), 400

    loc = find_kalima_location_by_id(loc_id)
    if not loc:
        return jsonify(ok=False, error="No matching Kalima location", provided={"id": loc_id}), 404

    def _mut(st):
        st["map_change_position"] = True
        st["kalima_map_loc"] = {
            "x": int(loc["x"]),
            "y": int(loc["y"]),
            "loc_x": int(loc["loc_x"]),
            "loc_y": int(loc["loc_y"]),
            "tolerance": int(loc.get("tolerance", 10)),
            "moobs": loc["moobs"]
        }

    state = state_mutate(_mut)
    return jsonify(ok=True, matched_id=loc["id"], kalima_map_loc=state.get("kalima_map_loc"))

@app.get("/logs/search")
def logs_search():
    q = (request.args.get("q") or "").strip()
    if not q:
        return jsonify(ok=False, error="missing q"), 400

    limit = int(request.args.get("limit") or 200)
    tail  = int(request.args.get("tail") or 200000)
    icase = (request.args.get("icase") or "1") == "1"
    needle = q.lower() if icase else q

    buf = deque(maxlen=max(1, tail))
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                buf.append(line)
    except Exception as e:
        return jsonify(ok=False, error=f"log read failed: {e}"), 500

    out = []
    for line in buf:
        hay = line.lower() if icase else line
        if needle in hay:
            out.append(line.rstrip("\n"))
            if len(out) >= limit:
                break

    return jsonify(ok=True, q=q, icase=icase, tail=tail, limit=limit, count=len(out), lines=out)

def get_map_limits(map_name: str):
    limits = state_get("map_level_limits", {}) or {}
    cfg = limits.get(map_name) or {}
    return int(cfg.get("min", 1)), int(cfg.get("max", 400))

def create_party():
    SGO_TO_XY_URL = "http://192.168.50.200:5055/mouse/goto_xy_relative"
    MOUSE_CLICK_URL = "http://192.168.50.228:5000/mouse/click"

    activate_window(player_info=PARTY_PLAYER)
    post(KEY_API, {"keycode": 19, "press_time": 0.5}) #press letter P (open Party menu)

    post(KEY_API, {"keycode": 19, "press_time": 0.5}) #press letter P (close Party menu)

#------------------------ main loop ------------------------
state_file = load_state()
speedrun_reset_date = bool(state_file.get("run_spspeedrun_reset_dateeedrun", "2025"))
latest_warped_location = ""
first_run = True
zen = 0
while_loop = 0

RESET_HOUR = 4  # 04:00
LIVE = {}

def main_loop():
    logging.info("Main loop started")
    main_tick = 0

    global latest_warped_location, LIVE, first_run
    interval = CHECK_INTERVAL

    while not stop_event.is_set():
        try:
            with state_lock:
                snap = STATE_SNAPSHOT
                state = snap.get("state")

            if not state:
                stop_event.wait(interval)
                continue

            now = datetime.now()
            today = date.today().isoformat()

            last_reset = state_get("speedrun_reset_date")
            helper_state = "Running" if state.get("helper_status") == "PAUSE" else "Not running"

            update_level_timer(state["level"])

            logger.debug(f"level: {state["level"]}")


            # if state["level"] == 1 and not state["stats_added"]:
            #     logger.info("stats not added, adding...")
            #     activate_window()
            #     go_to_point(420, 275)
            #     if state["reset"] <= 169:
            #         add_stats()
            #     state_set("stats_added", True)
            #     send_message("/re auto")

            # run_speedrun = state_get("run_speedrun", False)
            # if run_speedrun and state["stats_added"] and state["level"] == 1:
            #     start_speedrun()
            #     state_set("run_speedrun", False)

            # # ---------------------------
            # # logika atakowania i lvlowania
            # if 1 <= state["level"] < 60:
            #     if is_at_position(state["location_coord_x"], state["location_coord_y"], 152, 237):
            #         logger.info("Lorencia Skeletons 19lvl")
            #         delta = [(660, 320), (597, 439), (420, 440)]
            #         round_attack(delta, hold_time=10)
            #     else:
            #         go_to_point(461, 81)

            # if 80 > state["level"] >= 60 and state["location_name"] == "Lorencia":
            #     logger.info("Time to Devias")
            #     warp_to("devias2")

            # if 82 >= state["level"] >= 60 and state["location_name"] == "Devias":
            #     if is_at_position(state["location_coord_x"], state["location_coord_y"], 7, 56):
            #         logger.info("Devias Elite Yeti & Queen X lvl")
            #         delta = [(473, 405), (597, 200), (568, 426), (460, 395), (600, 200), (450, 390)]
            #         round_attack(delta, hold_time=5)
            #     else:
            #         logger.info("Go to spot on Devias")
            #         go_to_point(166, 454)

            # if 100 > state["level"] >= 80 and state["location_name"] == "Devias":
            #     logger.info("Time to Atlans")
            #     warp_to("atlans")

            # if 121 >= state["level"] >= 80 and state["location_name"] == "Atlans":
            #     if is_at_position(state["location_coord_x"], state["location_coord_y"], 24, 122, tol=7):
            #         logger.info("Atlans Vepar 45lvl")
            #         if state["helper_status"] == "PLAY":
            #             logger.info("Double confirm, and run helper...")
            #             go_to_point(199, 320)
            #             click_on_helper()
            #     else:
            #         logger.info("Go to spot on Atlans")
            #         go_to_point(199, 320)

            # if 210 > state["level"] > 121 and state["location_name"] == "Atlans" and latest_warped_location != "atlans2":
            #     logger.info("Time to Atlans2")
            #     latest_warped_location = "atlans2"
            #     warp_to(latest_warped_location)

            # if 210 >= state["level"] > 121 and state["location_name"] == "Atlans" and latest_warped_location == "atlans2":
            #     # map_x = state_file["aida_map_loc"]["x"]
            #     # map_y = state_file["aida_map_loc"]["y"]
            #     # tolerance = state_file["aida_map_loc"]["tolerance"]
            #     if (
            #         is_at_position(state["location_coord_x"], state["location_coord_y"], 182, 91, tol=7)
            #         or is_at_position(state["location_coord_x"], state["location_coord_y"], 146, 111, tol=10)
            #     ):
            #         logger.info(f"Atlans2 Lizard King 70lvl, current pos: {state['location_coord_x']},{state['location_coord_y']}")
            #         if state["helper_status"] == "PLAY":
            #             logger.info("Double confirm, and run helper...")
            #             go_to_point(526, 378)
            #             click_on_helper()
            #     else:
            #         logger.info("Go to spot on Atlans2")
            #         go_to_point(526, 378)

            # aida_min, aida_max = get_map_limits("Aida")
            # if state["level"] > aida_min and state["location_name"] == "Atlans":
            #     logger.info("Time to Aida2")
            #     latest_warped_location = "aida2"
            #     warp_to(latest_warped_location)

            # logger.debug(f"debug {aida_max}, {state["level"]}, {aida_min}, {state["location_name"]}")
            # if aida_max >= state["level"] >= aida_min and state["location_name"] == "Aida":
            #     aida = state_get("aida_map_loc")
            #     map_x = aida["x"]
            #     map_y = aida["y"]
            #     map_loc_x = aida["loc_x"]
            #     map_loc_y = aida["loc_y"]
            #     tolerance = aida["tolerance"]

            #     if state_file["map_change_position"]:
            #         go_to_point(map_x, map_y)
            #         state_set("map_change_position", False)

            #     logger.debug(f"Checking, state: {state["location_coord_x"]} == {map_loc_x}, {state["location_coord_y"]} == {map_loc_y}, tol: {tolerance}")
            #     if is_at_position(state["location_coord_x"], state["location_coord_y"], map_loc_x, map_loc_y, tol=tolerance):
            #         logger.info(f"Aida2 {aida["moobs"]}, current pos: {state['location_coord_x']},{state['location_coord_y']}, desired pos: {map_loc_x},{map_loc_y}")
            #         if state["helper_status"] == "PLAY":
            #             logger.info("Double confirm, and run helper...")
            #             go_to_point(map_x, map_y)
            #             click_on_helper()
            #     else:
            #         logger.info("Go to spot on Aida2")
            #         if state["helper_status"] == "PAUSE":
            #             logger.info("Stop helper because Im going somewhere...")
            #             click_on_helper()
            #         go_to_point(map_x, map_y)

            # if state["level"] >= 325 and not state["resets_disabled"] and (state["location_name"] == "Aida" or state["location_name"] == "Lorencia"):
            #     logger.info("Time to Raklion/LaCleon")
            #     latest_warped_location = "raklion"
            #     warp_to(latest_warped_location)

            # if 400 > state["level"] >= 311 and state_file["start_kalima"] and not state_file["went_to_kalima"]:
            #     logger.info(f"Kalima state is {state_file["start_kalima"]}, going to kalima...")
            #     state_update({"start_kalima": False, "went_to_kalima": True})
            #     go_to_kalima()

            # if 400 > state["level"] >= 325 and state["location_name"] != "Kalima":
            #     lacleon = state_get("lacleon_map_loc")
            #     map_x = lacleon["x"]
            #     map_y = lacleon["y"]
            #     map_loc_x = lacleon["loc_x"]
            #     map_loc_y = lacleon["loc_y"]
            #     tolerance = lacleon["tolerance"]

            #     if state["location_name"] == "LaCleon":
            #         if is_at_position(state["location_coord_x"], state["location_coord_y"], map_loc_x, map_loc_y, tol=tolerance):
            #             logger.info(f"Raklion/LaCleon {lacleon["moobs"]}, current pos: {state['location_coord_x']},{state['location_coord_y']}")
            #             if state["helper_status"] == "PLAY":
            #                 go_to_point(map_x,map_y)
            #                 logger.info("activating helper")
            #                 click_on_helper()
            #         else:
            #             logger.info("Go to spot on Raklion/LaCleon")
            #             go_to_point(map_x,map_y)

            # if 400 > state["level"] >= 311 and state["location_name"] == "Kalima":
            #     logger.info("Kalima money exping...")
            #     kalima = state_get("kalima_map_loc")
            #     map_x = kalima["x"]
            #     map_y = kalima["y"]
            #     map_loc_x = kalima["loc_x"]
            #     map_loc_y = kalima["loc_y"]
            #     tolerance = kalima["tolerance"]

            #     if main_tick % 90 == 0:
            #         logger.info("Checking ZEN in Kalima")
            #         zen = check_zen()

            #     if state_file["map_change_position"]:
            #         go_to_point(map_x, map_y)
            #         state_file["map_change_position"] = False
            #         save_state(state_file)

            #     logger.debug(f"Checking, state: {state["location_coord_x"]} == {map_loc_x}, {state["location_coord_y"]} == {map_loc_y}, tol: {tolerance}")
            #     if is_at_position(state["location_coord_x"], state["location_coord_y"], map_loc_x, map_loc_y, tol=tolerance):
            #         logger.info(f"Kalima {kalima["moobs"]}, current pos: {state['location_coord_x']},{state['location_coord_y']}, desired pos: {map_loc_x},{map_loc_y}")
            #         if state["helper_status"] == "PLAY":
            #             print_txt = "Double confirm, and run helper..."
            #             go_to_point(map_x, map_y, print_txt)
            #             click_on_helper()
            #     else:
            #         logger.info("Go to spot on Kalima")
            #         if state["helper_status"] == "PAUSE":
            #             logger.info("Stop helper because Im going somewhere...")
            #             click_on_helper()
            #         print_txt = "still ongoing..."
            #         go_to_point(map_x, map_y, print_txt)
            # #------------------------------------

            # if state["level"] == 400 and not state["resets_disabled"]:
            #     logger.info("400lvl, doing reset...")
            #     state_set("stats_added", False)
            #     latest_warped_location = ""
            #     activate_window()
            #     stop_event.wait(0.4)
            #     full_reset()
            #     main_tick = 0

            # if now.hour >= RESET_HOUR and last_reset != today:
            #     logger.debug("setting up next run as speedrun")
            #     state_update({"run_speedrun": True, "speedrun_reset_date": today})
            #     logger.debug("[Turn on speedrun] speedrun_reset_date=True (daily 05:00)")

            # # -----------------------------
            # # HELPERY czy wszystko ok z grą
            # payload_inventory_state = {
            #     "title": "GoldMU || Player: CoZaBzdura",
            #     "rect": {"x": 630, "y": 496, "w": 30, "h": 40},
            #     "thr": 0.88,
            #     "pad": 2
            # }

            # CHECK_HELPER_ERROR_URL = "http://192.168.50.200:5055/screen/helper_inventory"
            # check_inv_payload = {
            #     "title": f"GoldMU || Player: {PLAYER}",
            #     "rect": {"x": 295, "y": 228, "w": 225, "h": 116},
            #     "thr": 0.88,
            #     "pad": 2
            # }
            # check_inv = post(CHECK_HELPER_ERROR_URL, check_inv_payload)
            # logger.debug(f"Safety checker inventory and popup: {check_inv["state"]}")
            # if check_inv["state"] == "INV ON":
            #     logger.debug("Closing popup and inventory...")
            #     close_helper_popu_and_inventory()

            # INVENTORY_STATE_URL = "http://192.168.50.200:5055/screen/inventory_state"
            # inventory_state = post(INVENTORY_STATE_URL, payload_inventory_state)
            # logger.debug(f"Safety checker inventory: {inventory_state["state"]}")
            # if inventory_state["state"] == "INV ON":
            #     logger.debug("inventory is open I need to close it...")
            #     time.sleep(0.7)
            #     close_inventory()

            main_tick += 1

        except Exception:
            logging.exception("Main loop error")

        stop_event.wait(interval)

def scraper_loop():
    global STATE_SNAPSHOT
    interval = 2

    while not stop_event.is_set():
        try:
            s = check_conditions()
            ts = time.time()
            with state_lock:
                STATE_SNAPSHOT = {"ts": ts, "state": s}
        except Exception:
            logging.exception("scraper error")

        stop_event.wait(interval)

def controller_loop():
    global LIVE, while_loop, first_run
    interval = CHECK_INTERVAL
    ready_sent = False

    while not stop_event.is_set():
        try:
            with state_lock:
                snap = STATE_SNAPSHOT
                state = snap["state"]

            if not state:
                stop_event.wait(interval)
                continue

            if state["helper_status"] == "PAUSE":
                helper_state = "Running"
            else:
                helper_state = "Not running"

            logger.info(
                f"Location: {state["location_name"]}, map_coords: {state["location_coord_x"]},{state["location_coord_y"]} "
                f"state lvl: {state["level"]}, Mouse RELATIVE position: {state["mouse_relative_pos"]["x"]},{state["mouse_relative_pos"]["y"]} "
            )

            system_usage = LIVE.get("system")
            if while_loop % 50 == 0:
                system_usage = get_system_usage()
                logger.info(
                    f"SYSTEM CPU {system_usage['cpu']}% | "
                    f"RAM {system_usage['ram_percent']}% "
                    f"({system_usage['ram_used_mb']:.0f}/{system_usage['ram_total_mb']:.0f} MB)"
                )

            LIVE = {
                "status": state["connected"],
                "player_name": state["player"],
                "location": state["location_name"],
                "location_coord_x": state["location_coord_x"],
                "location_coord_y": state["location_coord_y"],
                "level": int(state["level"]),
                "resets": int(state["reset"]),
                "time": state["time"],
                "is_it_speedrun": state["run_speedrun"],
                "health": state["health"],
                "exp_per_minute": state["exp_per_minute"],
                "zen": state["zen"],
                "while_loop": while_loop,
                "helper_state": helper_state,
                "system": system_usage,
                "resets_disabled": state.get("resets_disabled", False),
            }

            if not ready_sent:
                controller_ready.set()
                ready_sent = True
                logger.info("Controller ready → main_loop can start")

            while_loop += 1

        except Exception:
            logging.exception("controller error")

        stop_event.wait(interval)

@app.route("/")
def index():
    logs = []
    level_logs = []

    try:
        with open(LEVEL_LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            level_logs = list(deque(f, maxlen=400))
    except Exception:
        level_logs = ["[log file not found]"]

    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            logs = list(deque(f, maxlen=3000))
    except Exception:
        logs = ["[log file not found]"]

    atlans_options = [
        {"id": loc["id"], "label": f'{loc.get("id","")} {loc.get("moobs","")} ({loc.get("map","Atlans")} {loc.get("loc_x")},{loc.get("loc_y")})'}
        for loc in ATLANS_LOCATIONS
    ]

    aida_options = [
        {"id": loc["id"], "label": f'{loc.get("id","")} {loc.get("moobs","")} ({loc.get("map","Aida")} {loc.get("loc_x")},{loc.get("loc_y")})'}
        for loc in AIDA_LOCATIONS
    ]

    lacleon_options = [
        {"id": loc["id"], "label": f'{loc.get("id","")} {loc.get("moobs","")} ({loc.get("map","lacleon")} {loc.get("loc_x")},{loc.get("loc_y")})'}
        for loc in LACLEON_LOCATIONS
    ]

    kalima_options = [
        {"id": loc["id"], "label": f'{loc.get("id","")} {loc.get("moobs","")} ({loc.get("map","Kalima")} {loc.get("loc_x")},{loc.get("loc_y")})'}
        for loc in KALIMA_LOCATIONS
    ]

    return render_template(
        "index.html",
        live=LIVE,
        logs=logs,
        level_logs=level_logs,
        atlans_options=atlans_options,
        aida_options=aida_options,
        kalima_options=kalima_options,
        lacleon_options=lacleon_options
    )

if __name__ == "__main__":
    first_sleep = 0
    print(f"First sleep is {first_sleep}s")
    for i in range(first_sleep):
        print(i)
        time.sleep(1)

    ts = threading.Thread(target=scraper_loop, daemon=True)
    tc = threading.Thread(target=controller_loop, daemon=True)
    tm = threading.Thread(target=main_loop, daemon=True)
    ts.start()
    tc.start()
    tm.start()
    app.run(host="0.0.0.0", port=5065, debug=True, use_reloader=False)
