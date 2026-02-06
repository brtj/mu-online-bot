import logging
import time
from functions import config_loader
from logger_config import setup_logging
from functions.host_api import send_message, activate_window
from functions.hud_coords import HUD_COORDS, get_hud_xy, get_rect
from functions.requests_functions import post

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

def jewels_to_bank(player_info=None):
  logger.info("Put all jewels to bank...")
  activate_window(player_info=player_info);time.sleep(0.1)

  x, y = get_hud_xy(HUD_COORDS, "inventory_icon")
  post(HOSTAPI_ENDPOINTS["mouse_goto_xy_relative"], { 
      "title": f"{player_info}",
      "target_x": x,
      "target_y": y,
      "require_inside": False
  })
  time.sleep(0.2)
  post(HIDAPI_ENDPOINTS["mouse_click"], {"button": "left", "action": "click", "hold_time": 0.2})
  time.sleep(0.3)
  payload = {
      "title": f"{player_info}",
      "rect": { "x": 0, "y": 0, "w": 800, "h": 650 },
      "templates": ["inventory_jewel.png"],
      "thr": 0.85,
      "nms_radius": 25,
      "pick": "best",
      "hover": { "require_inside": False }
  }
  jewel_inventory_status = post(HOSTAPI_ENDPOINTS["find_and_hover"], payload)
  logger.debug(f"{jewel_inventory_status}")
  if jewel_inventory_status.get("ok") == True:
    post(HIDAPI_ENDPOINTS["mouse_click"], {"button": "left", "action": "click", "hold_time": 0.2})
    payload = {
        "title": f"{player_info}",
        "rect": { "x": 0, "y": 0, "w": 800, "h": 650 },
        "templates": ["jewel_bank_inventory.png"],
        "thr": 0.85,
        "nms_radius": 25,
        "pick": "best",
        "hover": { "require_inside": False }
    }
  