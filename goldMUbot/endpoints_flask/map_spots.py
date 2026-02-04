from flask import Blueprint, jsonify, request
from functions.state_singleton import STATE

from functions.locations import AIDA_LOCATIONS, ATLANS_LOCATIONS, KALIMA_LOCATIONS, KARUTAN2_LOCATIONS, LACLEON_LOCATIONS, ICARUS2_LOCATIONS

map_spots_bp = Blueprint('map_spots', __name__, url_prefix='/api/locations')

@map_spots_bp.get("/aida")
def get_aida_locations():
    return jsonify(AIDA_LOCATIONS)

@map_spots_bp.get("/icarus2")
def get_icarus2_locations():
    return jsonify(ICARUS2_LOCATIONS)

@map_spots_bp.get("/atlans")
def get_atlans_locations():
    return jsonify(ATLANS_LOCATIONS)

@map_spots_bp.get("/kalima")
def get_kalima_locations():
    return jsonify(KALIMA_LOCATIONS)

@map_spots_bp.get("/karutan2")
def get_karutan2_locations():
    return jsonify(KARUTAN2_LOCATIONS)

@map_spots_bp.get("/lacleon")
def get_lacleon_locations():
    return jsonify(LACLEON_LOCATIONS)

@map_spots_bp.post("/aida/save")
def save_aida_spot():
    data = request.json
    if not data or 'location' not in data:
        return jsonify({"error": "Invalid data"}), 400
    location = data['location']
    current_map_spots = STATE.get('player_data', {}).get('map_spots', {})
    STATE.update_dict('player_data', {'map_spots': {**current_map_spots, 'aida_map_spots': location}})
    return jsonify({"ok": True, "saved": location})

@map_spots_bp.post("/icarus2/save")
def save_icarus2_spot():
    data = request.json
    if not data or 'location' not in data:
        return jsonify({"error": "Invalid data"}), 400
    location = data['location']
    current_map_spots = STATE.get('player_data', {}).get('map_spots', {})
    STATE.update_dict('player_data', {'map_spots': {**current_map_spots, 'icarus2_map_spots': location}})
    return jsonify({"ok": True, "saved": location})

@map_spots_bp.post("/atlans/save")
def save_atlans_spot():
    data = request.json
    if not data or 'location' not in data:
        return jsonify({"error": "Invalid data"}), 400
    location = data['location']
    current_map_spots = STATE.get('player_data', {}).get('map_spots', {})
    STATE.update_dict('player_data', {'map_spots': {**current_map_spots, 'atlans_map_spots': location}})
    return jsonify({"ok": True, "saved": location})

@map_spots_bp.post("/lacleon/save")
def save_lacleon_spot():
    data = request.json
    if not data or 'location' not in data:
        return jsonify({"error": "Invalid data"}), 400
    location = data['location']
    current_map_spots = STATE.get('player_data', {}).get('map_spots', {})
    STATE.update_dict('player_data', {'map_spots': {**current_map_spots, 'lacleon_map_spots': location}})
    return jsonify({"ok": True, "saved": location})
