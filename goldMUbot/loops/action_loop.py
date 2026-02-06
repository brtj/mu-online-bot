import logging, time
from functions.state_singleton import STATE
from functions import config_loader
from functions.generic_attack_loop import generic_attack_on_spot

from gameactions.resets import elf_reset
from gameactions.addstats import main_player_add_stats
from gameactions.attacks import attack_no_helper_on_spot, attack_with_helper_on_spot
from gameactions.warp_to import warp_to
from gameactions.pop_ups import popups_closer
from gameactions.send_message_ui import send_message_via_ui
from gameactions.check_zen import check_inventory_zen
from gameactions.inventory_actions import jewels_to_bank


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

def action_loop(stop_event, interval=1):
    logger.info("Action loop started")

    last_log_sig = None  # żeby nie spamować logów

    time.sleep(2)  # dajmy czas na zebranie pierwszych danych

    last_check_inventory = 0

    while not stop_event.is_set():
        try:
            state = STATE.get_all() or {}

            # Pauza - bierz z tego samego odczytu
            if state.get("paused", False):
                player_data = state.get("player_data") or {}
                main_player_location_x = int(player_data.get("location_coord_x") or 0)
                main_player_location_y = int(player_data.get("location_coord_y") or 0)
                mouse_rel = player_data.get("mouse_relative_pos") or {}
                mouse_relative_pos_x = mouse_rel.get("x")
                mouse_relative_pos_y = mouse_rel.get("y")
                logger.info(f"PAUSED | Location: ({main_player_location_x},{main_player_location_y}), Mouse Rel Pos: ({mouse_relative_pos_x},{mouse_relative_pos_y})")
                stop_event.wait(0.5)
                continue

            player_data = state.get("player_data") or {}

            # map level limits control (from state.json)
            map_level_limits = player_data.get("map_level_limits", {}) or {}
            # always read common map cfgs
            devias_cfg = map_level_limits.get("Devias") or {}
            devias_enabled = ("enabled" in devias_cfg) and bool(devias_cfg.get("enabled"))
            devias_min = int(devias_cfg.get("min") or 0)
            devias_max = int(devias_cfg.get("max") or 0)

            atlans_cfg = map_level_limits.get("Atlans") or {}
            atlans_enabled = ("enabled" in atlans_cfg) and bool(atlans_cfg.get("enabled"))
            atlans_min = int(atlans_cfg.get("min") or 0)
            atlans_max = int(atlans_cfg.get("max") or 0)

            icarus2_cfg = map_level_limits.get("Icarus2") or {}
            icarus2_enabled = ("enabled" in icarus2_cfg) and bool(icarus2_cfg.get("enabled"))
            icarus2_min = int(icarus2_cfg.get("min") or 0)
            icarus2_max = int(icarus2_cfg.get("max") or 0)

            aida_cfg = map_level_limits.get("Aida") or {}
            aida_enabled = ("enabled" in aida_cfg) and bool(aida_cfg.get("enabled"))
            aida_min = int(aida_cfg.get("min") or 0)
            aida_max = int(aida_cfg.get("max") or 0)

            lacleon_cfg = map_level_limits.get("LaCleon") or {}
            lacleon_enabled = ("enabled" in lacleon_cfg) and bool(lacleon_cfg.get("enabled"))
            lacleon_min = int(lacleon_cfg.get("min") or 0)
            lacleon_max = int(lacleon_cfg.get("max") or 0)

            # Noria / Lorencia selection depends on character type from config
            cfg = config_loader.load_config()
            char_type = cfg.get("mainplayer", {}).get("character_type", "")

            noria_cfg = map_level_limits.get("Noria") or {}
            noria_enabled = ("enabled" in noria_cfg) and bool(noria_cfg.get("enabled"))

            lorencia_cfg = map_level_limits.get("Lorencia") or {}
            lorencia_enabled = ("enabled" in lorencia_cfg) and bool(lorencia_cfg.get("enabled"))

            # primary map for low levels: Noria for Elves, Lorencia otherwise
            if str(char_type).lower() == "elf":
                primary_map_name = "Noria"
                primary_cfg = noria_cfg
                primary_enabled = noria_enabled
            else:
                primary_map_name = "Lorencia"
                primary_cfg = lorencia_cfg
                primary_enabled = lorencia_enabled

            # derive primary level limits
            primary_min = int(primary_cfg.get("min") or 0)
            primary_max = int(primary_cfg.get("max") or 0)

            # Jeśli jeszcze nie ma danych - nie rób nic
            main_player_name = player_data.get("player")
            if not main_player_name:
                logger.debug("action_loop: player_data not ready yet: %s", player_data)
                stop_event.wait(0.5)
                continue

            #speedrun 
            run_speedrun = bool(player_data.get("run_speedrun", False))
            is_it_speedrun = bool(player_data.get("is_it_speedrun", False))

            # Bezpieczne odczyty pól
            main_player_level = int(player_data.get("level") or 0)
            main_player_reset = int(player_data.get("reset") or 0)
            main_player_location_name = player_data.get("location_name") or "not_available"
            main_player_location_x = int(player_data.get("location_coord_x") or 0)
            main_player_location_y = int(player_data.get("location_coord_y") or 0)

            mouse_rel = player_data.get("mouse_relative_pos") or {}
            mouse_relative_pos_x = mouse_rel.get("x")
            mouse_relative_pos_y = mouse_rel.get("y")

            stats_added = bool(player_data.get("stats_added", False))

            # Loguj tylko gdy coś się zmieni (żeby nie spamować co sekundę)
            sig = (
                main_player_name,
                main_player_level,
                main_player_location_name,
                main_player_location_x,
                main_player_location_y,
                mouse_relative_pos_x,
                mouse_relative_pos_y,
            )
            if sig != last_log_sig:
                logger.info(
                    "Player=%s | lvl=%s | Loc=%s (%s,%s) | mouse rel x=%s y=%s",
                    main_player_name,
                    main_player_level,
                    main_player_location_name,
                    main_player_location_x,
                    main_player_location_y,
                    mouse_relative_pos_x,
                    mouse_relative_pos_y,
                )
                last_log_sig = sig

            # --- Errory z helperami/okienkami ---
            # popups_closer(player_info=main_player_name)

            # --- akcje wymagające izolacji od innych uruchamiane z UI ---
            send_message_via_ui(player_info=main_player_name)

            jewels_to_bank(player_info=main_player_name)
            logger.info("KONIEC --------------")
            time.sleep(30)

            # --- akcje wymagające izolacji od innych cykliczne ---
            inv_interval_state = STATE.get("inventory_interval", 60 * 5)  # default 5 minut, można nadpisać z state.json
            INVENTORY_INTERVAL = 60 * inv_interval_state
            now = time.time()
            if now - last_check_inventory >= INVENTORY_INTERVAL:
                check_inventory_zen(player_info=main_player_name)
                last_check_inventory = now

            # --- Twoja logika akcji ---

            if main_player_level == 400:
                logger.info("Need to do reset")
                STATE.update_dict("player_data", {"stats_added": False})
                elf_reset(player_info=main_player_name)

            if main_player_level == 1 and not stats_added:
                logger.info("Player after reset, need to adjust character")
                STATE.update_dict("player_data", {"stats_added": True})
                main_player_add_stats(player_info=main_player_name, main_player_reset=main_player_reset)

            if main_player_level == 1 and run_speedrun and not is_it_speedrun:
                logger.info("Player after reset, need to set speedrun mode ON")
                STATE.update_dict("player_data", {"is_it_speedrun": True, "run_speedrun": False})  
            
            #"is_it_speedrun": false,
            #"run_speedrun": false,

            if primary_enabled and primary_max >= main_player_level >= primary_min:
                logger.info("Exping on %s (min=%s max=%s)...", primary_map_name, primary_min, primary_max)
                delta = [(620, 305), (620, 365), (620, 430)]
                attack_no_helper_on_spot(
                    player_info=main_player_name,
                    level_max=primary_max,
                    location_coord_x=main_player_location_x,
                    location_coord_y=main_player_location_y,
                    desired_coord_x=237,
                    desired_coord_y=152,
                    mouse_on_map_x=614,
                    mouse_on_map_y=257,
                    delta=delta,
                )

            if devias_enabled and devias_max >= main_player_level >= devias_min and (main_player_location_name != "Devias" or main_player_location_name == "not_available"):
                warp_to(
                    player_info=main_player_name,
                    desired_location="Devias",
                    actual_location=main_player_location_name,
                    actual_location_coord_x=main_player_location_x,
                )

            if devias_enabled and devias_max >= main_player_level >= devias_min and main_player_location_name == "Devias":
                logger.info("Exping on %s (min=%s max=%s)...", "Devias", devias_min, devias_max)
                delta = [(580, 210), (580, 400), (580, 500)]
                attack_no_helper_on_spot(
                    player_info=main_player_name,
                    level_max=devias_max,
                    location_coord_x=main_player_location_x,
                    location_coord_y=main_player_location_y,
                    desired_coord_x=5,
                    desired_coord_y=179,
                    mouse_on_map_x=163,
                    mouse_on_map_y=200,
                    delta=delta,
                )

            atlans_spot = (player_data.get("map_spots") or {}).get("atlans_map_spots")
            generic_attack_on_spot(
                atlans_enabled, 
                "Atlans", # map_name
                atlans_max, # lvl_max
                atlans_min, # lvl_min
                main_player_name,
                main_player_level,
                main_player_location_name,
                main_player_location_x,
                "atlans", #warp string (ex atlans2, aida2 etc)
                atlans_spot # map_spot data
            )

            icarus2_spot = (player_data.get("map_spots") or {}).get("icarus2_map_spots")
            generic_attack_on_spot(
                icarus2_enabled, 
                "Icarus", # map_name
                icarus2_max, # lvl_max
                icarus2_min, # lvl_min
                main_player_name,
                main_player_level,
                main_player_location_name,
                main_player_location_x,
                "Icarus2", #warp string (ex atlans2, aida2 etc)
                icarus2_spot # map_spot data
            )

            aida_spot = (player_data.get("map_spots") or {}).get("aida_map_spots")
            generic_attack_on_spot(
                aida_enabled, 
                "Aida", # map_name
                aida_max, # lvl_max
                aida_min, # lvl_min
                main_player_name,
                main_player_level,
                main_player_location_name,
                main_player_location_x,
                "Aida2", #warp string (ex atlans2, aida2 etc)
                aida_spot # map_spot data
            )

            lacleon_spot = (player_data.get("map_spots") or {}).get("lacleon_map_spots")
            generic_attack_on_spot(
                lacleon_enabled, 
                "LaCleon", # map_name
                lacleon_max, # lvl_max
                lacleon_min, # lvl_min
                main_player_name,
                main_player_level,
                main_player_location_name,
                main_player_location_x,
                "raklion", #warp string (ex atlans2, aida2 etc)
                lacleon_spot # map_spot data
            )

        except Exception:
            logger.exception("action_loop error")

        stop_event.wait(interval)
