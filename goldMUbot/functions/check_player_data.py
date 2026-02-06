from functions import requests_functions, hud_coords
from functions import config_loader
import logging
from logger_config import setup_logging
from datetime import datetime

from functions.state_singleton import STATE

setup_logging()
logger = logging.getLogger(__name__)

CONFIG = config_loader.load_config()
HOSTAPI = CONFIG["hostapi"]
BASE_URL = f"http://{HOSTAPI['ip']}:{HOSTAPI['port']}"

ENDPOINTS = {
    name: f"{BASE_URL}{path}"
    for name, path in HOSTAPI["endpoints"].items()
}

def player_data(player_info=""):
    title_request = requests_functions.post(ENDPOINTS["parse_title"], {
        "title": f"{player_info}",
        "topmost": False
    })

    helper_request = requests_functions.post(ENDPOINTS["autorun_state"], {
        "title": f"{player_info}",
        "rect": hud_coords.get_rect("helper_state"),
        "debug_image": False
    })

    if helper_request["state"] == "PLAY":
        helper_status = "Not running"
    else:
        helper_status = "Running"

    health_request = requests_functions.post(ENDPOINTS["ocr_health"], {
        "title": f"{player_info}",
        "rect": hud_coords.get_rect("health_box")
    })

    exppm_request = requests_functions.post(ENDPOINTS["ocr_exp_per_minute"], {
        "title": f"{player_info}",
        "rect": hud_coords.get_rect("exppm_box")
    })

    mouse_rel_request = requests_functions.post(ENDPOINTS["mouse_position_relative"], {
        "title": f"{player_info}"
    })
    mouse_position = requests_functions.request_get(ENDPOINTS["mouse_position"])

    conn_status = True if "Connected" in (title_request.get("raw", "") or "") else False

    location_request = requests_functions.post(ENDPOINTS["screen_ocr"], {
        "title": f"{player_info}",
        "rect": hud_coords.get_rect("location_box"),
        "psm": 7,
        "whitelist": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789(),"
    })

    try:
        parsed = location_request["parsed"]
        location_name = parsed["name"]
        location_x = parsed["x"]
        location_y = parsed["y"]
        logger.debug("Location debug: %s, %s, %s", location_name, location_x, location_y)
    except (TypeError, KeyError):
        logger.debug("Location raw ERROR: %s", location_request)
        location_name = "not_available"
        location_x = 0
        location_y = 0

    check_party_state = "to do 2"
    now = datetime.now().strftime("%H:%M:%S")

    result = {
        "time": now,
        "player": title_request.get("player") or player_info,
        "player_in_party": check_party_state,
        "level": title_request.get("level") or 0,
        "exp_per_minute": exppm_request.get("digits") or 0,
        "reset": title_request.get("reset") or 0,
        "rect": title_request.get("rect"),
        "location_name": location_name,
        "location_coord_x": location_x,
        "location_coord_y": location_y,
        "mouse_position": mouse_position,
        "mouse_relative_pos": mouse_rel_request or {},
        "helper_status": helper_status,
        "health": health_request.get("value") or 0,
        "connected": conn_status
    }

    # ✅ zapis do stanu (1) jako ostatni snapshot
    STATE.update_dict("player_data", result)

    # ✅ zapis do stanu (2) per player (jeśli chcesz historię per gracz)
    # key = result.get("player") or player_info or "unknown"
    # STATE.patch({"players": {**STATE.get("players", {}), key: result}})  # proste, ale czyta+pisze całość

    return result