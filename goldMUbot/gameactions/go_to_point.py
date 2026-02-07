from functions.host_api import activate_window, check_map_on
from functions.requests_functions import post
from functions.host_api import press_key
from functions import config_loader
from functions.location_checks import wait_until_at_position, get_location_state, is_at_position
from gameactions.helper_attack import click_on_helper_to_turn_off

from functions.state_singleton import STATE

import time
import logging
from logger_config import setup_logging

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


def go_to_point_and_wait(mouse_x, mouse_y, target_loc_x, target_loc_y, print_txt="...", player_info="", tol=10, timeout=80, click_interval=3, poll_interval=2):
    logger.info(
        f"go_to_point → mouse=({mouse_x},{mouse_y}) "
        f"target_loc=({target_loc_x},{target_loc_y}) {print_txt}"
    )

    activate_window(player_info=player_info)

    press_key_payload = {"keycode": 30, "press_time": 1} #press number 1
    press_key(payload=press_key_payload)

    state = STATE.get_all()
    main_player_data = state.get("main_player_data") or {}

    if main_player_data["helper_status"] == "Running":
        logger.info("Helper is Running, need to turn it off")
        click_on_helper_to_turn_off(player_info=player_info)

    time.sleep(0.25)

    if check_map_on(player_info=player_info) == "MAP OFF":
        logger.info("Map is OFF need to turn it ON")
        press_key_payload = {"keycode": 43, "press_time": 1} #press tab
        press_key(payload=press_key_payload)
        time.sleep(0.3)

    start = time.time()
    attempt = 0

    while True:
        attempt += 1

        if check_map_on(player_info=player_info) == "MAP OFF":
            logger.info("Map is OFF need to turn it ON")
            press_key_payload = {"keycode": 43, "press_time": 1} #press tab
            press_key(payload=press_key_payload)
            time.sleep(0.3)

        # 1️⃣ NAJAZD
        post(HOSTAPI_ENDPOINTS["mouse_goto_xy_relative"], { 
            "title": f"{player_info}",
            "target_x": mouse_x,
            "target_y": mouse_y,
            "require_inside": False
        })

        time.sleep(0.25)

        # 2️⃣ KLIK
        post(HIDAPI_ENDPOINTS["mouse_click"], {
            "button": "left",
            "action": "click",
            "hold_time": 0.30
        })

        logger.info(f"go_to_point: click attempt #{attempt}")

        # 3️⃣ CZEKAJ AŻ DOJŚCIE ZOSTANIE POTWIERDZONE
        reached = wait_until_at_position(
            tx=target_loc_x,
            ty=target_loc_y,
            tol=tol,
            timeout=poll_interval * 3,  # krótki wait po każdym kliku
            interval=poll_interval,
            player_info=player_info,
        )

        if reached:
            logger.info(
                f"go_to_point: reached target "
                f"({target_loc_x},{target_loc_y}) after {attempt} clicks"
            )
            break

        # 4️⃣ TIMEOUT GLOBALNY
        if time.time() - start >= timeout:
            logger.warning(
                f"go_to_point: TIMEOUT after {attempt} attempts "
                f"target=({target_loc_x},{target_loc_y})"
            )
            break

        time.sleep(click_interval)

    # MAP OFF
    if check_map_on(player_info=player_info) == "MAP ON":
        press_key_payload = {"keycode": 43, "press_time": 1} #press tab
        press_key(payload=press_key_payload)
        time.sleep(0.3)

    # FINAL STATE
    st = get_location_state(player_info=player_info)
    ok = (
        st.get("ok")
        and is_at_position(
            st["location_coord_x"],
            st["location_coord_y"],
            target_loc_x,
            target_loc_y,
            tol=tol,
        )
    )

    return {
        "ok": bool(ok),
        "attempts": attempt,
        "state": st,
        "tx": target_loc_x,
        "ty": target_loc_y,
    }