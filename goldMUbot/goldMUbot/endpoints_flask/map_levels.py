from flask import Blueprint, jsonify, request
from functions.state_singleton import STATE

map_levels_bp = Blueprint("map_levels", __name__)


@map_levels_bp.get("/api/map-level-limits")
def api_get_map_level_limits():
    pd = STATE.get("player_data", {}) or {}
    return jsonify(pd.get("map_level_limits", {}) or {})


@map_levels_bp.post("/api/map-level-limits")
def api_set_map_level_limits():
    data = request.get_json(silent=True) or {}

    # allow two formats:
    # 1) { "map_level_limits": { ... } }
    # 2) { ... }  (direct map)
    limits = data.get("map_level_limits", data)

    if not isinstance(limits, dict):
        return jsonify({"error": "payload must be a dict (map -> {min,max,enabled})"}), 400


    # minimal validation
    allowed_maps = {"Lorencia", "Noria", "Devias", "Atlans", "Aida", "Icarus2", "LaCleon"}
    for map_name, cfg in limits.items():
        if not isinstance(map_name, str):
            return jsonify({"error": "map name must be a string"}), 400
        if map_name not in allowed_maps:
            return jsonify({"error": f"Unknown map name '{map_name}'"}), 400
        if not isinstance(cfg, dict):
            return jsonify({"error": f"value for '{map_name}' must be an object"}), 400

        if "min" in cfg and cfg["min"] is not None and not isinstance(cfg["min"], (int, float)):
            return jsonify({"error": f"'{map_name}.min' must be a number"}), 400
        if "max" in cfg and cfg["max"] is not None and not isinstance(cfg["max"], (int, float)):
            return jsonify({"error": f"'{map_name}.max' must be a number"}), 400
        if "enabled" in cfg and cfg["enabled"] is not None and not isinstance(cfg["enabled"], bool):
            return jsonify({"error": f"'{map_name}.enabled' must be true/false"}), 400

    STATE.update_dict("player_data", {
        "map_level_limits": limits
    })

    return jsonify({"ok": True, "map_level_limits": limits})