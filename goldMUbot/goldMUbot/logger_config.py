from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler


LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_INFO_FILE = LOG_DIR / "logs_info.log"
LOG_DEBUG_FILE = LOG_DIR / "logs_debug.log"


class OnlyInfoFilter(logging.Filter):
    def filter(self, record):
        return record.levelno == logging.INFO


class NoInfoFilter(logging.Filter):
    def filter(self, record):
        return record.levelno != logging.INFO


def setup_logging():
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s]: %(message)s"
    )

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    # -------- INFO -> logs_info.log --------
    info_handler = RotatingFileHandler(
        LOG_INFO_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    info_handler.setLevel(logging.INFO)
    info_handler.addFilter(OnlyInfoFilter())
    info_handler.setFormatter(formatter)

    # -------- DEBUG+ (bez INFO) -> logs_debug.log --------
    debug_handler = RotatingFileHandler(
        LOG_DEBUG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    debug_handler.setLevel(logging.DEBUG)
    debug_handler.addFilter(NoInfoFilter())
    debug_handler.setFormatter(formatter)

    # -------- Console: INFO+ --------
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root.addHandler(info_handler)
    root.addHandler(debug_handler)
    root.addHandler(console_handler)

    logging.getLogger("werkzeug").setLevel(logging.WARNING)
