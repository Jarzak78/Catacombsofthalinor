"""Attributions remain readable without changing an adventure or requiring its cwd."""

from pathlib import Path
import io
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from actions import Action
from credits import credits_lines, credits_text
from game import Game
from room import Enemy
import Main


class CreditsTests(unittest.TestCase):
    def test_credits_are_free_in_combat_the_shop_and_after_the_adventure(self):
        game = Game(seed=7)
        game.room.enemy = Enemy("Practice foe", 20, 20, 12, 3, (1, 6), 1, 50, 3)
        game.begin_encounter()
        for scene in ("combat", "shop", "over"):
            with self.subTest(scene=scene):
                game.in_shop = scene == "shop"
                game.quit_requested = scene == "over"
                before, rng_before = game.get_state(), game.rng.getstate()
                for command in ("credits", "licenses"):
                    self.assertEqual(game.handle_command(command), credits_lines())
                    self.assertEqual(game.perform(Action(command)), credits_lines())
                self.assertEqual(game.get_state(), before)
                self.assertEqual(game.rng.getstate(), rng_before)

    def test_terminal_credits_work_before_creation_from_an_unrelated_folder(self):
        entry = Path(__file__).resolve().parents[1] / "Main.py"
        with TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, str(entry), "--credits"],
                                    cwd=folder, input="", text=True,
                                    capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout.strip(), credits_text())
        self.assertIn("System Reference Document", result.stdout)
        self.assertIn("https://creativecommons.org/licenses/by/4.0/legalcode", result.stdout)
        self.assertNotIn("Choose your adventurer", result.stdout)

    def test_packaged_windows_play_requires_explicit_runtime_agreement(self):
        for terminal in (False, True):
            with self.subTest(interactive=terminal), \
                 patch.object(Main, "runtime_terms_required", return_value=True), \
                 patch.object(sys, "argv", ["Main.py", "--quick-start"]), \
                 patch.object(sys, "stdin") as stdin, \
                 patch("builtins.input", return_value="decline"), \
                 patch.object(Main, "Game") as game, \
                 patch("sys.stdout", new_callable=io.StringIO):
                stdin.isatty.return_value = terminal
                Main.main()
                game.assert_not_called()

    def test_credits_and_terms_are_available_without_acceptance(self):
        for option, expected in (("--credits", "System Reference Document"),
                                 ("--runtime-terms", "MICROSOFT RUNTIME TERMS")):
            with self.subTest(option=option), \
                 patch.object(Main, "runtime_terms_required", return_value=True), \
                 patch.object(sys, "argv", ["Main.py", option]), \
                 patch("builtins.input") as prompt, \
                 patch("sys.stdout", new_callable=io.StringIO) as output:
                Main.main()
                prompt.assert_not_called()
                self.assertIn(expected, output.getvalue())


if __name__ == "__main__":
    unittest.main()
