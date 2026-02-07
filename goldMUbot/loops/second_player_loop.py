import logging, time
from functions.state_singleton import STATE_SECOND_PLAYER
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

def second_player_loop(state):
            last_log_sig = None  # żeby nie spamować logów
            last_check_inventory = 0

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
            # time.sleep(1000)

            # --- Errory z helperami/okienkami ---
            popups_closer(player_info=second_player_name)

            # --- akcje wymagające izolacji od innych uruchamiane z UI ---
            send_message_via_ui(player_info=second_player_name)

            # --- akcje wymagające izolacji od innych cykliczne ---
            inv_interval_state = STATE_SECOND_PLAYER.get("inventory_interval", 60 * 5)  # default 5 minut, można nadpisać z state.json
            INVENTORY_INTERVAL = 60 * inv_interval_state
            now = time.time()
            if now - last_check_inventory >= INVENTORY_INTERVAL:
                check_inventory_zen(player_info=second_player_name)
                last_check_inventory = now

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

            if second_player_level == 1 and run_speedrun and not is_it_speedrun:
                logger.info("Player after reset, need to set speedrun mode ON")
                STATE_SECOND_PLAYER.update_dict("second_player_data", {"is_it_speedrun": True, "run_speedrun": False})  
            
            primary_max = 400
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