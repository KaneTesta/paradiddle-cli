import contextlib
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cli import run_session


class RestartTests(unittest.TestCase):
    @patch("cli.sys.stdin.isatty", return_value=True)
    @patch("cli.main", side_effect=[0, 0])
    def test_enter_starts_fresh_search_without_reusing_arguments(self, main, tty):
        with patch("builtins.input", side_effect=["", "q"]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_session(["--artist", "Turnstile", "--all"]), 0)
        self.assertEqual(main.call_args_list, [call(["--artist", "Turnstile", "--all"]), call([])])

    @patch("cli.sys.stdin.isatty", return_value=False)
    @patch("cli.main", return_value=1)
    def test_piped_commands_do_not_prompt(self, main, tty):
        with patch("builtins.input", side_effect=AssertionError("Unexpected prompt")):
            self.assertEqual(run_session(["--song", "Example"]), 1)
        main.assert_called_once()

    @patch("cli.sys.stdin.isatty", return_value=True)
    @patch("cli.main", return_value=0)
    def test_list_commands_do_not_prompt(self, main, tty):
        with patch("builtins.input", side_effect=AssertionError("Unexpected prompt")):
            self.assertEqual(run_session(["--artist", "Turnstile", "--list"]), 0)

    @patch("cli.sys.stdin.isatty", return_value=True)
    @patch("cli.main", side_effect=[ValueError("Bad chart"), 0])
    def test_can_restart_after_error(self, main, tty):
        with patch("builtins.input", side_effect=["", "Q"]), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(run_session([]), 0)

    @patch("cli.sys.stdin.isatty", return_value=True)
    @patch("cli.main", return_value=0)
    def test_unknown_shortcut_reprompts(self, main, tty):
        with patch("builtins.input", side_effect=["oops", "q"]), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_session([]), 0)
        main.assert_called_once()
