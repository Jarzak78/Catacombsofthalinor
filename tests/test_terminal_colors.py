"""Color adapters preserve engine text and keep redirected output parseable."""

import io
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from floor_lore import LORE
from game import Game
from loot_flavor import discovery_description, preview_description
from presentation import (
    TAG_COLORS, classify_message, enable_terminal_colors, format_message, print_messages,
)
from room import Room


class InteractiveOutput(io.StringIO):
    def isatty(self):
        return True


class TerminalColorTests(unittest.TestCase):
    def test_every_authored_floor_and_container_description_is_green(self):
        for floor, lore in enumerate(LORE, 1):
            for text in (lore.arrival, lore.revelation):
                with self.subTest(floor=floor, text=text):
                    self.assertEqual(classify_message(text), "room")
            for name, description in (lore.entrance, lore.sanctum, *lore.rooms):
                room = Room((0, 0), name, description, {})
                for text in (name, description, discovery_description(room, floor),
                             preview_description(room, floor)):
                    with self.subTest(floor=floor, text=text):
                        self.assertEqual(classify_message(text), "room")
        self.assertEqual(TAG_COLORS["room"], "#81d98e")

    def test_loot_clues_keep_room_color_without_revealing_the_reward(self):
        self.assertEqual(classify_message(
            "Among the dusty belongings, you glimpse a gleaming blade. Type 'loot' to search them."
        ), "room")

    def test_item_examination_labels_and_compact_rows_are_light_blue(self):
        for line in ("Description: A keen, balanced steel blade.", "Item: Longsword +1",
                     "Damage dice: 1d8 + 1", "Slot: Helmet", "Rarity: Rare",
                     "Protection: +2 AC", "Buff: Strength +1",
                     "longsword_1: Longsword +1 — 65 gold", "boots_1: Boots +1 x1 | equipped"):
            with self.subTest(line=line):
                self.assertEqual(classify_message(line), "item")
        self.assertEqual(TAG_COLORS["item"], "#9ddcff")

    def test_dialogue_combat_healing_and_commands_have_distinct_roles(self):
        cases = {
            "Mira: Welcome, traveler. I am Mira.": "dialogue",
            "Crypt Rat hits you with 1d4 (3) for 4 damage.": "combat",
            "You miss Crypt Rat (d20 [8], total 12).": "combat",
            "Sneak Attack: 1d6 (5).": "combat",
            "Opening Hide: d20 [20] +7 = 27 vs DC 20.": "combat",
            "You drink a potion and regain 7 HP.": "healing",
            "Use 'examine <item id>' to learn more.": "command",
            "> look": "command",
            "Your guild badge is still bright; your first trial awaits below.": "log",
        }
        for line, expected in cases.items():
            with self.subTest(line=line):
                self.assertEqual(classify_message(line), expected)
        self.assertEqual(len({TAG_COLORS[role] for role in cases.values()}), len(set(cases.values())))

    def test_redirected_output_preserves_exact_text_without_ansi(self):
        output = io.StringIO()
        lines = [LORE[0].arrival, "Description: A finely worked helmet.", "", "Mira: Welcome."]
        print_messages(lines, stream=output)
        self.assertEqual(output.getvalue(), "\n".join(lines) + "\n")
        self.assertNotIn("\033", output.getvalue())

    def test_multiline_messages_keep_line_specific_console_colors(self):
        output = InteractiveOutput()
        with patch("presentation.enable_terminal_colors", return_value=True):
            print_messages(["Mira: Welcome.\nDescription: A blue-glass vial."], stream=output)
        self.assertEqual(output.getvalue(),
                         "\033[95mMira: Welcome.\033[0m\n"
                         "\033[96mDescription: A blue-glass vial.\033[0m\n")

    def test_no_color_and_dumb_term_disable_interactive_ansi(self):
        output = InteractiveOutput()
        self.assertFalse(enable_terminal_colors(output, {"NO_COLOR": ""}))
        self.assertFalse(enable_terminal_colors(output, {"NO_COLOR": "1"}))
        with patch("presentation.os.name", "posix"):
            self.assertFalse(enable_terminal_colors(output, {"TERM": "dumb"}))
            self.assertTrue(enable_terminal_colors(output, {"TERM": "xterm"}))
        self.assertEqual(format_message("Description: A sword."), "Description: A sword.")
        self.assertEqual(format_message("", color=True), "")

    def test_windows_color_requires_successful_console_mode_change(self):
        output = InteractiveOutput()
        with patch("presentation.os.name", "nt"), patch("presentation._enable_windows_vt") as enable:
            enable.return_value = True
            self.assertTrue(enable_terminal_colors(output, {}))
            enable.assert_called_once_with(output)
            enable.return_value = False
            self.assertFalse(enable_terminal_colors(output, {}))
            enable.reset_mock()
            self.assertFalse(enable_terminal_colors(io.StringIO(), {}))
            self.assertFalse(enable_terminal_colors(output, {"NO_COLOR": ""}))
            enable.assert_not_called()

    def test_formatting_responses_never_changes_engine_state_or_rng(self):
        game = Game(seed=7)
        state = game.get_state()
        rng = game.rng.getstate()
        for lines in (game.introduction(), game.describe_room(), game.inventory()):
            self.assertTrue(all("\033" not in line for line in lines))
            for line in lines:
                format_message(line, color=True)
                classify_message(line)
            print_messages(lines, io.StringIO())
        self.assertEqual(game.get_state(), state)
        self.assertEqual(game.rng.getstate(), rng)

    def test_real_terminal_launcher_keeps_redirected_transcript_plain(self):
        checkout = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, str(checkout / "Main.py"), "--quick-start", "--seed", "7"],
            input="look\nquit\n", text=True, capture_output=True, timeout=15, cwd=checkout,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CATACOMBS OF THALINOR", result.stdout)
        self.assertIn(LORE[0].arrival, result.stdout)
        self.assertNotIn("\033", result.stdout)
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
