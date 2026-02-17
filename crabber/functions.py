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
    ProjectState,
    StopHookInput,
)
from crabber.github_client import GitHubClient
from crabber.settings import CONFIG_FILENAME, STOP_SLEEP_SECONDS

logger = logging.getLogger(__name__)


def _prompt(label: str, default: str = "") -> str:
    """Prompt the user for input, showing a default value in brackets."""
    if default:
        raw = input(f"{label} [{default}]: ").strip()
        return raw or default
    while True:
        raw = input(f"{label}: ").strip()
        if raw:
            return raw


def _parse_project_url(url: str) -> tuple[str, int] | None:
    """Extract (org_name, project_id) from a GitHub Projects V2 URL."""
    match = re.match(r"https://github\.com/orgs/([^/]+)/projects/(\d+)", url)
    if match:
        return match.group(1), int(match.group(2))
    return None


def _prompt_project_url() -> tuple[str, int]:
    """Prompt for a GitHub project URL and extract org and project ID."""
    while True:
        url = input("GitHub project URL (e.g. https://github.com/orgs/myorg/projects/1): ").strip()
        result = _parse_project_url(url)
        if result:
            return result
        print("Invalid URL. Expected format: https://github.com/orgs/<org>/projects/<id>")  # noqa: T201


def handle_init(output_dir: Path) -> None:
    """Interactively create a github_project_config.json file."""
    org_name, project_id = _prompt_project_url()
    assignee = _prompt("Assignee (GitHub username)")
    awaiting_task_column = _prompt("Awaiting task column name", "Awaiting")
    inprogress_task_column = _prompt("In-progress task column name", "In Progress")
    in_review_task_column = _prompt("In-review task column name", "In Review")

    config_data = {
        "org_name": org_name,
        "project_id": project_id,
        "assignee": assignee,
        "awaiting-task-column": awaiting_task_column,
        "inprogress-task-column": inprogress_task_column,
        "in-review-task-column": in_review_task_column,
    }
    config = GithubProjectConfig(**config_data)

    config_path = output_dir / CONFIG_FILENAME
    config_path.write_text(json.dumps(config.model_dump(by_alias=True), indent=4) + "\n")
    print(f"Wrote {config_path}")  # noqa: T201

    answer = input("Add github_project_config.json to .gitignore? [Y/n]: ").strip().lower()
    if answer in ("", "y", "yes"):
        gitignore_path = output_dir / ".gitignore"
        if gitignore_path.is_file():
            content = gitignore_path.read_text()
            if CONFIG_FILENAME not in content.splitlines():
                with gitignore_path.open("a") as f:
                    if content and not content.endswith("\n"):
                        f.write("\n")
                    f.write(f"{CONFIG_FILENAME}\n")
                print(f"Appended {CONFIG_FILENAME} to .gitignore")  # noqa: T201
            else:
                print(f"{CONFIG_FILENAME} already in .gitignore")  # noqa: T201
        else:
            gitignore_path.write_text(f"{CONFIG_FILENAME}\n")
            print(f"Created .gitignore with {CONFIG_FILENAME}")  # noqa: T201


def load_project_config(cwd: Path) -> GithubProjectConfig | None:
    config_path = cwd / CONFIG_FILENAME
    if not config_path.is_file():
        logger.debug("No %s found in %s", CONFIG_FILENAME, cwd)
        return None
    with config_path.open() as f:
        data = json.load(f)
    return GithubProjectConfig(**data)


def parse_project_state(cwd: Path) -> ProjectState:
    state_path = cwd / "CURRENT_PROJECT_STATE.md"
    if not state_path.is_file():
        return ProjectState()

    content = state_path.read_text()
    values: dict[str, str | None] = {}
    key_map = {
        "LAST_ISSUE_ID": "last_issue_id",
        "LAST_ISSUE_STATE": "last_issue_state",
        "LAST_UPDATED_DATETIME": "last_updated_datetime",
    }
    for file_key, field_name in key_map.items():
        match = re.search(rf"{file_key}\s*[=:]\s*(.+)", content)
        if match:
            values[field_name] = match.group(1).strip()

    return ProjectState(**values)


def _extract_issue_parts(issue_id: str) -> tuple[str, str, int] | None:
    """Extract owner, repo, issue_number from an issue URL."""
    url_match = re.match(r"https://github\.com/([^/]+)/([^/]+)/issues/(\d+)", issue_id)
    if url_match:
        return url_match.group(1), url_match.group(2), int(url_match.group(3))
    return None


def _get_issue_context(cwd: Path) -> tuple[str, str, int] | None:
    """Check project is configured and return (owner, repo, issue_number) or None."""
    config_path = cwd / CONFIG_FILENAME
    if not config_path.is_file():
        logger.debug("No %s found in %s, skipping", CONFIG_FILENAME, cwd)
        return None

    state = parse_project_state(cwd)
    if not state.last_issue_id:
        logger.debug("No LAST_ISSUE_ID in project state")
        return None

    parts = _extract_issue_parts(state.last_issue_id)
    if parts is None:
        logger.warning("Cannot parse issue ID: %s", state.last_issue_id)
        return None

    return parts


def handle_session_start(input_data: HookInput) -> tuple[str, int]:
    cwd = Path(input_data.cwd)
    config = load_project_config(cwd)
    if config is None:
        return "", 0

    state = parse_project_state(cwd)
    client = GitHubClient()

    if state.last_issue_id and state.last_issue_state in (IssueState.ON_GOING.value, IssueState.PENDING.value):
        return _handle_existing_issue(client, state.last_issue_id, state.last_updated_datetime)

    if not state.last_issue_id:
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

    if last_updated and issue.updated_at <= last_updated:
        return "", 0

    summary = f"{issue.title}\n\n{issue.body}"
    latest_comment = issue.comments[0].body if issue.comments else "No comments yet."

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
    context = _get_issue_context(cwd)
    if context is None:
        return "", 0

    owner, repo, issue_number = context
    comment_body = f"{input_data.message}: {input_data.title}\n\nWhich should we do:\n0: Continue\n2: Stop and review"

    client = GitHubClient()
    client.post_issue_comment(owner, repo, issue_number, comment_body)
    return "", 0


def handle_stop(input_data: StopHookInput) -> tuple[str, int]:
    cwd = Path(input_data.cwd)
    context = _get_issue_context(cwd)
    if context is None:
        return "", 0

    owner, repo, issue_number = context
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
