import logging, time
from functions.state_singleton import STATE, STATE_SECOND_PLAYER
from gameactions.attacks import attack_with_helper_on_spot
from gameactions.warp_to import warp_to
from functions.location_checks import is_at_position

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
    send_message=False,
):

    if player_name == "AleElfisko":
        state = STATE.get_all()
        player_data = state.get("main_player_data") or {}
    elif player_name == "AleToBot":
        state = STATE_SECOND_PLAYER.get_all()
        player_data = state.get("second_player_data") or {}

    desired_coord_x = map_spot.get("loc_x", 0)
    desired_coord_y = map_spot.get("loc_y", 0)

    if map_enabled and map_max > player_level >= map_min:
        if not is_at_position(
            player_data["location_coord_x"],
            player_data["location_coord_y"],
            desired_coord_x,
            desired_coord_y,
            tol=15,
        ):
            logger.info(
                f"Player not in {map_name} or spot {player_data['location_coord_x']},{player_data['location_coord_y']} desired: {desired_coord_x},{desired_coord_y}, warping..."
            )
            warp_to(
                player_info=player_name,
                desired_location=warp_to_location,
                actual_location=player_location_name,
                actual_location_coord_x=player_location_x,
            );time.sleep(3)

    if player_name == "AleElfisko":
        state = STATE.get_all()
        player_data = state.get("main_player_data") or {}
    elif player_name == "AleToBot":
        state = STATE_SECOND_PLAYER.get_all()
        player_data = state.get("second_player_data") or {}

    player_location_name = player_data.get("location_name") or "not_available"
    player_location_x = int(player_data.get("location_coord_x") or 0)

    if (
        map_enabled
        and map_max > player_level >= map_min
        and player_location_name == map_name
    ):
        logger.info(
            "Player in correct location for attack, checking map spot and attacking if set..."
        )
        if map_spot:
            attack_with_helper_on_spot(
                player_info=player_name,
                mouse_on_map_x=map_spot.get("x", 0),
                mouse_on_map_y=map_spot.get("y", 0),
                desired_coord_x=map_spot.get("loc_x", 0),
                desired_coord_y=map_spot.get("loc_y", 0),
                player_location_name=player_location_name,
                send_message=send_message,
                tolerance=map_spot.get("tolerance", 3),
            )
        else:
            logger.warning("No map_spot set in state, skipping attack on %s.", map_name)
