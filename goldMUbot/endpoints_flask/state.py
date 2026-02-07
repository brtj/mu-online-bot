from flask import Blueprint, jsonify, request
from functions.state_singleton import STATE

state_bp = Blueprint("state", __name__)

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