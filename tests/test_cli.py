from argparse import Namespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from crabber.cli import build_parser, cmd_init, cmd_notification, cmd_session_start, cmd_stop
from crabber.definitions import HookInput, NotificationHookInput, StopHookInput


class TestBuildParser(TestCase):
    def test_session_start_command(self):
        parser = build_parser()
        args = parser.parse_args(["session-start"])
        assert args.command == "session-start"
        assert args.func == cmd_session_start

    def test_notification_command(self):
        parser = build_parser()
        args = parser.parse_args(["notification"])
        assert args.command == "notification"
        assert args.func == cmd_notification

    def test_stop_command(self):
        parser = build_parser()
        args = parser.parse_args(["stop"])
        assert args.command == "stop"
        assert args.func == cmd_stop

    def test_init_command(self):
        parser = build_parser()
        args = parser.parse_args(["init"])
        assert args.command == "init"
        assert args.func == cmd_init
        assert args.output_dir == "."

    def test_init_command_with_output_dir(self):
        parser = build_parser()
        args = parser.parse_args(["init", "--output-dir", "/tmp/mydir"])
        assert args.output_dir == "/tmp/mydir"

    def test_no_command_raises(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([])


@patch("crabber.cli._require_github_token", return_value=True)
class TestCmdSessionStart(TestCase):
    @patch("crabber.cli._make_handler")
    @patch("crabber.cli._read_and_parse", return_value=HookInput(session_id="test-123", cwd="/tmp/test"))
    def test_dispatches_to_handler(self, mock_read, mock_make_handler, mock_token):
        mock_handler = MagicMock()
        mock_handler.handle_session_start.return_value = ("session output", 0)
        mock_make_handler.return_value = mock_handler

        with (
            patch("sys.stdout") as mock_stdout,
            self.assertRaises(SystemExit),
        ):
            cmd_session_start(Namespace())

        mock_handler.handle_session_start.assert_called_once()
        mock_stdout.write.assert_called_once_with("session output")

    @patch("crabber.cli._read_and_parse", side_effect=SystemExit(1))
    def test_empty_stdin_exits_one(self, mock_read, mock_token):
        with self.assertRaises(SystemExit) as ctx:
            cmd_session_start(Namespace())
        assert ctx.exception.code == 1

    @patch("crabber.cli._make_handler")
    @patch("crabber.cli._read_and_parse", return_value=HookInput(session_id="test-123", cwd="/tmp/test"))
    def test_no_output_doesnt_write(self, mock_read, mock_make_handler, mock_token):
        mock_handler = MagicMock()
        mock_handler.handle_session_start.return_value = ("", 0)
        mock_make_handler.return_value = mock_handler

        with (
            patch("sys.stdout") as mock_stdout,
            self.assertRaises(SystemExit),
        ):
            cmd_session_start(Namespace())

        mock_stdout.write.assert_not_called()


@patch("crabber.cli._require_github_token", return_value=True)
class TestCmdNotification(TestCase):
    @patch("crabber.cli._make_handler")
    @patch(
        "crabber.cli._read_and_parse",
        return_value=NotificationHookInput(
            session_id="test-123",
            cwd="/tmp/test",
            title="Alert",
            message="Something happened",
        ),
    )
    def test_dispatches_to_handler(self, mock_read, mock_make_handler, mock_token):
        mock_handler = MagicMock()
        mock_handler.handle_notification.return_value = ("Waiting on response.", 2)
        mock_make_handler.return_value = mock_handler

        with self.assertRaises(SystemExit) as ctx:
            cmd_notification(Namespace())

        mock_handler.handle_notification.assert_called_once()
        assert ctx.exception.code == 2

    @patch("crabber.cli._read_and_parse", side_effect=SystemExit(1))
    def test_empty_stdin_exits_one(self, mock_read, mock_token):
        with self.assertRaises(SystemExit) as ctx:
            cmd_notification(Namespace())
        assert ctx.exception.code == 1


@patch("crabber.cli._require_github_token", return_value=True)
class TestCmdStop(TestCase):
    @patch("crabber.cli._make_handler")
    @patch(
        "crabber.cli._read_and_parse",
        return_value=StopHookInput(
            session_id="test-123",
            cwd="/tmp/test",
            stopReason="user_request",
        ),
    )
    def test_dispatches_to_handler(self, mock_read, mock_make_handler, mock_token):
        mock_handler = MagicMock()
        mock_handler.handle_stop.return_value = ("", 0)
        mock_make_handler.return_value = mock_handler

        with self.assertRaises(SystemExit) as ctx:
            cmd_stop(Namespace())

        mock_handler.handle_stop.assert_called_once()
        assert ctx.exception.code == 0

    @patch("crabber.cli._read_and_parse", side_effect=SystemExit(1))
    def test_empty_stdin_exits_one(self, mock_read, mock_token):
        with self.assertRaises(SystemExit) as ctx:
            cmd_stop(Namespace())
        assert ctx.exception.code == 1


class TestCmdInit(TestCase):
    @patch("crabber.cli.handle_init")
    def test_dispatches_to_handle_init(self, mock_handle_init):
        args = Namespace(output_dir="/tmp/test")
        cmd_init(args)
        mock_handle_init.assert_called_once()
        call_args = mock_handle_init.call_args[0]
        assert str(call_args[0]) == "/tmp/test"
