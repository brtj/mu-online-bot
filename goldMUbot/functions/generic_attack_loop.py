import logging
from functions.state_singleton import STATE
from gameactions.attacks import attack_with_helper_on_spot
from gameactions.warp_to import warp_to

logger = logging.getLogger(__name__)

def generic_attack_on_spot(
    map_enabled,
    map_name, 
    map_max, 
    map_min,
    player_name,
    player_level,
    player_location_name,
    player_location_x,
    warp_to_location,
    map_spot,
    send_message=False):
  
  if map_enabled and map_max > player_level >= map_min and (player_location_name != map_name or player_location_name == "not_available"):
    logger.info(f"Player not in {map_name}, warping...")
    warp_to(
      player_info=player_name,
      desired_location=warp_to_location,
      actual_location=player_location_name,
      actual_location_coord_x=player_location_x,
    )

  if map_enabled and map_max > player_level >= map_min and player_location_name == map_name:
      logger.info("Player in correct location for attack, checking map spot and attacking if set...")
      if map_spot:
          attack_with_helper_on_spot(
              player_info=player_name,
              mouse_on_map_x=map_spot.get("x", 0),
              mouse_on_map_y=map_spot.get("y", 0),
              desired_coord_x=map_spot.get("loc_x", 0),
              desired_coord_y=map_spot.get("loc_y", 0),
              player_location_name=player_location_name,
              send_message=send_message,
              tolerance=map_spot.get("tolerance", 3)
          )
      else:
          logger.warning("No map_spot set in state, skipping attack on %s.", map_name)
