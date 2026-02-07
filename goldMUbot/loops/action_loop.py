import logging, time
from functions.state_singleton import STATE, STATE_SECOND_PLAYER
from functions import config_loader

from loops.second_player_loop import second_player_loop
from loops.main_player_loop import main_player_loop

logger = logging.getLogger(__name__)


from functions.requests_functions import post

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

TYPE_GAME = CONFIG.get("type_game", "single")

def action_loop(stop_event, interval=1):
    logger.info("Action loop started")

    last_log_sig = None  # żeby nie spamować logów

    time.sleep(2)  # dajmy czas na zebranie pierwszych danych

    last_check_inventory = 0

    while not stop_event.is_set():
        try:
            state = STATE.get_all() or {}
            second_player_state = STATE_SECOND_PLAYER.get_all() or {}
            # Pauza - bierz z tego samego odczytu
            if state.get("paused", False):
                main_player_data = state.get("main_player_data") or {}
                main_player_location_x = int(main_player_data.get("location_coord_x") or 0)
                main_player_location_y = int(main_player_data.get("location_coord_y") or 0)
                mouse_rel = main_player_data.get("mouse_relative_pos") or {}
                mouse_relative_pos_x = mouse_rel.get("x")
                mouse_relative_pos_y = mouse_rel.get("y")
                logger.info(f"PAUSED | Location: ({main_player_location_x},{main_player_location_y}), Mouse Rel Pos: ({mouse_relative_pos_x},{mouse_relative_pos_y})")
                stop_event.wait(0.5)
                continue

            main_player_loop(state=state)
            
            if TYPE_GAME == "two_players_in_party":
                second_player_loop(state=second_player_state)


        except Exception:
            logger.exception("action_loop error")

        stop_event.wait(interval)
