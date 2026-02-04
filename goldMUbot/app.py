from functions.scheduler import start_scheduler

import threading
import time
import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory
import logging

from flask_cors import CORS

from functions import config_loader
from logger_config import setup_logging
from functions.state_singleton import STATE
from loops.scraper_loop import scraper_loop
from loops.action_loop import action_loop

from endpoints_flask.state import state_bp
from endpoints_flask.map_levels import map_levels_bp
from endpoints_flask.map_spots import map_spots_bp


config = config_loader.load_config()

setup_logging()
logger = logging.getLogger(__name__)
logger.info(config)

SCRAPER_INTERVAL = config["scraper"]["interval"]
SCRAPER_PERSIST_INTERVAL = config["scraper"]["persist_interval"]
MAIN_PLAYER = config["mainplayer"]["nickname"]

app = Flask(__name__)

app.register_blueprint(state_bp)
app.register_blueprint(map_levels_bp)
app.register_blueprint(map_spots_bp)

@app.post("/api/scraper/force")
def force_scraper():
    force_event.set()
    return {"ok": True}

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/tab2.html")
def tab2():
    return render_template("tab2.html")

CORS(app, resources={
    r"/bot/*": {"origins": [
        "http://100.67.68.58:5065",
        "http://localhost:5065"
    ]}
})

stop_event = threading.Event()
force_event = threading.Event()


def start_threads():
    t = threading.Thread(
        target=scraper_loop,
        kwargs={
            "stop_event": stop_event,
            "force_event": force_event,
            "main_player": MAIN_PLAYER,
            "scraper_interval": SCRAPER_INTERVAL,
            "persist_interval": SCRAPER_PERSIST_INTERVAL,
        },
        daemon=True,
        name="scraper-loop",
    )
    t.start()
    logger.info("Scraper thread started")
    # --- ACTION THREAD ---
    t_action = threading.Thread(
        target=action_loop,
        kwargs={
            "stop_event": stop_event,
            "interval": 1,
        },
        daemon=True,
        name="action-loop",
    )
    t_action.start()
    logger.info("Action thread started")

@app.get("/api/state")
def api_state():
    snap = STATE.get_snapshot()
    if snap is None:
        snap = STATE.get("snapshot", {})
    return jsonify(snap or {})
    



if __name__ == "__main__":
    start_threads()
    start_scheduler()
    app.run(host="0.0.0.0", port=5065, debug=True, use_reloader=False)
