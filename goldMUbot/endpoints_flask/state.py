from flask import Blueprint, jsonify, request
from functions import config_loader
from functions.state_singleton import STATE

state_bp = Blueprint("state", __name__)

CONFIG = config_loader.load_config()
DEFAULT_PAUSE_TIMEOUT_MINUTES = CONFIG.get("pause_auto_resume_minutes", 5)
PAUSE_TIMEOUT_STATE_KEY = "pause_auto_resume_minutes"


def _as_float_minutes(value, allow_zero=True):
    if isinstance(value, (int, float)):
        minutes = float(value)
    else:
        try:
            minutes = float(value)
        except (TypeError, ValueError):
            return None
    if minutes < 0:
        return None
    if not allow_zero and minutes == 0:
        return None
    return minutes


def _current_pause_timeout_minutes():
    stored = _as_float_minutes(STATE.get(PAUSE_TIMEOUT_STATE_KEY))
    if stored is not None:
        return stored
    fallback = _as_float_minutes(DEFAULT_PAUSE_TIMEOUT_MINUTES)
    if fallback is not None:
        return fallback
    return 0.0


@state_bp.get("/api/state")
def api_state():
    snap = STATE.get_snapshot()
    if snap is None:
        snap = STATE.get("snapshot", {})
    return jsonify(snap or {})


@state_bp.get("/api/main_player_data")
def api_main_player_data():
    return jsonify(STATE.get("main_player_data", {}) or {})


@state_bp.get("/api/pause")
def api_pause_status():
    """
    Get current pause status
    """
    paused = STATE.get("paused", False)
    return jsonify({"paused": bool(paused)})


@state_bp.post("/api/pause")
def api_pause_set():
    """
    Set pause status: { "paused": true|false }
    """
    data = request.get_json(silent=True) or {}

    if "paused" not in data:
        return jsonify({"error": "missing 'paused' field"}), 400

    paused = bool(data["paused"])
    STATE.set("paused", paused)

    return jsonify({"paused": paused})


@state_bp.get("/api/pause-timeout")
def api_pause_timeout_get():
    minutes = round(_current_pause_timeout_minutes(), 2)
    enabled = minutes > 0
    seconds = minutes * 60 if enabled else 0
    return jsonify(
        {
            "minutes": minutes,
            "seconds": seconds,
            "enabled": enabled,
        }
    )


@state_bp.post("/api/pause-timeout")
def api_pause_timeout_set():
    data = request.get_json(silent=True) or {}
    if "minutes" not in data:
        return jsonify({"error": "missing 'minutes' field"}), 400

    minutes = _as_float_minutes(data.get("minutes"))
    if minutes is None:
        return jsonify({"error": "minutes must be a number >= 0"}), 400

    minutes = round(minutes, 2)
    stored_value = minutes if minutes > 0 else 0
    STATE.set(PAUSE_TIMEOUT_STATE_KEY, stored_value)

    enabled = stored_value > 0
    seconds = stored_value * 60 if enabled else 0
    return jsonify(
        {
            "minutes": stored_value,
            "seconds": seconds,
            "enabled": enabled,
        }
    )
