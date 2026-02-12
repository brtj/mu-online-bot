from flask import Blueprint, jsonify, request
from functions.state_singleton import STATE, STATE_SECOND_PLAYER

map_levels_bp = Blueprint("map_levels", __name__)


MAP_LEVEL_DEFAULTS = {
    "Lorencia": {"min": 1, "max": 50, "enabled": True},
    "Noria": {"min": 1, "max": 50, "enabled": True},
    "Devias": {"min": 50, "max": 80, "enabled": True},
    "Atlans": {"min": 80, "max": 210, "enabled": True},
    "Aida": {"min": 210, "max": 400, "enabled": True},
    "Karutan2": {"min": 310, "max": 400, "enabled": True},
    "Icarus2": {"min": 180, "max": 400, "enabled": False},
    "LaCleon": {"min": 325, "max": 400, "enabled": False},
}


def merge_with_defaults(custom_limits=None):
    custom_limits = custom_limits or {}
    merged = {}
    for map_name, defaults in MAP_LEVEL_DEFAULTS.items():
        current = custom_limits.get(map_name) or {}
        merged[map_name] = {
            "min": current.get("min", defaults["min"]),
            "max": current.get("max", defaults["max"]),
            "enabled": current.get("enabled", defaults["enabled"]),
        }

    # keep any custom maps that are not in defaults
    for map_name, cfg in custom_limits.items():
        if map_name not in merged:
            merged[map_name] = cfg
    return merged


def persist_map_level_limits(limits: dict) -> dict:
    merged = merge_with_defaults(limits)
    STATE.update_dict("main_player_data", {"map_level_limits": merged})

    STATE_SECOND_PLAYER.update_dict("second_player_data", {"map_level_limits": merged})

    return merged


@map_levels_bp.get("/api/map-level-limits")
def api_get_map_level_limits():
    pd = STATE.get("main_player_data", {}) or {}
    current = pd.get("map_level_limits", {}) or {}
    return jsonify(merge_with_defaults(current))


@map_levels_bp.get("/api/map-level-minimums")
def api_get_map_level_minimums():
    return jsonify({name: cfg["min"] for name, cfg in MAP_LEVEL_DEFAULTS.items()})


@map_levels_bp.post("/api/map-level-limits")
def api_set_map_level_limits():
    data = request.get_json(silent=True) or {}

    # allow two formats:
    # 1) { "map_level_limits": { ... } }
    # 2) { ... }  (direct map)
    limits = data.get("map_level_limits", data)

    if not isinstance(limits, dict):
        return jsonify(
            {"error": "payload must be a dict (map -> {min,max,enabled})"}
        ), 400

    # minimal validation
    allowed_maps = set(MAP_LEVEL_DEFAULTS.keys())
    for map_name, cfg in limits.items():
        if not isinstance(map_name, str):
            return jsonify({"error": "map name must be a string"}), 400
        if map_name not in allowed_maps:
            return jsonify({"error": f"Unknown map name '{map_name}'"}), 400
        if not isinstance(cfg, dict):
            return jsonify({"error": f"value for '{map_name}' must be an object"}), 400

        if (
            "min" in cfg
            and cfg["min"] is not None
            and not isinstance(cfg["min"], (int, float))
        ):
            return jsonify({"error": f"'{map_name}.min' must be a number"}), 400
        if (
            "max" in cfg
            and cfg["max"] is not None
            and not isinstance(cfg["max"], (int, float))
        ):
            return jsonify({"error": f"'{map_name}.max' must be a number"}), 400
        if (
            "enabled" in cfg
            and cfg["enabled"] is not None
            and not isinstance(cfg["enabled"], bool)
        ):
            return jsonify({"error": f"'{map_name}.enabled' must be true/false"}), 400

    merged_limits = persist_map_level_limits(limits)

    return jsonify({"ok": True, "map_level_limits": merged_limits})
