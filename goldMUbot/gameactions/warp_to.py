import logging
import time
from functions import config_loader
from logger_config import setup_logging
from functions.host_api import send_message, activate_window

from functions.state_singleton import STATE

setup_logging()
logger = logging.getLogger(__name__)


def warp_to(player_info, desired_location, actual_location, actual_location_coord_x, sleept=1, timeout=30):
    activate_window(player_info=player_info);time.sleep(0.2)
    logger.info(f"warping from {actual_location} to {desired_location}")
    send_message(f"dobra zwijam sie do {desired_location}", player_info=player_info)
    send_message(f"/warp {desired_location}", player_info=player_info)
    wait_for_location_name_change(actual_location, actual_location_coord_x, timeout=timeout)
    time.sleep(sleept)

def wait_for_location_name_change(before_location, before_location_coord_x, timeout=30, interval=0.5):
    start = time.time()
    before_name = before_location
    before_loc_x = before_location_coord_x

    while True:
        state = STATE.get_all()
        player_data = state.get("player_data") or {}

        after_name = player_data["location_name"]
        after_loc_x = player_data["location_coord_x"]

        if after_name != before_name and after_loc_x != before_loc_x:
            logger.info(f"Warped from {before_name} to {after_name}")
            return after_name

        if time.time() - start >= timeout:
            return None

        time.sleep(interval)
        logger.info(f"Warp process... waiting..., before: {before_name}, after: {after_name}, before x: {before_loc_x}, after x: {after_loc_x}")
