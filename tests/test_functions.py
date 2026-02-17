import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

from crabber.definitions import (
    GithubProjectConfig,
    HookInput,
    NotificationHookInput,
    ProjectItem,
    ProjectItemContent,
    StopHookInput,
)
from crabber.functions import (
    _parse_project_url,
    handle_init,
    handle_notification,
    handle_session_start,
    handle_stop,
    load_project_config,
    parse_project_state,
)
from crabber.settings import CONFIG_FILENAME

SAMPLE_CONFIG = {
    "project_id": 42,
    "org_name": "test-org",
    "assignee": "testuser",
    "awaiting-task-column": "Awaiting",
    "inprogress-task-column": "In Progress",
    "in-review-task-column": "In Review",
}


class TestLoadProjectConfig(TestCase):
    def test_load_valid_config(self, tmp_path: Path | None = None):
        tmp = tmp_path or Path("/tmp/test_load_config")
        tmp.mkdir(parents=True, exist_ok=True)
        config_file = tmp / "github_project_config.json"
        config_file.write_text(json.dumps(SAMPLE_CONFIG))

        result = load_project_config(tmp)

        assert result is not None
        assert result.project_id == 42
        assert result.org_name == "test-org"
        assert result.assignee == "testuser"
        assert result.awaiting_task_column == "Awaiting"

        config_file.unlink()

    def test_load_missing_config(self):
        result = load_project_config(Path("/tmp/nonexistent_dir_12345"))
        assert result is None


class TestParseProjectState(TestCase):
    def test_parse_with_values(self):
        tmp = Path("/tmp/test_parse_state")
        tmp.mkdir(parents=True, exist_ok=True)
        state_file = tmp / "CURRENT_PROJECT_STATE.md"
        state_file.write_text(
            "# Project State\n"
            "LAST_ISSUE_ID = https://github.com/org/repo/issues/123\n"
            "LAST_ISSUE_STATE = ON_GOING\n"
            "LAST_UPDATED_DATETIME = 2025-01-01T00:00:00Z\n"
        )

        result = parse_project_state(tmp)

        assert result["LAST_ISSUE_ID"] == "https://github.com/org/repo/issues/123"
        assert result["LAST_ISSUE_STATE"] == "ON_GOING"
        assert result["LAST_UPDATED_DATETIME"] == "2025-01-01T00:00:00Z"

        state_file.unlink()

    def test_parse_with_colon_separator(self):
        tmp = Path("/tmp/test_parse_state_colon")
        tmp.mkdir(parents=True, exist_ok=True)
        state_file = tmp / "CURRENT_PROJECT_STATE.md"
        state_file.write_text("LAST_ISSUE_ID: https://github.com/org/repo/issues/99\n")

        result = parse_project_state(tmp)
        assert result["LAST_ISSUE_ID"] == "https://github.com/org/repo/issues/99"

        state_file.unlink()

    def test_parse_missing_file(self):
        result = parse_project_state(Path("/tmp/nonexistent_dir_12345"))
        assert result["LAST_ISSUE_ID"] is None
        assert result["LAST_ISSUE_STATE"] is None
        assert result["LAST_UPDATED_DATETIME"] is None


class TestHandleSessionStart(TestCase):
    @patch("crabber.functions.GitHubClient")
    def test_no_config_returns_empty(self, mock_client_cls):
        input_data = HookInput(session_id="test", cwd="/tmp/no_config_here_xyz", hook_event_name="SessionStart")
        output, exit_code = handle_session_start(input_data)
        assert output == ""
        assert exit_code == 0

    @patch("crabber.functions.GitHubClient")
    @patch("crabber.functions.parse_project_state")
    @patch("crabber.functions.load_project_config")
    def test_existing_issue_with_update(self, mock_load_config, mock_parse_state, mock_client_cls):
        mock_load_config.return_value = GithubProjectConfig(**SAMPLE_CONFIG)
        mock_parse_state.return_value = {
            "LAST_ISSUE_ID": "https://github.com/org/repo/issues/10",
            "LAST_ISSUE_STATE": "ON_GOING",
            "LAST_UPDATED_DATETIME": "2025-01-01T00:00:00Z",
        }
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_issue_details.return_value = {
            "title": "Fix the bug",
            "body": "There is a bug in the login flow",
            "updatedAt": "2025-06-01T00:00:00Z",
            "comments": {"nodes": [{"body": "Please also fix the signup flow"}]},
        }

        input_data = HookInput(session_id="test", cwd="/tmp/test", hook_event_name="SessionStart")
        output, exit_code = handle_session_start(input_data)

        assert exit_code == 0
        assert "Fix the bug" in output
        assert "There is a bug in the login flow" in output
        assert "Please also fix the signup flow" in output

    @patch("crabber.functions.GitHubClient")
    @patch("crabber.functions.parse_project_state")
    @patch("crabber.functions.load_project_config")
    def test_no_issue_fetches_from_column(self, mock_load_config, mock_parse_state, mock_client_cls):
        mock_load_config.return_value = GithubProjectConfig(**SAMPLE_CONFIG)
        mock_parse_state.return_value = {
            "LAST_ISSUE_ID": None,
            "LAST_ISSUE_STATE": None,
            "LAST_UPDATED_DATETIME": None,
        }
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_items_for_column.return_value = [
            ProjectItem(
                status="Awaiting",
                assignees=["testuser"],
                content=ProjectItemContent(
                    number=5,
                    title="New feature request",
                    body="Please add dark mode",
                    url="https://github.com/org/repo/issues/5",
                    owner="org",
                    repo="repo",
                ),
            )
        ]

        input_data = HookInput(session_id="test", cwd="/tmp/test", hook_event_name="SessionStart")
        output, exit_code = handle_session_start(input_data)

        assert exit_code == 0
        assert "New feature request" in output
        assert "Please add dark mode" in output

    @patch("crabber.functions.GitHubClient")
    @patch("crabber.functions.parse_project_state")
    @patch("crabber.functions.load_project_config")
    def test_existing_issue_no_update(self, mock_load_config, mock_parse_state, mock_client_cls):
        mock_load_config.return_value = GithubProjectConfig(**SAMPLE_CONFIG)
        mock_parse_state.return_value = {
            "LAST_ISSUE_ID": "https://github.com/org/repo/issues/10",
            "LAST_ISSUE_STATE": "ON_GOING",
            "LAST_UPDATED_DATETIME": "2025-12-01T00:00:00Z",
        }
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.get_issue_details.return_value = {
            "title": "Fix the bug",
            "body": "Body text",
            "updatedAt": "2025-06-01T00:00:00Z",
            "comments": {"nodes": []},
        }

        input_data = HookInput(session_id="test", cwd="/tmp/test", hook_event_name="SessionStart")
        output, exit_code = handle_session_start(input_data)

        assert exit_code == 0
        assert output == ""


class TestHandleNotification(TestCase):
    @patch("crabber.functions.GitHubClient")
    @patch("crabber.functions.parse_project_state")
    @patch("crabber.functions.load_project_config")
    def test_posts_comment(self, mock_load_config, mock_parse_state, mock_client_cls):
        mock_load_config.return_value = GithubProjectConfig(**SAMPLE_CONFIG)
        mock_parse_state.return_value = {
            "LAST_ISSUE_ID": "https://github.com/org/repo/issues/10",
            "LAST_ISSUE_STATE": "ON_GOING",
            "LAST_UPDATED_DATETIME": None,
        }
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        input_data = NotificationHookInput(
            session_id="test",
            cwd="/tmp/test",
            hook_event_name="Notification",
            title="Test Title",
            message="Test Message",
        )
        output, exit_code = handle_notification(input_data)

        assert exit_code == 0
        mock_client.post_issue_comment.assert_called_once()
        call_args = mock_client.post_issue_comment.call_args
        comment_body = call_args[0][3]
        assert "Test Message: Test Title" in comment_body

    @patch("crabber.functions.GitHubClient")
    def test_no_config_skips(self, mock_client_cls):
        input_data = NotificationHookInput(
            session_id="test",
            cwd="/tmp/no_config_xyz",
            hook_event_name="Notification",
            title="Title",
            message="Msg",
        )
        output, exit_code = handle_notification(input_data)
        assert exit_code == 0
        assert output == ""


class TestHandleStop(TestCase):
    @patch("crabber.functions._spawn_kill_process")
    @patch("crabber.functions.GitHubClient")
    @patch("crabber.functions.parse_project_state")
    @patch("crabber.functions.load_project_config")
    def test_posts_stop_comment_and_spawns_kill(self, mock_load_config, mock_parse_state, mock_client_cls, mock_spawn):
        mock_load_config.return_value = GithubProjectConfig(**SAMPLE_CONFIG)
        mock_parse_state.return_value = {
            "LAST_ISSUE_ID": "https://github.com/org/repo/issues/10",
            "LAST_ISSUE_STATE": "ON_GOING",
            "LAST_UPDATED_DATETIME": None,
        }
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        input_data = StopHookInput(
            session_id="test",
            cwd="/tmp/test",
            hook_event_name="Stop",
            stopReason="user_request",
        )
        output, exit_code = handle_stop(input_data)

        assert exit_code == 0
        mock_client.post_issue_comment.assert_called_once()
        mock_spawn.assert_called_once()


PROJECT_URL = "https://github.com/orgs/my-org/projects/42"


class TestParseProjectUrl(TestCase):
    def test_parses_basic_url(self):
        result = _parse_project_url("https://github.com/orgs/kiconiaworks/projects/98")
        assert result == ("kiconiaworks", 98)

    def test_parses_url_with_views(self):
        result = _parse_project_url("https://github.com/orgs/kiconiaworks/projects/98/views/1")
        assert result == ("kiconiaworks", 98)

    def test_returns_none_for_invalid_url(self):
        assert _parse_project_url("https://github.com/user/repo") is None
        assert _parse_project_url("not-a-url") is None


class TestHandleInit(TestCase):
    @patch("builtins.input", side_effect=[PROJECT_URL, "myuser", "", "", "", "Y"])
    def test_writes_config_with_defaults(self, mock_input):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            handle_init(tmp_path)

            config_path = tmp_path / CONFIG_FILENAME
            assert config_path.is_file()
            data = json.loads(config_path.read_text())
            assert data["org_name"] == "my-org"
            assert data["project_id"] == 42
            assert data["assignee"] == "myuser"
            assert data["awaiting-task-column"] == "Awaiting"
            assert data["inprogress-task-column"] == "In Progress"
            assert data["in-review-task-column"] == "In Review"

    @patch(
        "builtins.input",
        side_effect=["https://github.com/orgs/other-org/projects/99", "devuser", "Todo", "Doing", "Done", "n"],
    )
    def test_writes_config_with_custom_columns(self, mock_input):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            handle_init(tmp_path)

            data = json.loads((tmp_path / CONFIG_FILENAME).read_text())
            assert data["org_name"] == "other-org"
            assert data["project_id"] == 99
            assert data["awaiting-task-column"] == "Todo"
            assert data["inprogress-task-column"] == "Doing"
            assert data["in-review-task-column"] == "Done"

    @patch("builtins.input", side_effect=[PROJECT_URL, "user", "", "", "", "Y"])
    def test_appends_to_existing_gitignore(self, mock_input):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            gitignore = tmp_path / ".gitignore"
            gitignore.write_text("*.pyc\n")

            handle_init(tmp_path)

            content = gitignore.read_text()
            assert "*.pyc" in content
            assert CONFIG_FILENAME in content

    @patch("builtins.input", side_effect=[PROJECT_URL, "user", "", "", "", "Y"])
    def test_creates_gitignore_when_missing(self, mock_input):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            handle_init(tmp_path)

            gitignore = tmp_path / ".gitignore"
            assert gitignore.is_file()
            assert CONFIG_FILENAME in gitignore.read_text()

    @patch("builtins.input", side_effect=[PROJECT_URL, "user", "", "", "", "n"])
    def test_skips_gitignore_when_user_says_no(self, mock_input):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            handle_init(tmp_path)

            gitignore = tmp_path / ".gitignore"
            assert not gitignore.exists()

    @patch("builtins.input", side_effect=[PROJECT_URL, "user", "", "", "", "Y"])
    def test_skips_duplicate_gitignore_entry(self, mock_input):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            gitignore = tmp_path / ".gitignore"
            gitignore.write_text(f"{CONFIG_FILENAME}\n")

            handle_init(tmp_path)

            lines = gitignore.read_text().splitlines()
            assert lines.count(CONFIG_FILENAME) == 1

    @patch("builtins.input", side_effect=["bad-url", PROJECT_URL, "user", "", "", "", "n"])
    def test_retries_on_invalid_url(self, mock_input):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            handle_init(tmp_path)

            data = json.loads((tmp_path / CONFIG_FILENAME).read_text())
            assert data["org_name"] == "my-org"
            assert data["project_id"] == 42
