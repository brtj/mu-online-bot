from functions import requests_functions, hud_coords
from functions import config_loader
import logging
from logger_config import setup_logging
from datetime import datetime
import time

from functions.state_singleton import STATE, STATE_SECOND_PLAYER

setup_logging()
logger = logging.getLogger(__name__)

CONFIG = config_loader.load_config()
HOSTAPI = CONFIG["hostapi"]
BASE_URL = f"http://{HOSTAPI['ip']}:{HOSTAPI['port']}"

ENDPOINTS = {
    name: f"{BASE_URL}{path}"
    for name, path in HOSTAPI["endpoints"].items()
}

MAX_LOCATION_RETRIES = 4
LOCATION_RETRY_DELAY = 0.2

def check_helper_state(player_info=""):
    helper_request = requests_functions.post(ENDPOINTS["autorun_state"], {
        "title": f"{player_info}",
        "rect": hud_coords.get_rect("helper_state"),
        "debug_image": False
    })

    if helper_request["state"] == "PLAY":
        helper_status = "Not running"
    else:
        helper_status = "Running"

    return helper_status