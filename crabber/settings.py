import logging
import os

# logging.basicConfig set in __init__.py
logger = logging.getLogger()

DEFAULT_LOG_LEVEL = "DEBUG"
LOG_LEVEL = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
if LOG_LEVEL and LOG_LEVEL in ("INFO", "ERROR", "WARNING", "DEBUG", "CRITICAL"):
    level = getattr(logging, LOG_LEVEL)
    logger.setLevel(level)

# GitHub API
GITHUB_TOKEN: str | None = os.getenv("GITHUB_TOKEN")
GITHUB_GRAPHQL_URL: str = "https://api.github.com/graphql"

# Config
CONFIG_FILENAME: str = "github_project_config.json"

# Stop hook
DEFAULT_STOP_SLEEP_SECONDS: int = 5
STOP_SLEEP_SECONDS: int = int(os.getenv("STOP_SLEEP_SECONDS", str(DEFAULT_STOP_SLEEP_SECONDS)))
