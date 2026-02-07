import time
import logging
from functions.state_singleton import STATE_SECOND_PLAYER
from functions import check_player_data

logger = logging.getLogger(__name__)

def second_player_scraper_loop(
    stop_event,
    force_event,
    second_player: str,
    scraper_interval: float,
    persist_interval: float,
):
    last_flush = 0.0

    while not stop_event.is_set():
        try:
            s = check_player_data.player_data(
                player_info=second_player,
                state_store=STATE_SECOND_PLAYER,
                state_key="second_player_data",
            )
            ts = time.time()
            snap = {"ts": ts, "state": s}

            STATE_SECOND_PLAYER.set_snapshot(snap)

            if ts - last_flush >= persist_interval:
                STATE_SECOND_PLAYER.flush_snapshot()
                last_flush = ts

        except Exception:
            logger.exception("scraper error")

        # czekaj na:
        # - normalny interval
        # - ALBO force_event
        force_event.wait(scraper_interval)
        force_event.clear()

