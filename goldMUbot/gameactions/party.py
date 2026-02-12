import logging
import time
from functions import config_loader
from functions.requests_functions import post
from logger_config import setup_logging
from functions.host_api import (
    press_leter_i,
    press_leter_p,
    send_message,
    activate_window,
)
from functions.hud_coords import HUD_COORDS, get_hud_xy, get_rect

from functions.state_singleton import STATE

CONFIG = config_loader.load_config()
HOSTAPI = CONFIG["hostapi"]
HOSTAPI_BASE_URL = f"http://{HOSTAPI['ip']}:{HOSTAPI['port']}"
HOSTAPI_ENDPOINTS = {
    name: f"{HOSTAPI_BASE_URL}{path}" for name, path in HOSTAPI["endpoints"].items()
}
HIDAPI = CONFIG["hidapi"]
HIDAPI_BASE_URL = f"http://{HIDAPI['ip']}:{HIDAPI['port']}"
HIDAPI_ENDPOINTS = {
    name: f"{HIDAPI_BASE_URL}{path}" for name, path in HIDAPI["endpoints"].items()
}

setup_logging()
logger = logging.getLogger(__name__)


def check_if_its_in_party(player_info=None):
    activate_window(player_info=player_info)
    time.sleep(0.2)
    press_leter_p()
    time.sleep(0.3)

    payload = {
        "title": f"{player_info}",
        "rect": {"x": 0, "y": 0, "w": 800, "h": 650},
        "templates": ["party_aleelfisko.png"],
        "thr": 0.85,
        "nms_radius": 25,
        "pick": "best",
        "hover": {"require_inside": False},
    }
    party_status = post(HOSTAPI_ENDPOINTS["find_and_hover"], payload)
    time.sleep(0.2)
    logger.info(f"{party_status}")
    if party_status.get("ok") == True:
        post(
            HIDAPI_ENDPOINTS["mouse_click"],
            {"button": "left", "action": "click", "hold_time": 0.2},
        )
        x, y = get_hud_xy(HUD_COORDS, "party_window_join_party_button")
        post(
            HOSTAPI_ENDPOINTS["mouse_goto_xy_relative"],
            {
                "title": f"{player_info}",
                "target_x": x,
                "target_y": y,
                "require_inside": False,
            },
        )
        post(
            HIDAPI_ENDPOINTS["mouse_click"],
            {"button": "left", "action": "click", "hold_time": 0.2},
        )
        press_leter_p()
        time.sleep(0.3)
    else:
        press_leter_p()
        time.sleep(0.3)

    logger.info("Checking if in party ends...")
