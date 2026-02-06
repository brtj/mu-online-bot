import logging
import time
from functions import config_loader
from logger_config import setup_logging
from functions.host_api import send_message, activate_window
from gameactions.warp_to import warp_to

from functions.state_singleton import STATE

setup_logging()
logger = logging.getLogger(__name__)



logger = logging.getLogger(__name__)

def chaos_machine_bc_invite():
  # warp to noria 
  # go to inventory
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