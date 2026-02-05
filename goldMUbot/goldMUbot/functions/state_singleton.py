from functions.state_store import JsonStateStore

STATE = JsonStateStore(
    "data/state.json",
    default={"snapshot": None, "player_data": {}, "players": {}}
)