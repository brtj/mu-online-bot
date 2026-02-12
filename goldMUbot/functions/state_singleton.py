from pathlib import Path
from functions.state_store import JsonStateStore

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_PATH = BASE_DIR / "data" / "state.json"
STATE_SECOND_PLAYER_PATH = BASE_DIR / "data" / "state_second_player.json"

STATE = JsonStateStore(
    STATE_PATH, default={"snapshot": None, "main_player_data": {}, "players": {}}
)

STATE_SECOND_PLAYER = JsonStateStore(
    STATE_SECOND_PLAYER_PATH,
    default={"snapshot": None, "second_player_data": {}, "players": {}},
)
