

from asyncio.log import logger
from functions.state_singleton import STATE
from functions.host_api import send_message


def send_message_via_ui(player_info=None):
    state = STATE.get_all()
    send_message_data = state.get("send_message_via_ui") or {}
    if send_message_data.get("new_message"):
        text = send_message_data.get("message", "")
        if text:
            try:
                send_message(text, player_info=player_info)
            except Exception as exc:
                logger.error(f"Error sending message via UI: {exc}")
        STATE.update_dict('send_message_via_ui', {
            'new_message': False
        })