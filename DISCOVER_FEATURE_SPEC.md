# Feature Spec: `discover` Command

## Summary

Add a `crabber discover` command that scans a parent directory for project subdirectories containing `github_project_config.json`, launches a `claude` process in each, and reports a summary of started processes.

## Motivation

Running crabber-hooked Claude sessions across many repos currently requires manually navigating to each project and starting Claude individually. The `discover` command automates this by scanning a directory tree and spawning Claude in every configured project.

## CLI Interface

```
crabber discover --projects-directory <path> [--dry-run] [--print-prompt]
```

### Options

| Option | Required | Default | Description |
|---|---|---|---|
| `--projects-directory` | Yes | — | Path to a directory containing project subdirectories |
| `--dry-run` | No | `False` | List discovered projects without launching Claude |
| `--print-prompt` | No | `False` | Print the prompt passed to claude for each discovered project |

### Constraints

- `--projects-directory` must exist and be a directory; exit with error if not
- Only **immediate** subdirectories are scanned (no recursive descent)
- A subdirectory qualifies if it contains `github_project_config.json` (value of `settings.CONFIG_FILENAME`)

## Behavior

### 1. Discovery

Iterate immediate subdirectories of `--projects-directory`. For each, check for `<subdir>/github_project_config.json`. Collect qualifying paths into a list.

If no qualifying directories are found, log a warning and exit 0.

### 2. Prompt Resolution

installed crabber hooks will trigger 'github project' issue processing.

### 3. Process Launch

For each qualifying directory, spawn:

```
claude --dangerously-skip-permissions
```

- `cwd` set to the qualifying subdirectory
- Process started detached via `subprocess.Popen` (not waited on)
- `--dangerously-skip-permissions` is required — crabber hooks handle project context, so Claude must run non-interactively

### 4. Discovery Summary

After all processes launch, log a summary table to stderr and to the rotating log file (`~/.crabber/logs/crabber.log`):

```
=== crabber discover summary ===
Projects scanned: 12
Projects matched: 3
Claude processes started: 3

  PID    Project
  -----  ----------------------------
  48201  /home/user/projects/repo-alpha
  48215  /home/user/projects/repo-beta
  48220  /home/user/projects/repo-gamma
```

If `--dry-run`, replace the process table with a list of matched directories and skip launching.

## Integration Points

- **`settings.py`**: Reuse `CONFIG_FILENAME` for the config file check
- **`cli.py`**: Register `discover` subparser in `build_parser()`, wire to `cmd_discover`
- **`functions.py`**: Add `discover_projects(projects_directory: Path) -> list[Path]` and `launch_claude_sessions(projects: list[Path]) -> list[tuple[int, Path]]`
- **No `GITHUB_TOKEN` required**: `discover` only scans the filesystem and spawns processes; token validation in `main()` should exclude `discover` (same pattern as `init`)

## Pre-flight Checks

Before scanning or launching, `discover` validates the environment:

1. `--projects-directory` exists and is a directory
2. `claude` binary is on PATH
3. `GITHUB_TOKEN` is set — spawned Claude sessions invoke crabber hooks (`session-start`, `notification`, `stop`) which all require the token. Fail early rather than spawning sessions that break on every hook call.

All three checks must pass or the command exits 1 with a descriptive error.

## Error Handling

| Condition | Behavior |
|---|---|
| `--projects-directory` doesn't exist | Exit 1 with error message |
| `--projects-directory` is a file | Exit 1 with error message |
| `GITHUB_TOKEN` not set | Exit 1: "GITHUB_TOKEN is required — hooks in spawned sessions depend on it" |
| `claude` binary not found on PATH | Exit 1 with error message |
| No subdirectories contain config | Log warning, exit 0 |
| A single subprocess fails to start | Log error for that project, continue with remaining |

## Testing

- **Unit**: Mock `subprocess.Popen`, verify correct `cwd` and args per project
- **Unit**: `discover_projects()` with a temp directory tree (some with config, some without)
- **Unit**: Dry-run produces expected output without spawning processes
- **Integration**: CLI parser accepts `--projects-directory`, rejects missing value
- **Unit**: `--print-prompt` outputs prompt text without launching

## Out of Scope

- Recursive directory scanning (only immediate subdirectories)
- Process lifecycle management (monitoring, restarting, health checks)
- Parallel launch throttling / rate limiting
- Config validation beyond file existence