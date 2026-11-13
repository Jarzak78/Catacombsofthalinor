"""Camera controls change presentation only, including failed moves and resets."""

import copy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from desktop_ui import DungeonWindow
from game import Game


class FirstPersonCameraTests(unittest.TestCase):
    def window(self):
        window = object.__new__(DungeonWindow)
        window.session = SimpleNamespace(game=Game(seed=7))
        window.session.get_state = lambda: window.session.game.get_state()
        window.view_facing = "north"
        window.view_state = {}
        window._view_location = None
        window._view_game = None
        window.view_caption = Mock()
        window.command_entry = Mock()
        window.turn_left_button = Mock()
        window.turn_right_button = Mock()
        window.draw_view = Mock()
        window.refresh_view(window.session.get_state())
        return window

    def test_turns_are_free_and_do_not_change_the_engine_or_rng(self):
        window = self.window()
        game = window.session.game
        before, rng = game.get_state(), game.rng.getstate()
        for steps, expected in ((1, "east"), (1, "south"), (-1, "east"), (-2, "west")):
            window.turn_view(steps)
            self.assertEqual(window.view_facing, expected)
            self.assertEqual(window.view_state["facing"], expected)
        self.assertEqual(game.get_state(), before)
        self.assertEqual(game.rng.getstate(), rng)
        window.command_entry.focus_set.assert_called()

    def test_actual_movement_faces_travel_and_invalid_commands_do_not_rotate(self):
        window = self.window()
        game = window.session.game
        direction = next(iter(game.room.exits))
        game.handle_command(direction)
        before, rng = game.get_state(), game.rng.getstate()
        window.refresh_view(before)
        self.assertEqual(window.view_facing, direction)
        self.assertEqual(game.get_state(), before)
        self.assertEqual(game.rng.getstate(), rng)
        window.turn_view(1)
        facing = window.view_facing
        game.handle_command("go nowhere")
        window.refresh_view(game.get_state())
        self.assertEqual(window.view_facing, facing)

    def test_new_floor_and_new_adventure_reset_facing_without_changing_snapshots(self):
        window = self.window()
        window.turn_view(1)
        changed = copy.deepcopy(window.session.get_state())
        changed["floor"] = 2
        original = copy.deepcopy(changed)
        window.refresh_view(changed)
        self.assertEqual(window.view_facing, "north")
        self.assertEqual(changed, original)
        window.view_facing = "west"
        window.session.game = Game(seed=42)
        window.refresh_view(window.session.get_state())
        self.assertEqual(window.view_facing, "north")
        self.assertIs(window._view_game, window.session.game)

    def test_sanctuary_does_not_show_a_dungeon_camera_or_reveal_its_foe(self):
        window = self.window()
        game = window.session.game
        game.in_shop = True
        before, rng = game.get_state(), game.rng.getstate()
        window.refresh_view(before)
        self.assertEqual(window.view_state["scene"], "shop")
        self.assertIsNone(window.view_state["enemy"])
        window.turn_left_button.configure.assert_called_with(state="disabled")
        window.turn_right_button.configure.assert_called_with(state="disabled")
        self.assertEqual(game.get_state(), before)
        self.assertEqual(game.rng.getstate(), rng)


if __name__ == "__main__":
    unittest.main()
