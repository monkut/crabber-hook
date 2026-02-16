import logging
import sys

__version__ = "0.1.0"

LOG_FORMAT = "%(asctime)s [%(levelname)s] (%(name)s) %(funcName)s: %(message)s"
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG, force=True, format=LOG_FORMAT)

# Suppress specific loggers to reduce noise
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
