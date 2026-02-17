from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from crabber.definitions import HookInput, NotificationHookInput, StopHookInput
from crabber.functions import handle_init, handle_notification, handle_session_start, handle_stop

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


def _run_and_exit(output: str, exit_code: int) -> None:
    if output:
        sys.stdout.write(output)
        sys.stdout.flush()
    sys.exit(exit_code)


def cmd_session_start(_args: argparse.Namespace) -> None:
    data = _read_stdin()
    if data is None:
        sys.exit(1)
    input_data = HookInput(**data)
    output, exit_code = handle_session_start(input_data)
    _run_and_exit(output, exit_code)


def cmd_notification(_args: argparse.Namespace) -> None:
    data = _read_stdin()
    if data is None:
        sys.exit(1)
    input_data = NotificationHookInput(**data)
    output, exit_code = handle_notification(input_data)
    _run_and_exit(output, exit_code)


def cmd_stop(_args: argparse.Namespace) -> None:
    data = _read_stdin()
    if data is None:
        sys.exit(1)
    input_data = StopHookInput(**data)
    output, exit_code = handle_stop(input_data)
    _run_and_exit(output, exit_code)


def cmd_init(args: argparse.Namespace) -> None:
    handle_init(Path(args.output_dir))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crabber",
        description="Claude Code hook dispatcher for GitHub Projects V2",
    )
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
    if args.command != "init" and not os.getenv("GITHUB_TOKEN"):
        parser.error("GITHUB_TOKEN environment variable is required")
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
