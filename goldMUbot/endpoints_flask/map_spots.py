from flask import Blueprint, jsonify, request
from functions.state_singleton import STATE, STATE_SECOND_PLAYER

from functions.locations import (
    AIDA_LOCATIONS,
    ATLANS_LOCATIONS,
    KALIMA_LOCATIONS,
    KARUTAN2_LOCATIONS,
    LACLEON_LOCATIONS,
    ICARUS2_LOCATIONS,
)

map_spots_bp = Blueprint("map_spots", __name__, url_prefix="/api/locations")


def _persist_map_spot(slot_key: str, location: dict) -> None:
    def _apply(store, parent_key):
        parent = store.get(parent_key) or {}
        current_spots = parent.get("map_spots", {}) or {}
        store.update_dict(
            parent_key, {"map_spots": {**current_spots, slot_key: location}}
        )

    _apply(STATE, "main_player_data")
    _apply(STATE_SECOND_PLAYER, "second_player_data")


def _save_map_spot(slot_key: str):
    data = request.get_json(silent=True) or {}
    location = data.get("location")
    if not location:
        return jsonify({"error": "Invalid data"}), 400
    _persist_map_spot(slot_key, location)
    return jsonify({"ok": True, "saved": location})


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
    return _save_map_spot("aida_map_spots")


@map_spots_bp.post("/icarus2/save")
def save_icarus2_spot():
    return _save_map_spot("icarus2_map_spots")


@map_spots_bp.post("/atlans/save")
def save_atlans_spot():
    return _save_map_spot("atlans_map_spots")


@map_spots_bp.post("/lacleon/save")
def save_lacleon_spot():
    return _save_map_spot("lacleon_map_spots")


@map_spots_bp.post("/karutan2/save")
def save_karutan2_spot():
    return _save_map_spot("karutan2_map_spots")
