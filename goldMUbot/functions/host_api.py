from functions.requests_functions import post
from functions import config_loader
from logger_config import setup_logging
from functions.hud_coords import HUD_COORDS, get_hud_xy, get_rect

import logging
import time

setup_logging()
logger = logging.getLogger(__name__)

CONFIG = config_loader.load_config()
HOSTAPI = CONFIG["hostapi"]
HOSTAPI_BASE_URL = f"http://{HOSTAPI['ip']}:{HOSTAPI['port']}"
HOSTAPI_ENDPOINTS = {
    name: f"{HOSTAPI_BASE_URL}{path}"
    for name, path in HOSTAPI["endpoints"].items()
}
HIDAPI = CONFIG["hidapi"]
HIDAPI_BASE_URL = f"http://{HIDAPI['ip']}:{HIDAPI['port']}"
HIDAPI_ENDPOINTS = {
    name: f"{HIDAPI_BASE_URL}{path}"
    for name, path in HIDAPI["endpoints"].items()
}


def send_message(text: str, player_info=""):
    logger.info(f"{text}, {player_info}")
    payload = {
        "title": f"{player_info}",
        "text": text
    }
    return post(HOSTAPI_ENDPOINTS["send_message"], payload)

def activate_window(player_info=""):

    x, y = get_hud_xy(HUD_COORDS, "safe_spot")
    post(HOSTAPI_ENDPOINTS["mouse_goto_xy_relative"], { 
        "title": f"{player_info}",
        "target_x": x,
        "target_y": y,
        "require_inside": False
    })
    time.sleep(0.2)
    post(HIDAPI_ENDPOINTS["mouse_click"], {"button": "left", "action": "click", "hold_time": 0.2})
    x, y = get_hud_xy(HUD_COORDS, "shortcut_w_box")
    post(HOSTAPI_ENDPOINTS["mouse_goto_xy_relative"], { 
        "title": f"{player_info}",
        "target_x": x,
        "target_y": y,
        "require_inside": False
    })
    post(HIDAPI_ENDPOINTS["mouse_click"], {"button": "left", "action": "click", "hold_time": 0.2})
    post(HIDAPI_ENDPOINTS["mouse_click"], {"button": "left", "action": "click", "hold_time": 0.1})
    time.sleep(0.2)
    return "Mouse clicked"


def press_key(payload={}):
    post(HIDAPI_ENDPOINTS["press_key"], payload)


def check_map_on(player_info=""):
    time.sleep(0.1)
    payload = {
        "title": f"{player_info}",
        "rect": get_rect("mapon_box"),
        "min_white_ratio": 0.34
    }
    r = post(HOSTAPI_ENDPOINTS["screen_map"], payload)
    logger.info(f"Check map on state: {r}")
    time.sleep(0.2)
    return r["state"]