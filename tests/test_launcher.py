"""A double-clicked console must retain results without blocking redirected runs."""

import unittest
from unittest.mock import patch

import Main


class LauncherTests(unittest.TestCase):
    def test_frozen_interactive_game_waits_before_closing(self):
        with patch.object(Main, "main"), patch.object(Main.sys, "frozen", True, create=True), \
             patch.object(Main.sys, "stdin") as stdin, patch("builtins.input", return_value="") as prompt:
            stdin.isatty.return_value = True
            self.assertEqual(Main.launch(), 0)
            prompt.assert_called_once_with("\nPress Enter to close the game window...")

    def test_frozen_game_with_redirected_input_exits_without_pause(self):
        with patch.object(Main, "main"), patch.object(Main.sys, "frozen", True, create=True), \
             patch.object(Main.sys, "stdin") as stdin, patch("builtins.input") as prompt:
            stdin.isatty.return_value = False
            self.assertEqual(Main.launch(), 0)
            prompt.assert_not_called()

    def test_source_game_does_not_add_an_exit_prompt(self):
        with patch.object(Main, "main"), patch.object(Main.sys, "frozen", False, create=True), \
             patch("builtins.input") as prompt:
            self.assertEqual(Main.launch(), 0)
            prompt.assert_not_called()

    def test_failure_is_visible_before_window_close_prompt(self):
        events = []
        with patch.object(Main, "main", side_effect=RuntimeError("launch failed")), \
             patch.object(Main.sys, "frozen", True, create=True), \
             patch.object(Main.sys, "stdin") as stdin, \
             patch.object(Main.traceback, "print_exc", side_effect=lambda: events.append("error")), \
             patch("builtins.input", side_effect=lambda _: events.append("pause")):
            stdin.isatty.return_value = True
            self.assertEqual(Main.launch(), 1)
        self.assertEqual(events, ["error", "pause"])

    def test_closed_input_at_exit_does_not_raise_an_error(self):
        with patch.object(Main, "main"), patch.object(Main.sys, "frozen", True, create=True), \
             patch.object(Main.sys, "stdin") as stdin, patch("builtins.input", side_effect=EOFError):
            stdin.isatty.return_value = True
            self.assertEqual(Main.launch(), 0)


if __name__ == "__main__":
    unittest.main()
