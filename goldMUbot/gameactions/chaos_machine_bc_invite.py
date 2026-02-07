import logging
import time

from functions.requests_functions import post
from functions import config_loader
from gameactions.go_to_point import go_to_point_and_wait
from logger_config import setup_logging
from functions.host_api import send_message, activate_window
from gameactions.warp_to import warp_to

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

def chaos_machine_bc_invite(player_info):
  state = STATE.get_all()
  main_player_data = state.get("main_player_data") or {}

  actual_location = main_player_data["location_name"]
  actual_location_coord_x = main_player_data["location_coord_x"]
  warp_to(player_info, "noria", actual_location, actual_location_coord_x, sleept=1, timeout=2)

  go_to_point_and_wait(
    player_info=player_info, 
    mouse_x=502, 
    mouse_y=378, 
    target_loc_x=172, 
    target_loc_y=92
  );time.sleep(4)
  payload_inventory_box = {
      "title": f"{player_info}",
      "rect": { "x": 0, "y": 0, "w": 800, "h": 650 },
      "templates": ["noria_inventory_box.png"],
      "thr": 0.55,
      "nms_radius": 25,
      "pick": "best",
      "hover": { "require_inside": False }
  }
  payload_inventory_box_status = post(HOSTAPI_ENDPOINTS["find_and_hover"], payload_inventory_box)
  time.sleep(0.7)
  if payload_inventory_box_status.get("ok") == True:
    post(HIDAPI_ENDPOINTS["mouse_click"], {"button": "left", "action": "click", "hold_time": 0.2})
    time.sleep(2.5)
    post(HOSTAPI_ENDPOINTS["mouse_goto_xy_relative"], { 
        "title": f"{player_info}",
        "target_x": 524,
        "target_y": 469,
        "require_inside": False #click on store 3
    });time.sleep(1)
    post(HIDAPI_ENDPOINTS["mouse_click"], {"button": "left", "action": "click", "hold_time": 0.2})
    time.sleep(1)
    payload_blood_bone7_box = {
        "title": f"{player_info}",
        "rect": { "x": 0, "y": 0, "w": 800, "h": 650 },
        "templates": ["blood_bone_7.png"],
        "thr": 0.55,
        "nms_radius": 25,
        "pick": "best",
        "hover": { "require_inside": False }
    }
    payload_blood_bone7_box_status = post(HOSTAPI_ENDPOINTS["find_and_hover"], payload_blood_bone7_box)
    if payload_blood_bone7_box_status.get("ok") == True:
      post(HIDAPI_ENDPOINTS["mouse_click"], {"button": "right", "action": "click", "hold_time": 0.2})
      time.sleep(0.5)
    payload_scroll_of_arch7_box = {
        "title": f"{player_info}",
        "rect": { "x": 0, "y": 0, "w": 800, "h": 650 },
        "templates": ["scroll_of_arch_7.png"],
        "thr": 0.55,
        "nms_radius": 25,
        "pick": "best",
        "hover": { "require_inside": False }
    }
    payload_scroll_of_arch7_box_status = post(HOSTAPI_ENDPOINTS["find_and_hover"], payload_scroll_of_arch7_box)
    if payload_scroll_of_arch7_box_status.get("ok") == True:
      post(HIDAPI_ENDPOINTS["mouse_click"], {"button": "right", "action": "click", "hold_time": 0.2})
      time.sleep(0.5)

    # zamknąć inventory
    # podejść do chaos machine 
    # otworzyć inventory, wziąć chaosa jeżeli nie ma w inventory
    # otworzyć chaos machine
    # przenieść blood + scroll + jewel 
    # zakrecic pralką
    # jeżeli wyszło przenieść do inventory, jeżeli nie to powtórzyć cały proces max 2x 
