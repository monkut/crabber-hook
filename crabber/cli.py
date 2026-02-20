from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import typing
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Sequence

from crabber import __version__
from crabber.definitions import HookInput, NotificationHookInput, StopHookInput
from crabber.functions import HookHandler, handle_init
from crabber.github_client import GitHubClient

logger = logging.getLogger(__name__)


def _read_stdin() -> dict | None:
    """Read and parse JSON from stdin. Returns None on empty or invalid input."""
    raw_input = sys.stdin.read()
    if not raw_input.strip():
        logger.debug("Empty stdin")
        return None
    try:
        return json.loads(raw_input)
    except json.JSONDecodeError:
        logger.exception("Failed to parse stdin JSON")
        return None


def _read_and_parse[T: BaseModel](model_cls: type[T]) -> T:
    """Read JSON from stdin and parse into a Pydantic model, or exit with code 1."""
    data = _read_stdin()
    if data is None:
        sys.exit(1)
    return model_cls(**data)


def _run_and_exit(output: str, exit_code: int, *, stream: typing.TextIO | None = None) -> None:
    if output:
        target = stream or sys.stdout
        target.write(output)
        target.flush()
    sys.exit(exit_code)


def _make_handler() -> HookHandler:
    return HookHandler(GitHubClient())


def _require_github_token() -> bool:
    """Check if GITHUB_TOKEN is set. Log warning and return False if missing."""
    if not os.getenv("GITHUB_TOKEN"):
        logger.warning("GITHUB_TOKEN not set, skipping hook")
        return False
    return True


def cmd_session_start(_args: argparse.Namespace) -> None:
    if not _require_github_token():
        sys.exit(0)
    input_data = _read_and_parse(HookInput)
    handler = _make_handler()
    output, exit_code = handler.handle_session_start(input_data)
    _run_and_exit(output, exit_code)


def cmd_notification(_args: argparse.Namespace) -> None:
    if not _require_github_token():
        sys.exit(0)
    input_data = _read_and_parse(NotificationHookInput)
    handler = _make_handler()
    output, exit_code = handler.handle_notification(input_data)
    _run_and_exit(output, exit_code, stream=sys.stderr)


def cmd_stop(_args: argparse.Namespace) -> None:
    if not _require_github_token():
        sys.exit(0)
    input_data = _read_and_parse(StopHookInput)
    handler = _make_handler()
    output, exit_code = handler.handle_stop(input_data)
    _run_and_exit(output, exit_code)


def cmd_init(args: argparse.Namespace) -> None:
    handle_init(Path(args.output_dir))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crabber",
        description="Claude Code hook dispatcher for GitHub Projects V2",
    )
    parser.add_argument("--version", action="version", version=f"crabber {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sp_session = subparsers.add_parser("session-start", help="Handle SessionStart hook")
    sp_session.set_defaults(func=cmd_session_start)

    sp_notification = subparsers.add_parser("notification", help="Handle Notification hook")
    sp_notification.set_defaults(func=cmd_notification)

    sp_stop = subparsers.add_parser("stop", help="Handle Stop hook")
    sp_stop.set_defaults(func=cmd_stop)

    sp_init = subparsers.add_parser("init", help="Interactively create github_project_config.json")
    sp_init.add_argument("--output-dir", default=".", help="Directory to write config file (default: cwd)")
    sp_init.set_defaults(func=cmd_init)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
