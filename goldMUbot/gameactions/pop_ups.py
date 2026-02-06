import logging
import time
from logger_config import setup_logging
from functions.host_api import activate_window
from functions.requests_functions import post
from functions.hud_coords import get_hud_xy, HUD_COORDS
from functions import config_loader

from functions.state_singleton import STATE

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

LOCALAPI = CONFIG["playerapi"]
LOCALAPI_BASE_URL = f"http://{LOCALAPI['ip']}:{LOCALAPI['port']}"
LOCALAPI_ENDPOINTS = {
    name: f"{LOCALAPI_BASE_URL}{path}"
    for name, path in LOCALAPI["endpoints"].items()
}


def popups_closer(player_info):
    payload_click = {"button": "left", "action": "click", "hold_time": 0.3}

    payload = {
        "title": f"{player_info}",
        "rect": { "x": 0, "y": 0, "w": 800, "h": 650 },
        "templates": ["ok_button_icon.png"],
        "thr": 0.85,
        "nms_radius": 25,
        "pick": "best",
        "hover": { "require_inside": False }
    }
    popup_status = post(HOSTAPI_ENDPOINTS["find_and_hover"], payload)
    logger.debug(f"{popup_status}")
    if popup_status.get("ok") == True:
        logger.info("need to close popup with OK button")
        logger.debug("need to close popup with OK button")
        logger.debug(popup_status)
        logger.debug(player_info)
        post(HIDAPI_ENDPOINTS["mouse_click"], payload_click)
        time.sleep(0.1)

    payload_close_button_x = {
        "title": f"{player_info}",
        "rect": { "x": 0, "y": 0, "w": 800, "h": 650 },
        "templates": ["close_button_x.png"],
        "thr": 0.85,
        "nms_radius": 25,
        "pick": "best",
        "hover": { "require_inside": False }
    }
    popup_status_close_button_x = post(HOSTAPI_ENDPOINTS["find_and_hover"], payload_close_button_x)
    logger.debug(f"{popup_status_close_button_x}")
    if popup_status_close_button_x.get("ok") == True:
        logger.info("need to close popup with X close button")
        post(HIDAPI_ENDPOINTS["mouse_click"], payload_click)
        time.sleep(0.1)

    # system popum menu bottom right
    payload_close_menu = {
        "title": f"{player_info}",
        "rect": { "x": 0, "y": 0, "w": 800, "h": 650 },
        "templates": ["system_button_pressed.png"],
        "thr": 0.999,
        "nms_radius": 25,
        "pick": "best",
        "hover": { "require_inside": False }
    }
    popup_status_close_menu = post(HOSTAPI_ENDPOINTS["find_and_hover"], payload_close_menu)
    logger.debug(f"{popup_status_close_menu}")
    if popup_status_close_menu.get("ok") == True:
        logger.info("need to close popup system menu")
        post(HIDAPI_ENDPOINTS["mouse_click"], payload_click)
        time.sleep(0.1)
