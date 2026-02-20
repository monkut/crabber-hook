# crabber-hook

A [Claude Code hook](https://docs.anthropic.com/en/docs/claude-code/hooks) system that connects Claude Code sessions to GitHub Projects V2. It reads JSON from stdin, interacts with the GitHub GraphQL API, and returns context to Claude via stdout.

## How It Works

Crabber provides argparse subcommands for each Claude Code hook event. Each command reads hook JSON from stdin, performs GitHub API operations, and writes context back to stdout.

### Supported Hooks

- **`session-start`** — On session start, loads `github_project_config.json` from the working directory. If an ongoing issue exists in `CHECKPOINT.md`, fetches updates and injects the latest comment into Claude's context. If no current issue, picks the top item from the awaiting column.
- **`notification`** — Posts the notification message and title as a comment on the current GitHub issue.
- **`stop`** — Posts the stop reason as a comment on the current GitHub issue, then spawns a background process to terminate the parent Claude process after a delay.

## Setup

### Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/guides/install-python/) for dependency management
- A `GITHUB_TOKEN` environment variable with access to your GitHub organization's Projects V2

### Install via uvx (recommended)

Run directly from the repository without a local clone:

```bash
uvx --from git+https://github.com/kiconiaworks/crabber-hook crabber --help
```

Use this form in your `.claude/hooks.json` to run hooks without a local install:

```bash
uvx --from git+https://github.com/kiconiaworks/crabber-hook crabber session-start
```

### Install from source

```bash
uv sync

# Install the `crabber` CLI command (editable/development mode)
uv pip install -e .
```

### Project Configuration

Generate a `github_project_config.json` interactively:

```bash
crabber init
```

The command prompts for your organization, project ID, assignee, and column names (with sensible defaults). It optionally adds the config file to `.gitignore`.

To write the config to a different directory:

```bash
crabber init --output-dir path/to/project
```

Or create the file manually in your project root:

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

Add the following `hooks` key to your project-level `.claude/settings.json` (shared/committed) or `.claude/settings.local.json` (local only):

```json
{
    "hooks": {
        "SessionStart": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "crabber session-start"
                    }
                ]
            }
        ],
        "Notification": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "crabber notification"
                    }
                ]
            }
        ],
        "Stop": [
            {
                "matcher": "",
                "hooks": [
                    {
                        "type": "command",
                        "command": "crabber stop"
                    }
                ]
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

### Logs

Crabber writes persistent logs to `~/.crabber/logs/crabber.log` using a rotating file handler (1 MB max, 3 backups). Logs are written alongside the existing stderr output.

### CHECKPOINT.md

Crabber reads project state from a free-form `CHECKPOINT.md` file via regex. The following fields are recognized:

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
