import logging,time
from functions.state_singleton import STATE
from gameactions.attacks import attack_with_helper_on_spot
from gameactions.warp_to import warp_to
from functions.host_api import send_message, activate_window

logger = logging.getLogger(__name__)

def generic_attack_on_spot(
    map_enabled,
    map_name, 
    map_max, 
    map_min,
    main_player_name,
    main_player_level,
    main_player_location_name,
    main_player_location_x,
    warp_to_location,
    map_spot):

  if map_enabled and map_max > main_player_level >= map_min and (main_player_location_name != map_name or main_player_location_name == "not_available"):
    warp_to(
      player_info=main_player_name,
      desired_location=warp_to_location,
      actual_location=main_player_location_name,
      actual_location_coord_x=main_player_location_x,
    )

  if map_enabled and map_max > main_player_level >= map_min and main_player_location_name == map_name:
      if map_spot:
          attack_with_helper_on_spot(
              player_info=main_player_name,
              mouse_on_map_x=map_spot.get("x", 0),
              mouse_on_map_y=map_spot.get("y", 0),
              desired_coord_x=map_spot.get("loc_x", 0),
              desired_coord_y=map_spot.get("loc_y", 0),
              main_player_location_name=main_player_location_name,
              map_max=map_max
          )


      else:
          logger.warning("No map_spot set in state, skipping attack on %s.", map_name)
