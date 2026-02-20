import logging
import sys
from importlib.metadata import version
from logging.handlers import RotatingFileHandler

from crabber.settings import LOG_BACKUP_COUNT, LOG_DIR, LOG_FILE, LOG_MAX_BYTES

__version__ = version("crabber")

LOG_FORMAT = "%(asctime)s [%(levelname)s] (%(name)s) %(funcName)s: %(message)s"
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG, force=True, format=LOG_FORMAT)

# Rotating file handler for persistent logs
LOG_DIR.mkdir(parents=True, exist_ok=True)
_file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=LOG_MAX_BYTES,
    backupCount=LOG_BACKUP_COUNT,
)
_file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
logging.getLogger().addHandler(_file_handler)

# Suppress specific loggers to reduce noise
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
