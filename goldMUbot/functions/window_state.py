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
    name: f"{HOSTAPI_BASE_URL}{path}" for name, path in HOSTAPI["endpoints"].items()
}
HIDAPI = CONFIG["hidapi"]
HIDAPI_BASE_URL = f"http://{HIDAPI['ip']}:{HIDAPI['port']}"
HIDAPI_ENDPOINTS = {
    name: f"{HIDAPI_BASE_URL}{path}" for name, path in HIDAPI["endpoints"].items()
}


def window_state(player_info=""):
    window_state = post(HOSTAPI_ENDPOINTS["window_state"], {"title": f"{player_info}"})
    logger.info(f"Window state: {window_state}")

    return window_state.get("active", False)
