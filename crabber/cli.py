import json
import logging
import sys

from crabber.definitions import HookInput, NotificationHookInput, StopHookInput
from crabber.functions import handle_notification, handle_session_start, handle_stop

logger = logging.getLogger(__name__)


def dispatch(raw_input: str) -> tuple[str, int]:
    """Parse stdin JSON and dispatch to the appropriate handler.

    Returns (output, exit_code).
    """
    if not raw_input.strip():
        logger.debug("Empty stdin, exiting")
        return "", 0

    try:
        data = json.loads(raw_input)
    except json.JSONDecodeError:
        logger.exception("Failed to parse stdin JSON")
        return "", 1

    hook_event_name = data.get("hook_event_name", "")
    logger.debug("Received hook event: %s", hook_event_name)

    if hook_event_name == "SessionStart":
        input_data = HookInput(**data)
        return handle_session_start(input_data)

    if hook_event_name == "Notification":
        input_data = NotificationHookInput(**data)
        return handle_notification(input_data)

    if hook_event_name == "Stop":
        input_data = StopHookInput(**data)
        return handle_stop(input_data)

    logger.debug("Unhandled hook event: %s", hook_event_name)
    return "", 0


def main() -> None:
    raw_input = sys.stdin.read()
    output, exit_code = dispatch(raw_input)

    if output:
        sys.stdout.write(output)
        sys.stdout.flush()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
