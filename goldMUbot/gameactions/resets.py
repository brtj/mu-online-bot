import logging
import time
from functions import config_loader
from gameactions.random_messages import generate_reset_message
from logger_config import setup_logging
from functions.host_api import send_message, activate_window

setup_logging()
logger = logging.getLogger(__name__)


def elf_reset(player_info="", reset_count=0):
    activate_window(player_info=player_info)
    logger.info("reset done")
    reset_message = generate_reset_message(reset_count)
    # send_message(player_info=player_info, text=f"/post {reset_message}")
    send_message(player_info=player_info, text="/reset")
    time.sleep(4)  # sleep to change map


def dk_reset(player_info="", reset_count=0):
    activate_window(player_info=player_info)
    logger.info("reset done")
    send_message(player_info=player_info, text="/reset")
    time.sleep(4)  # sleep to change map
