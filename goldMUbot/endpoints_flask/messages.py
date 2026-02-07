from flask import Blueprint, request, jsonify
from pathlib import Path
import time
import requests

from functions.host_api import send_message
from functions.state_singleton import STATE
from functions import config_loader

messages_bp = Blueprint('messages', __name__)

#test repo

CONFIG = config_loader.load_config()
HOSTAPI = CONFIG["hostapi"]
HOSTAPI_BASE_URL = f"http://{HOSTAPI['ip']}:{HOSTAPI['port']}"
SCREEN_CAPTURE_URL = f"{HOSTAPI_BASE_URL}{HOSTAPI['endpoints']['screen_capture']}"

STATIC_DATA_DIR = Path(__file__).resolve().parent.parent / "static" / "data"
STATIC_DATA_DIR.mkdir(parents=True, exist_ok=True)

@messages_bp.route('/api/send_message_ui', methods=['POST'])
def api_send_message_ui():
	data = request.get_json() or {}
	text = data.get('text', '').strip()
	player_info = data.get('player_info')
	if not player_info:
		player_info = STATE.get('main_player_data', {}).get('player') or ''
	result = None

	STATE.update_dict('send_message_via_ui', {
		'message': text,
		'player': player_info,
		'new_message': True
	})
	return jsonify({'ok': True, 'result': result})


@messages_bp.route('/api/screen_preview', methods=['POST'])
def api_screen_preview():
	data = request.get_json() or {}
	title = data.get('title')
	if not title:
		player = STATE.get('main_player_data', {}).get('player') or ''
		title = f"GoldMU || Player: {player}".strip()
	rect = data.get('rect') or {"x": 29, "y": 35, "w": 110, "h": 12}
	if not isinstance(rect, dict):
		return jsonify({'ok': False, 'error': 'rect must be an object'}), 400
	payload = {
		"title": title,
		"rect": rect
	}
	try:
		resp = requests.post(SCREEN_CAPTURE_URL, json=payload, timeout=30)
		resp.raise_for_status()
	except requests.RequestException as exc:
		return jsonify({'ok': False, 'error': str(exc)}), 502

	filename = 'screen_preview.png'
	filepath = STATIC_DATA_DIR / filename
	filepath.write_bytes(resp.content)
	cache_bust = int(time.time())
	return jsonify({
		'ok': True,
		'path': f"/static/data/{filename}?v={cache_bust}"
	})



