# crabber-hook

A [Claude Code hook](https://docs.anthropic.com/en/docs/claude-code/hooks) system that connects Claude Code sessions to GitHub Projects V2. It reads JSON from stdin, interacts with the GitHub GraphQL API, and returns context to Claude via stdout.

## How It Works

Crabber provides argparse subcommands for each Claude Code hook event. Each command reads hook JSON from stdin, performs GitHub API operations, and writes context back to stdout.

### Supported Hooks

- **`session-start`** — On session start, loads `github_project_config.json` from the working directory. If an ongoing issue exists in `CURRENT_PROJECT_STATE.md`, fetches updates and injects the latest comment into Claude's context. If no current issue, picks the top item from the awaiting column.
- **`notification`** — Posts the notification message and title as a comment on the current GitHub issue.
- **`stop`** — Posts the stop reason as a comment on the current GitHub issue, then spawns a background process to terminate the parent Claude process after a delay.

## Setup

### Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/guides/install-python/) for dependency management
- A `GITHUB_TOKEN` environment variable with access to your GitHub organization's Projects V2

### Install

```bash
uv sync
```

### Project Configuration

Place a `github_project_config.json` in your project root:

```json
{
    "project_id": 1,
    "org_name": "your-org",
    "assignee": "your-github-username",
    "awaiting-task-column": "Awaiting",
    "inprogress-task-column": "In Progress",
    "in-review-task-column": "In Review"
}
```

### Claude Code Hook Configuration

Add the following to your `.claude/hooks.json` (or equivalent):

```json
{
    "hooks": {
        "SessionStart": [
            {
                "command": "python -m crabber.cli session-start"
            }
        ],
        "Notification": [
            {
                "command": "python -m crabber.cli notification"
            }
        ],
        "Stop": [
            {
                "command": "python -m crabber.cli stop"
            }
        ]
    }
}
```

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GITHUB_TOKEN` | Yes | — | GitHub personal access token with project read/write scope |
| `STOP_SLEEP_SECONDS` | No | `5` | Delay in seconds before killing the parent Claude process on stop |
| `LOG_LEVEL` | No | `DEBUG` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |

### CURRENT_PROJECT_STATE.md

Crabber reads project state from a free-form `CURRENT_PROJECT_STATE.md` file via regex. The following fields are recognized:

```
LAST_ISSUE_ID = https://github.com/org/repo/issues/123
LAST_ISSUE_STATE = ON_GOING
LAST_UPDATED_DATETIME = 2025-01-01T00:00:00Z
```

`LAST_ISSUE_STATE` values: `ON_GOING`, `COMPLETED`, `PENDING`

### Exit Codes

- **0** — Action proceeds. Stdout content is added to Claude's context.
- **1** — Error (e.g. missing stdin, invalid JSON).
- **2** — Action blocked. Stderr is returned to Claude as feedback.

## Development

### Install dev dependencies

```bash
pre-commit install
uv sync
```

### Run checks

```bash
uv run poe check      # ruff lint
uv run poe typecheck   # pyright
uv run poe test        # pytest
```
