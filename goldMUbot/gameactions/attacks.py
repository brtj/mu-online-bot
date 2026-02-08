from functions.location_checks import is_at_position
from gameactions.go_to_point import go_to_point_and_wait
from gameactions.helper_attack import click_on_helper
from functions.host_api import activate_window, check_map_on, press_key
from functions.host_api import send_message
import logging, time
from gameactions.random_messages import generate_mu_party_message, generate_spot_message
from logger_config import setup_logging

from functions import config_loader
from functions.state_singleton import STATE, STATE_SECOND_PLAYER
from functions.hud_coords import HUD_COORDS, get_hud_xy, get_rect
from functions.requests_functions import post
from functions.helper_request import check_helper_state

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


# sposób na atak do czasu az bedzie mozna uzywac helper (>=80lvl)
def round_attack(player_info, deltas, step_delay=0.005, pause_range=(0.1, 0.4), hold_time=1, level_max=100, coord_x=0, coord_y=0, tol=20):
    logger.info("Attacking...")

    activate_window(player_info=player_info)

    x, y = get_hud_xy(HUD_COORDS, "safe_spot")
    post(HOSTAPI_ENDPOINTS["mouse_goto_xy_relative"], {
        "title": f"{player_info}",
        "target_x": x,
        "target_y": y,
        "require_inside": False
    }) #click on safe spot
    time.sleep(0.25)
    post(HIDAPI_ENDPOINTS["mouse_click"], {"button": "left", "action": "click", "hold_time": 0.5})

    if check_map_on(player_info=player_info) == "MAP ON":
        logger.info("Map is ON need to turn it OFF")
        press_key_payload = {"keycode": 43, "press_time": 1} #press tab
        press_key(payload=press_key_payload)
        time.sleep(0.3)

    spot_message = generate_spot_message(level_max)
    send_message(f"{spot_message}", player_info=player_info)

    delta360 = [(400, 100), (250, 300), (580, 300), (400, 400)]
    payload_click360 = {"button": "right", "action": "click", "hold_time": 1}
    for dx, dy in delta360:
        post(HOSTAPI_ENDPOINTS["mouse_goto_xy_relative"], {
            "title": f"{player_info}",
            "target_x": dx,
            "target_y": dy,
            "sleep_s": 0.005,
            "require_inside": False
        })
        post(HIDAPI_ENDPOINTS["mouse_click"], payload_click360)
        time.sleep(0.05)
    
    TIMEOUT_SEC = 7 * 60  # 7 minut
    start_ts = time.monotonic()

    if player_info == "AleElfisko":
        state = STATE.get_all()
        player_data = state.get("main_player_data") or {}
    elif player_info == "AleToBot":
        state = STATE_SECOND_PLAYER.get_all()
        player_data = state.get("second_player_data") or {}


    current_level = player_data["level"]
    while current_level <= level_max:
        if time.monotonic() - start_ts > TIMEOUT_SEC:
            logger.warning(
                f"Level loop timeout after {TIMEOUT_SEC}s "
                f"(current_level={current_level}, level_max={level_max})"
            )
            break

        if player_info == "AleElfisko":
            state = STATE.get_all()
            player_data = state.get("main_player_data") or {}
        elif player_info == "AleToBot":
            state = STATE_SECOND_PLAYER.get_all()
            player_data = state.get("second_player_data") or {}

        try:
            location_name = player_data["location_name"]
            location_x = player_data["location_coord_x"]
            location_y = player_data["location_coord_y"]
            logger.debug("Location debug: %s, %s, %s", location_name, location_x, location_y)
        except (TypeError, KeyError):
            logger.debug("Location raw ERROR: %s", player_data)
            location_name = "not_available"
            location_x = 0
            location_y = 0

        if not is_at_position(
            location_x,
            location_y,
            coord_x,
            coord_y,
            tol=tol
        ):
            logger.warning(
                "[SAFE EXIT] Player not at expected position — aborting loop"
            )
            logger.info(f"SAFE EXIT details: location_x={location_x}, location_y={location_y}, expected_x={coord_x}, expected_y={coord_y}, tol={tol}")
            break

        payload_click = {"button": "right", "action": "click", "hold_time": hold_time}
        for dx, dy in deltas:
            post(HOSTAPI_ENDPOINTS["mouse_goto_xy_relative"], {
                "title": f"{player_info}",
                "target_x": dx,
                "target_y": dy,
                "require_inside": False
            })
            post(HIDAPI_ENDPOINTS["mouse_click"], payload_click)

            post(LOCALAPI_ENDPOINTS["run_scraper_on_demand"], {})

            if player_info == "AleElfisko":
                state = STATE.get_all()
                player_data = state.get("main_player_data") or {}
            elif player_info == "AleToBot":
                state = STATE_SECOND_PLAYER.get_all()
                player_data = state.get("second_player_data") or {}
            
            current_level = player_data["level"]
        logger.info(f"Round attack, current level: {current_level}")


def attack_no_helper_on_spot(player_info, location_coord_x, location_coord_y, desired_coord_x, desired_coord_y, mouse_on_map_x, mouse_on_map_y, delta, level_max=100, print_txt="no helper attack", ):
  if is_at_position(location_coord_x, location_coord_y, desired_coord_x, desired_coord_y, tol=20):
      round_attack(player_info=player_info, hold_time=3, level_max=level_max, coord_x=desired_coord_x, coord_y=desired_coord_y, deltas=delta, tol=20)
  else:
    go_to_point_and_wait(player_info=player_info, mouse_x=mouse_on_map_x, mouse_y=mouse_on_map_y, target_loc_x=desired_coord_x, target_loc_y=desired_coord_y, print_txt=print_txt)


def attack_with_helper_on_spot(player_info, mouse_on_map_x, mouse_on_map_y, desired_coord_x, desired_coord_y, player_location_name, tolerance=8, timeout=80, print_txt="helper attack", send_message=False):
  if player_info == "AleElfisko":
    state = STATE.get_all()
    player_data = state.get("main_player_data") or {}
  elif player_info == "AleToBot":
    state = STATE_SECOND_PLAYER.get_all()
    player_data = state.get("second_player_data") or {}

  if is_at_position(player_data["location_coord_x"], player_data["location_coord_y"], desired_coord_x, desired_coord_y):
    check_helper_status = check_helper_state(player_info=player_info)
    if check_helper_status == "Not running":
      logger.info("I need to turn on helper...")
      go_to_point_and_wait(player_info=player_info, mouse_x=mouse_on_map_x, mouse_y=mouse_on_map_y, target_loc_x=desired_coord_x, target_loc_y=desired_coord_y, timeout=timeout, tol=tolerance, print_txt=print_txt)
      
      check_helper_status = check_helper_state(player_info=player_info)
      if check_helper_status == "Not running":
        click_on_helper(player_info=player_info)
        time.sleep(0.4)

      if send_message:
        message = generate_mu_party_message(player_location_name, desired_coord_x, desired_coord_y)
        send_message(f"{message}", player_info=player_info)
    else:
      logger.debug("Helper is running")

  else:
    logger.info(f"go to spot on XYZ - {desired_coord_x},{desired_coord_y}")
    go_to_point_and_wait(player_info=player_info, mouse_x=mouse_on_map_x, mouse_y=mouse_on_map_y, target_loc_x=desired_coord_x, target_loc_y=desired_coord_y, timeout=timeout, tol=tolerance, print_txt=print_txt)

