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
  player_data = state.get("player_data") or {}

  actual_location = player_data["location_name"]
  actual_location_coord_x = player_data["location_coord_x"]
  warp_to(player_info, "noria", actual_location, actual_location_coord_x, sleept=1, timeout=2)

  go_to_point_and_wait(
    player_info=player_info, 
    mouse_x=500, 
    mouse_y=378, 
    target_loc_x=172, 
    target_loc_y=92
  );time.sleep(1)

    
  # post(HOSTAPI_ENDPOINTS["mouse_goto_xy_relative"], { 
  #     "title": f"{player_info}",
  #     "target_x": 409,
  #     "target_y": 209,
  #     "require_inside": False
  # });time.sleep(2)
  # logger.info("mouse move2")
  # post(HOSTAPI_ENDPOINTS["mouse_goto_xy_relative"], { 
  #     "title": f"{player_info}",
  #     "target_x": 450,
  #     "target_y": 166,
  #     "require_inside": False
  # });time.sleep(1)
  # logger.info("mouse click")
  # post(HIDAPI_ENDPOINTS["mouse_click"], {
  #     "button": "left",
  #     "action": "click",
  #     "hold_time": 0.30
  # })
  # post(HOSTAPI_ENDPOINTS["mouse_goto_xy_relative"], { 
  #     "title": f"{player_info}",
  #     "target_x": 524,
  #     "target_y": 469,
  #     "require_inside": False #click on store 3
  # });time.sleep(1)
  # post(HIDAPI_ENDPOINTS["mouse_click"], {
  #     "button": "left",
  #     "action": "click",
  #     "hold_time": 0.30
  # })
  
  # takie things if necessary
  # open bank take chaos
  # go to chaos machine
  # put everything in chaos machine
  # generate invitation
  # if failed try again (if resources available)


    # warp_to(
    #   player_info=main_player_name,
    #   desired_location=warp_to_location,
    #   actual_location=main_player_location_name,
    #   actual_location_coord_x=main_player_location_x,
    # )