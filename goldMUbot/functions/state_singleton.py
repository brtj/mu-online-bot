from pathlib import Path
from functions.state_store import JsonStateStore

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_PATH = BASE_DIR / "data" / "state.json"

STATE = JsonStateStore(
    STATE_PATH,
    default={"snapshot": None, "player_data": {}, "players": {}}
)