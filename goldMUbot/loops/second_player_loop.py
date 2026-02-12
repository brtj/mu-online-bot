import logging, time
from functions.state_singleton import STATE, STATE_SECOND_PLAYER
from functions import config_loader
from functions.generic_attack_loop import generic_attack_on_spot

from gameactions.resets import dk_reset, elf_reset
from gameactions.addstats import second_player_add_stats
from gameactions.attacks import attack_no_helper_on_spot, attack_with_helper_on_spot
from gameactions.warp_to import warp_to
from gameactions.pop_ups import popups_closer
from gameactions.send_message_ui import send_message_via_ui
from gameactions.check_zen import check_inventory_zen
from gameactions.inventory_actions import jewels_to_bank
from gameactions.chaos_machine_bc_invite import chaos_machine_bc_invite
from gameactions.party import check_if_its_in_party
from functions.host_api import switch_window
from functions.location_checks import is_at_position
from gameactions.helper_attack import click_on_helper

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
LAST_CHECK_INVENTORY = 0
            
def second_player_loop():
            last_log_sig = None  # żeby nie spamować logów
            global LAST_CHECK_INVENTORY

            main_player_data = STATE.get("main_player_data") or {}
            main_player_name = CONFIG["mainplayer"]["nickname"]

            second_player_data = STATE_SECOND_PLAYER.get("second_player_data") or {}
            second_player_name = CONFIG["secondaccount"]["nickname"]

            # map level limits control (from STATE_SECOND_PLAYER.json)
            map_level_limits = second_player_data.get("map_level_limits", {}) or {}
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

            karutan2_cfg = map_level_limits.get("Karutan2") or {}
            karutan2_enabled = ("enabled" in karutan2_cfg) and bool(karutan2_cfg.get("enabled"))
            karutan2_min = int(karutan2_cfg.get("min") or 0)
            karutan2_max = int(karutan2_cfg.get("max") or 0)

            lacleon_cfg = map_level_limits.get("LaCleon") or {}
            lacleon_enabled = ("enabled" in lacleon_cfg) and bool(lacleon_cfg.get("enabled"))
            lacleon_min = int(lacleon_cfg.get("min") or 0)
            lacleon_max = int(lacleon_cfg.get("max") or 0)

            # Noria / Lorencia selection depends on character type from config
            cfg = config_loader.load_config()
            char_type = cfg.get("secondaccount", {}).get("character_type", "")

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

            #speedrun 
            run_speedrun = bool(second_player_data.get("run_speedrun", False))
            is_it_speedrun = bool(second_player_data.get("is_it_speedrun", False))

            # Bezpieczne odczyty pól
            second_player_level = int(second_player_data.get("level") or 0)
            second_player_reset = int(second_player_data.get("reset") or 0)
            second_player_location_name = second_player_data.get("location_name") or "not_available"
            second_player_location_x = int(second_player_data.get("location_coord_x") or 0)
            second_player_location_y = int(second_player_data.get("location_coord_y") or 0)

            mouse_rel = second_player_data.get("mouse_relative_pos") or {}
            mouse_relative_pos_x = mouse_rel.get("x")
            mouse_relative_pos_y = mouse_rel.get("y")

            stats_added = bool(second_player_data.get("stats_added", False))

            # Loguj tylko gdy coś się zmieni (żeby nie spamować co sekundę)
            sig = (
                second_player_name,
                second_player_level,
                second_player_location_name,
                second_player_location_x,
                second_player_location_y,
                mouse_relative_pos_x,
                mouse_relative_pos_y,
            )
            if sig != last_log_sig:
                logger.info(
                    "Player=%s | lvl=%s | Loc=%s (%s,%s) | mouse rel x=%s y=%s",
                    second_player_name,
                    second_player_level,
                    second_player_location_name,
                    second_player_location_x,
                    second_player_location_y,
                    mouse_relative_pos_x,
                    mouse_relative_pos_y,
                )
                last_log_sig = sig

            # --- miejsce na akcje do protypowania ---
            # chaos_machine_bc_invite(player_info=second_player_name)
            # check_if_its_in_party(player_info=second_player_name)
            # time.sleep(1000)

            # --- Errory z helperami/okienkami ---
            popups_closer(player_info=second_player_name)

            # --- Twoja logika akcji ---

            if second_player_level == 400:
                logger.info("Need to do reset")
                STATE_SECOND_PLAYER.update_dict("second_player_data", {"stats_added": False, "is_it_speedrun": False, "run_speedrun": False})
                jewels_to_bank(player_info=second_player_name)
                reset_count = second_player_reset + 1
                dk_reset(player_info=second_player_name, reset_count=reset_count)

            if second_player_level == 1 and not stats_added:
                logger.info("Player after reset, need to adjust character")
                STATE_SECOND_PLAYER.update_dict("second_player_data", {"stats_added": True})
                second_player_add_stats(player_info=second_player_name, second_player_reset=second_player_reset)
                check_if_its_in_party(player_info=second_player_name)

            if second_player_level == 1 and run_speedrun and not is_it_speedrun:
                logger.info("Player after reset, need to set speedrun mode ON")
                STATE_SECOND_PLAYER.update_dict("second_player_data", {"is_it_speedrun": True, "run_speedrun": False})  
            
            primary_max = 50
            primary_min = 1
            if primary_enabled and primary_max >= second_player_level >= primary_min:
                logger.info("Exping on %s (min=%s max=%s)...", primary_map_name, primary_min, primary_max)
                delta = [(620, 290), (620, 365)]
                attack_no_helper_on_spot(
                    player_info=second_player_name,
                    level_max=primary_max,
                    location_coord_x=second_player_location_x,
                    location_coord_y=second_player_location_y,
                    desired_coord_x=152,
                    desired_coord_y=237,
                    mouse_on_map_x=462,
                    mouse_on_map_y=81,
                    delta=delta,
                )

            devias_min = 50
            devias_max = 80
            if devias_enabled and devias_max >= second_player_level >= devias_min and (second_player_location_name != "Devias" or second_player_location_name == "not_available"):
                warp_to(
                    player_info=second_player_name,
                    desired_location="Devias",
                    actual_location=second_player_location_name,
                    actual_location_coord_x=second_player_location_x,
                )

            if devias_enabled and devias_max >= second_player_level >= devias_min and second_player_location_name == "Devias":
                logger.info("Exping on %s (min=%s max=%s)...", "Devias", devias_min, devias_max)
                delta = [(580, 210), (580, 400), (580, 500)]
                attack_no_helper_on_spot(
                    player_info=second_player_name,
                    level_max=devias_max,
                    location_coord_x=second_player_location_x,
                    location_coord_y=second_player_location_y,
                    desired_coord_x=5,
                    desired_coord_y=179,
                    mouse_on_map_x=163,
                    mouse_on_map_y=200,
                    delta=delta,
                )

            #atlans1 manual
            atlans_min = 80
            atlans_max = 120
            atlans_spot_manual = {'id': 'test', 'loc_x': 23, 'loc_y': 123, 'map': 'Atlans2', 'moobs': 'Vepar 45 lvl', 'tolerance': 9, 'x': 199, 'y': 315}
            generic_attack_on_spot(
                map_enabled=atlans_enabled, 
                map_name="Atlans", # map_name
                map_max=atlans_max, # lvl_max
                map_min=atlans_min, # lvl_min
                player_name=second_player_name,
                player_level=second_player_level,
                player_location_name=second_player_location_name,
                player_location_x=second_player_location_x,
                warp_to_location="atlans", #warp string (ex atlans2, aida2 etc)
                map_spot=atlans_spot_manual, # map_spot data
                send_message=False
            )

            #atlans2
            atlans_spot = (second_player_data.get("map_spots") or {}).get("atlans_map_spots")
            logger.info(atlans_spot)
            atlans_min = 120
            atlans_max = 210
            if atlans_enabled and atlans_max >= second_player_level >= atlans_min and (second_player_location_name == "Atlans" or second_player_location_name == "not_available"):
                desired_coord_x=atlans_spot.get("loc_x", 0)
                desired_coord_y=atlans_spot.get("loc_y", 0)
                logger.info(desired_coord_x)
                logger.info(desired_coord_y)
                if not is_at_position(second_player_location_x, second_player_location_y, desired_coord_x, desired_coord_y, tol=20):
                    warp_to(
                        player_info=second_player_name,
                        desired_location="Atlans2",
                        actual_location=second_player_location_name,
                        actual_location_coord_x=second_player_location_x,
                    )

            generic_attack_on_spot(
                map_enabled=atlans_enabled, 
                map_name="Atlans", # map_name
                map_max=atlans_max, # lvl_max
                map_min=120, # lvl_min
                player_name=second_player_name,
                player_level=second_player_level,
                player_location_name=second_player_location_name,
                player_location_x=second_player_location_x,
                warp_to_location="atlans2", #warp string (ex atlans2, aida2 etc)
                map_spot=atlans_spot,
                send_message=False
            )

            # icarus2 -----------------------------------------
            icarus2_spot = (main_player_data.get("map_spots") or {}).get("icarus2_map_spots")
            generic_attack_on_spot(
                map_enabled=icarus2_enabled, 
                map_name="Icarus", # map_name
                map_max=icarus2_max, # lvl_max
                map_min=icarus2_min, # lvl_min
                player_name=second_player_name,
                player_level=second_player_level,
                player_location_name=second_player_location_name,
                player_location_x=second_player_location_x,
                warp_to_location="Icarus2", #warp string (ex atlans2, aida2 etc)
                map_spot=icarus2_spot, # map_spot data
                send_message=False
            )

            # aida2 -----------------------------------------
            aida_spot = (main_player_data.get("map_spots") or {}).get("aida_map_spots")
            generic_attack_on_spot(
                map_enabled=aida_enabled, 
                map_name="Aida", # map_name
                map_max=aida_max, # lvl_max
                map_min=aida_min, # lvl_min
                player_name=second_player_name,
                player_level=second_player_level,
                player_location_name=second_player_location_name,
                player_location_x=second_player_location_x,
                warp_to_location="Aida2", #warp string (ex atlans2, aida2 etc)
                map_spot=aida_spot, # map_spot data
                send_message=False
            )

            # karutan2 -----------------------------------------
            karutan2_spot = (main_player_data.get("map_spots") or {}).get("karutan2_map_spots")
            generic_attack_on_spot(
                map_enabled=karutan2_enabled, 
                map_name="Karutan", # map_name
                map_max=karutan2_max, # lvl_max
                map_min=karutan2_min, # lvl_min
                player_name=second_player_name,
                player_level=second_player_level,
                player_location_name=second_player_location_name,
                player_location_x=second_player_location_x,
                warp_to_location="karutan2", #warp string (ex atlans2, aida2 etc)
                map_spot=karutan2_spot, # map_spot data
                send_message=False
            )


            # raklion ------------------------------------------
            lacleon_spot = (main_player_data.get("map_spots") or {}).get("lacleon_map_spots")
            generic_attack_on_spot(
                map_enabled=lacleon_enabled, 
                map_name="LaCleon", # map_name
                map_max=lacleon_max, # lvl_max
                map_min=lacleon_min, # lvl_min
                player_name=second_player_name,
                player_level=second_player_level,
                player_location_name=second_player_location_name,
                player_location_x=second_player_location_x,
                warp_to_location="raklion", #warp string (ex atlans2, aida2 etc)
                map_spot=lacleon_spot, # map_spot data
                send_message=False
            )

            # player_level = main_player_data.get("level", 0)
            # player_location_name = main_player_data.get("location_name", "not_available")
            # logger.info("Main player level: %s, location: %s", player_level, player_location_name)
            # if player_level >= 210 and player_location_name == "Aida" and second_player_level >= 210:

            #     player_spot = (main_player_data.get("map_spots") or {}).get("aida_map_spots")
            #     aida_min = 210
            #     aida_max = 400
            #     click_on_helper("AleElfisko")
            #     generic_attack_on_spot(
            #         map_enabled=True, 
            #         map_name="Aida", # map_name
            #         map_max=aida_max, # lvl_max
            #         map_min=aida_min, # lvl_min
            #         player_name=second_player_name,
            #         player_level=second_player_level,
            #         player_location_name=second_player_location_name,
            #         player_location_x=second_player_location_x,
            #         warp_to_location="aida2", 
            #         map_spot=player_spot,
            #         send_message=False
            #     )
            # else:
            #     logger.info("Im going to Atlans2 safe spot to wait for main player to reach requirements for Aida")
            #     #atlans2 as a workaround safe spot while waiting for main player to reach requirements for Aida
            #     atlans_spot = (second_player_data.get("map_spots") or {}).get("atlans_map_spots")
            #     logger.info(atlans_spot)
            #     atlans_min = 120
            #     atlans_max = 400

            #     generic_attack_on_spot(
            #         map_enabled=atlans_enabled, 
            #         map_name="Atlans", # map_name
            #         map_max=atlans_max, # lvl_max
            #         map_min=atlans_min, # lvl_min
            #         player_name=second_player_name,
            #         player_level=second_player_level,
            #         player_location_name=second_player_location_name,
            #         player_location_x=second_player_location_x,
            #         warp_to_location="atlans2", #warp string (ex atlans2, aida2 etc)
            #         map_spot=atlans_spot,
            #         send_message=False
            #     )

            # --- akcje wymagające izolacji od innych uruchamiane z UI ---
            send_message_via_ui(player_info=second_player_name)

            # --- akcje wymagające izolacji od innych cykliczne ---
            inv_interval_state = STATE.get("inventory_interval", 60 * 5)  # default 5 minut, można nadpisać z state.json
            INVENTORY_INTERVAL = 60 * inv_interval_state
            now = time.time()
            if now - LAST_CHECK_INVENTORY >= INVENTORY_INTERVAL:
                check_inventory_zen(player_info=main_player_name)
                LAST_CHECK_INVENTORY = now