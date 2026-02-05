import logging
from logger_config import setup_logging
import time
from functions.hud_coords import get_rect
from functions.requests_functions import post

setup_logging()
logger = logging.getLogger(__name__)

from functions import config_loader



CONFIG = config_loader.load_config()
HOSTAPI = CONFIG["hostapi"]
HOSTAPI_BASE_URL = f"http://{HOSTAPI['ip']}:{HOSTAPI['port']}"
HOSTAPI_ENDPOINTS = {
    name: f"{HOSTAPI_BASE_URL}{path}"
    for name, path in HOSTAPI["endpoints"].items()
}

HOSTAPI_ENDPOINTS["screen_ocr"]

def get_location_state(player_info="") -> dict:
    location_request = post(HOSTAPI_ENDPOINTS["screen_ocr"], {
        "title": f"{player_info}",
        "rect": get_rect("location_box"),
        "psm": 7,
        "whitelist": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789(),"
    })

    try:
        parsed = location_request["parsed"]
        location_name = parsed["name"]
        location_x    = int(parsed["x"])
        location_y    = int(parsed["y"])

        logger.debug(
            f"Location debug: {parsed['name']}, {parsed['x']}, {parsed['y']}"
        )

        return {
            "ok": True,
            "location_name": location_name,
            "location_coord_x": location_x,
            "location_coord_y": location_y,
            "raw": location_request,
        }
    except (TypeError, KeyError, ValueError):
        logger.debug(f"Location raw ERROR: {location_request}")
        return {
            "ok": False,
            "location_name": "not_available",
            "location_coord_x": 0,
            "location_coord_y": 0,
            "raw": location_request,
        }


# sprawdzenie czy jest na pozycji, porownanie tego co jest z gra a to co bylo klikane myszka
def is_at_position(x, y, tx, ty, tol=10):
    dx = abs(x - tx)
    dy = abs(y - ty)

    if dx <= tol and dy <= tol:
        return True

    # LOG TYLKO GDY FALSE
    if dx > tol and dy > tol:
        reason = f"x out (dx={dx}), y out (dy={dy}), tol={tol}"
    elif dx > tol:
        reason = f"x out (dx={dx}), tol={tol}"
    else:
        reason = f"y out (dy={dy}), tol={tol}"

    logger.info(
        f"[is_at_position=False] | pos=({x},{y}) target=({tx},{ty}) | {reason}"
    )

    return False

def wait_until_at_position(tx, ty, tol=10, timeout=80, interval=3, player_info=""):
    start = time.time()

    while True:
        st = get_location_state(player_info=player_info)
        if st.get("ok"):
            x = st["location_coord_x"]
            y = st["location_coord_y"]
            if is_at_position(x, y, tx, ty, tol=tol):
                return True

        if time.time() - start >= timeout:
            return False

        time.sleep(interval)