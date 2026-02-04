#------------------------ scraper loop ------------------------
# scraper loop gets data and save it to state (that kind of data not need mouse action )
# loops/scraper_loop.py
import time
import logging
from functions.state_singleton import STATE
from functions import check_player_data

logger = logging.getLogger(__name__)

def scraper_loop(
    stop_event,
    force_event,
    main_player: str,
    scraper_interval: float,
    persist_interval: float,
):
    last_flush = 0.0

    while not stop_event.is_set():
        try:
            s = check_player_data.player_data(player_info=main_player)
            ts = time.time()
            snap = {"ts": ts, "state": s}

            STATE.set_snapshot(snap)

            if ts - last_flush >= persist_interval:
                STATE.flush_snapshot()
                last_flush = ts

        except Exception:
            logger.exception("scraper error")

        # czekaj na:
        # - normalny interval
        # - ALBO force_event
        force_event.wait(scraper_interval)
        force_event.clear()

