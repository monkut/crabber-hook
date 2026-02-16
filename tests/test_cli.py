import json
from unittest import TestCase
from unittest.mock import patch

from crabber.cli import dispatch


class TestDispatch(TestCase):
    @patch("crabber.cli.handle_session_start", return_value=("session output", 0))
    def test_session_start_dispatch(self, mock_handler):
        stdin_data = json.dumps(
            {
                "hook_event_name": "SessionStart",
                "session_id": "test-123",
                "cwd": "/tmp/test",
            }
        )

        output, exit_code = dispatch(stdin_data)

        mock_handler.assert_called_once()
        assert output == "session output"
        assert exit_code == 0

    @patch("crabber.cli.handle_notification", return_value=("", 0))
    def test_notification_dispatch(self, mock_handler):
        stdin_data = json.dumps(
            {
                "hook_event_name": "Notification",
                "session_id": "test-123",
                "cwd": "/tmp/test",
                "title": "Alert",
                "message": "Something happened",
            }
        )

        output, exit_code = dispatch(stdin_data)

        mock_handler.assert_called_once()
        assert exit_code == 0

    @patch("crabber.cli.handle_stop", return_value=("", 0))
    def test_stop_dispatch(self, mock_handler):
        stdin_data = json.dumps(
            {
                "hook_event_name": "Stop",
                "session_id": "test-123",
                "cwd": "/tmp/test",
                "stopReason": "user_request",
            }
        )

        output, exit_code = dispatch(stdin_data)

        mock_handler.assert_called_once()
        assert exit_code == 0

    def test_empty_stdin_returns_zero(self):
        output, exit_code = dispatch("")
        assert output == ""
        assert exit_code == 0

    def test_unknown_hook_returns_zero(self):
        stdin_data = json.dumps(
            {
                "hook_event_name": "UnknownHook",
                "session_id": "test-123",
                "cwd": "/tmp/test",
            }
        )

        output, exit_code = dispatch(stdin_data)

        assert output == ""
        assert exit_code == 0

    def test_invalid_json_returns_one(self):
        output, exit_code = dispatch("not json {")
        assert exit_code == 1

    @patch("crabber.cli.handle_session_start", return_value=("", 0))
    def test_no_output_returns_empty(self, mock_handler):
        stdin_data = json.dumps(
            {
                "hook_event_name": "SessionStart",
                "session_id": "test-123",
                "cwd": "/tmp/test",
            }
        )

        output, exit_code = dispatch(stdin_data)

        assert output == ""
        assert exit_code == 0
