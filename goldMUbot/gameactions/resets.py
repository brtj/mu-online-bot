import logging
import time
from functions import config_loader
from logger_config import setup_logging
from functions.host_api import send_message, activate_window

setup_logging()
logger = logging.getLogger(__name__)



def elf_reset(player_info=""):
  activate_window(player_info=player_info)
  logger.info("reset done")
  send_message(player_info=player_info, text="To juz moj {reset_count} reset, a jak u was?")
  send_message(player_info=player_info, text="/reset")
  time.sleep(4) #sleep to change map