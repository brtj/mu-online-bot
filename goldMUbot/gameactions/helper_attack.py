import logging
import time
from logger_config import setup_logging
from functions.host_api import activate_window
from functions import requests_functions, hud_coords
from functions.requests_functions import post
from functions.hud_coords import get_hud_xy, HUD_COORDS
from functions import config_loader

from functions.state_singleton import STATE


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

setup_logging()
logger = logging.getLogger(__name__)

def click_on_helper(player_info):
    activate_window(player_info=player_info)

    post(LOCALAPI_ENDPOINTS["run_scraper_on_demand"], {})
    state = STATE.get_all()
    main_player_data = state.get("main_player_data") or {}
    helper_status = main_player_data["helper_status"]

    if helper_status != "Running":
        logger.info("Helper is not Running, need to turn it on")
        x, y = get_hud_xy(HUD_COORDS, "helper_icon")
        post(HOSTAPI_ENDPOINTS["mouse_goto_xy_relative"], {"title": f"{player_info}", "target_x": x, "target_y": y, "require_inside": False})
        time.sleep(0.4)
        post(HIDAPI_ENDPOINTS["mouse_click"], {"button": "left", "action": "click", "hold_time": 0.5})
        time.sleep(0.3)
    x, y = get_hud_xy(HUD_COORDS, "safe_spot")
    post(HOSTAPI_ENDPOINTS["mouse_goto_xy_relative"], {"title": f"{player_info}", "target_x": x, "target_y": y, "require_inside": False})    

    return "Mouse clicked"

def click_on_helper_to_turn_off(player_info):
    activate_window(player_info=player_info)

    x, y = get_hud_xy(HUD_COORDS, "helper_icon")
    post(HOSTAPI_ENDPOINTS["mouse_goto_xy_relative"], {"title": f"{player_info}", "target_x": x, "target_y": y, "require_inside": False})
    time.sleep(0.3)
    post(HIDAPI_ENDPOINTS["mouse_click"], {"button": "left", "action": "click", "hold_time": 0.5})
    time.sleep(0.3)
    x, y = get_hud_xy(HUD_COORDS, "safe_spot")
    post(HOSTAPI_ENDPOINTS["mouse_goto_xy_relative"], {"title": f"{player_info}", "target_x": x, "target_y": y, "require_inside": False})   