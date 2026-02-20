"""Tests for crabber package-level logging setup."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from crabber.settings import LOG_DIR, LOG_FILE


def test_root_logger_has_rotating_file_handler() -> None:
    """Root logger includes a RotatingFileHandler after crabber import."""
    root = logging.getLogger()
    handler_types = [type(h) for h in root.handlers]
    assert RotatingFileHandler in handler_types


def test_log_directory_exists() -> None:
    """The log directory is created on import."""
    assert LOG_DIR.exists()
    assert LOG_DIR.is_dir()


def test_log_file_path_is_under_log_dir() -> None:
    """LOG_FILE sits inside LOG_DIR."""
    assert LOG_FILE.parent == LOG_DIR
    assert LOG_FILE.name == "crabber.log"


def test_log_dir_is_in_home_crabber() -> None:
    """LOG_DIR resolves to ~/.crabber/logs."""
    expected = Path.home() / ".crabber" / "logs"
    assert expected == LOG_DIR
