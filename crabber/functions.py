import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

from crabber.definitions import (
    GithubProjectConfig,
    HookInput,
    IssueState,
    NotificationHookInput,
    StopHookInput,
)
from crabber.github_client import GitHubClient
from crabber.settings import CONFIG_FILENAME, STOP_SLEEP_SECONDS

logger = logging.getLogger(__name__)


def load_project_config(cwd: Path) -> GithubProjectConfig | None:
    config_path = cwd / CONFIG_FILENAME
    if not config_path.is_file():
        logger.debug("No %s found in %s", CONFIG_FILENAME, cwd)
        return None
    with config_path.open() as f:
        data = json.load(f)
    return GithubProjectConfig(**data)


def parse_project_state(cwd: Path) -> dict[str, str | None]:
    state_path = cwd / "CURRENT_PROJECT_STATE.md"
    result: dict[str, str | None] = {
        "LAST_ISSUE_ID": None,
        "LAST_ISSUE_STATE": None,
        "LAST_UPDATED_DATETIME": None,
    }
    if not state_path.is_file():
        return result

    content = state_path.read_text()
    for key in result:
        match = re.search(rf"{key}\s*[=:]\s*(.+)", content)
        if match:
            result[key] = match.group(1).strip()

    return result


def _extract_issue_parts(issue_id: str) -> tuple[str, str, int] | None:
    """Extract owner, repo, issue_number from an issue URL."""
    url_match = re.match(r"https://github\.com/([^/]+)/([^/]+)/issues/(\d+)", issue_id)
    if url_match:
        return url_match.group(1), url_match.group(2), int(url_match.group(3))
    return None


def handle_session_start(input_data: HookInput) -> tuple[str, int]:
    cwd = Path(input_data.cwd)
    config = load_project_config(cwd)
    if config is None:
        return "", 0

    state = parse_project_state(cwd)
    client = GitHubClient()

    last_issue_id = state.get("LAST_ISSUE_ID")
    last_issue_state = state.get("LAST_ISSUE_STATE")
    last_updated = state.get("LAST_UPDATED_DATETIME")

    if last_issue_id and last_issue_state in (IssueState.ON_GOING.value, IssueState.PENDING.value):
        return _handle_existing_issue(client, last_issue_id, last_updated)

    if not last_issue_id:
        return _handle_new_issue(client, config)

    return "", 0


def _handle_existing_issue(
    client: GitHubClient,
    issue_id: str,
    last_updated: str | None,
) -> tuple[str, int]:
    parts = _extract_issue_parts(issue_id)
    if parts is None:
        logger.warning("Cannot parse issue ID: %s", issue_id)
        return "", 0

    owner, repo, issue_number = parts
    issue = client.get_issue_details(owner, repo, issue_number)
    current_updated = issue.get("updatedAt", "")

    if last_updated and current_updated <= last_updated:
        return "", 0

    title = issue.get("title", "")
    body = issue.get("body", "")
    summary = f"{title}\n\n{body}"

    comments = issue.get("comments", {}).get("nodes", [])
    latest_comment = comments[0]["body"] if comments else "No comments yet."

    output = (
        f"Here is a summary of the current issue:\n\n"
        f"    {summary}\n\n"
        f"Review the latest comment below and address the comments, "
        f"when complete run the `/checkpoint` command, then respond to the comments in the issue.\n"
        f"    {latest_comment}\n"
    )
    return output, 0


def _handle_new_issue(client: GitHubClient, config: GithubProjectConfig) -> tuple[str, int]:
    items = client.get_items_for_column(
        org=config.org_name,
        project_number=config.project_id,
        column_name=config.awaiting_task_column,
        assignee=config.assignee,
    )
    if not items:
        return "", 0

    top_item = items[0]
    if top_item.content is None:
        return "", 0

    content = top_item.content
    issue_content = f"#{content.number}: {content.title}\n\n{content.body}\n\n{content.url}"

    output = f"Review the following and address the issue:\n\n    {issue_content}\n"
    return output, 0


def handle_notification(input_data: NotificationHookInput) -> tuple[str, int]:
    cwd = Path(input_data.cwd)
    config = load_project_config(cwd)
    if config is None:
        return "", 0

    state = parse_project_state(cwd)
    last_issue_id = state.get("LAST_ISSUE_ID")
    if not last_issue_id:
        logger.debug("No LAST_ISSUE_ID in project state, skipping notification")
        return "", 0

    parts = _extract_issue_parts(last_issue_id)
    if parts is None:
        logger.warning("Cannot parse issue ID: %s", last_issue_id)
        return "", 0

    owner, repo, issue_number = parts

    comment_body = f"{input_data.message}: {input_data.title}\n\nWhich should we do:\n0: Continue\n2: Stop and review"

    client = GitHubClient()
    client.post_issue_comment(owner, repo, issue_number, comment_body)
    return "", 0


def handle_stop(input_data: StopHookInput) -> tuple[str, int]:
    cwd = Path(input_data.cwd)
    config = load_project_config(cwd)
    if config is None:
        return "", 0

    state = parse_project_state(cwd)
    last_issue_id = state.get("LAST_ISSUE_ID")
    if not last_issue_id:
        logger.debug("No LAST_ISSUE_ID in project state, skipping stop comment")
        return "", 0

    parts = _extract_issue_parts(last_issue_id)
    if parts is None:
        logger.warning("Cannot parse issue ID: %s", last_issue_id)
        return "", 0

    owner, repo, issue_number = parts

    comment_body = f"Claude Code session stopped. Reason: {input_data.stop_reason}"

    client = GitHubClient()
    client.post_issue_comment(owner, repo, issue_number, comment_body)

    _spawn_kill_process()

    return "", 0


def _spawn_kill_process() -> None:
    parent_pid = os.getppid()
    subprocess.Popen(  # noqa: S603
        [
            sys.executable,
            "-c",
            (f"import time, os, signal; time.sleep({STOP_SLEEP_SECONDS}); os.kill({parent_pid}, signal.SIGTERM)"),
        ],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    logger.debug("Spawned kill process for PID %d with %ds delay", parent_pid, STOP_SLEEP_SECONDS)
