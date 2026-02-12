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
    name: f"{HOSTAPI_BASE_URL}{path}" for name, path in HOSTAPI["endpoints"].items()
}

HIDAPI = CONFIG["hidapi"]
HIDAPI_BASE_URL = f"http://{HIDAPI['ip']}:{HIDAPI['port']}"
HIDAPI_ENDPOINTS = {
    name: f"{HIDAPI_BASE_URL}{path}" for name, path in HIDAPI["endpoints"].items()
}

LOCALAPI = CONFIG["playerapi"]
LOCALAPI_BASE_URL = f"http://{LOCALAPI['ip']}:{LOCALAPI['port']}"
LOCALAPI_ENDPOINTS = {
    name: f"{LOCALAPI_BASE_URL}{path}" for name, path in LOCALAPI["endpoints"].items()
}

TYPE_GAME = CONFIG.get("type_game", "single")
CONFIG_PAUSE_AUTO_RESUME_MINUTES = CONFIG.get("pause_auto_resume_minutes", 5)
PAUSE_TIMEOUT_STATE_KEY = "pause_auto_resume_minutes"


def _as_float_minutes(value):
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _default_pause_minutes():
    default_minutes = _as_float_minutes(CONFIG_PAUSE_AUTO_RESUME_MINUTES)
    return (
        default_minutes if default_minutes is not None and default_minutes >= 0 else 0
    )


def _seed_pause_timeout_default():
    if STATE.get(PAUSE_TIMEOUT_STATE_KEY, None) is not None:
        return
    STATE.set(PAUSE_TIMEOUT_STATE_KEY, _default_pause_minutes())


def _pause_timeout_seconds_from_state():
    minutes_raw = STATE.get(PAUSE_TIMEOUT_STATE_KEY, CONFIG_PAUSE_AUTO_RESUME_MINUTES)
    minutes = _as_float_minutes(minutes_raw)
    if minutes is None:
        minutes = _as_float_minutes(CONFIG_PAUSE_AUTO_RESUME_MINUTES)
    if minutes and minutes > 0:
        return minutes * 60
    return None


_seed_pause_timeout_default()


def action_loop(stop_event, interval=1):
    logger.info("Action loop started")

    last_log_sig = None  # żeby nie spamować logów

    time.sleep(2)  # dajmy czas na zebranie pierwszych danych

    last_check_inventory = 0
    pause_started_at = None
    pause_auto_resume_seconds = _pause_timeout_seconds_from_state()
    pause_timeout_refresh_at = time.monotonic()

    while not stop_event.is_set():
        loop_monotonic = time.monotonic()
        if loop_monotonic - pause_timeout_refresh_at >= 5:
            pause_auto_resume_seconds = _pause_timeout_seconds_from_state()
            pause_timeout_refresh_at = loop_monotonic
        try:
            state = STATE.get_all() or {}
            second_player_state = STATE_SECOND_PLAYER.get_all() or {}
            # Pauza - bierz z tego samego odczytu
            if state.get("paused", False):
                if pause_started_at is None:
                    pause_started_at = loop_monotonic

                paused_duration = loop_monotonic - pause_started_at
                if (
                    pause_auto_resume_seconds
                    and paused_duration >= pause_auto_resume_seconds
                ):
                    STATE.set("paused", False)
                    STATE.set(PAUSE_TIMEOUT_STATE_KEY, _default_pause_minutes())
                    pause_auto_resume_seconds = _pause_timeout_seconds_from_state()
                    pause_timeout_refresh_at = loop_monotonic
                    pause_started_at = None
                    logger.warning(
                        "PAUSE TIMEOUT | Auto-resumed after %.1f min",
                        paused_duration / 60,
                    )
                else:
                    main_player_data = state.get("main_player_data") or {}
                    main_player_location_x = int(
                        main_player_data.get("location_coord_x") or 0
                    )
                    main_player_location_y = int(
                        main_player_data.get("location_coord_y") or 0
                    )
                    mouse_rel = main_player_data.get("mouse_relative_pos") or {}
                    mouse_relative_pos_x = mouse_rel.get("x")
                    mouse_relative_pos_y = mouse_rel.get("y")
                    if pause_auto_resume_seconds:
                        remaining_seconds = max(
                            pause_auto_resume_seconds - paused_duration, 0
                        )
                        remaining_label = (
                            f"Auto-resume in {remaining_seconds / 60:.1f} min"
                        )
                    else:
                        remaining_label = "Auto-resume disabled"

                    logger.info(
                        "PAUSED | Location: (%s,%s), Mouse Rel Pos: (%s,%s) | %s",
                        main_player_location_x,
                        main_player_location_y,
                        mouse_relative_pos_x,
                        mouse_relative_pos_y,
                        remaining_label,
                    )
                    stop_event.wait(0.5)
                    continue
            else:
                pause_started_at = None

            main_player_loop(state=state)

            if TYPE_GAME == "two_players_in_party":
                second_player_loop()

        except Exception:
            logger.exception("action_loop error")

        stop_event.wait(interval)
