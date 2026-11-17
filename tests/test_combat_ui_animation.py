"""Attack playback owns one cancelable display timer and never replays a turn."""

from collections import deque
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from combat_animation import FX_TAG
from desktop_ui import DungeonWindow
from dungeon_view import VIEW_TAG
from game import Game
from room import Enemy
from ui_controller import DesktopSession


class ExactRandom:
    def __init__(self, values):
        self.values = deque(values)
        self.calls = []

    def randint(self, low, high):
        if not self.values:
            raise AssertionError(f"Presentation requested an extra roll: {low}..{high}")
        value = self.values.popleft()
        if not low <= value <= high:
            raise AssertionError((low, high, value))
        self.calls.append((low, high, value))
        return value


class Scheduler:
    """Like Tk after(), with deliberately callable canceled/stale callbacks."""

    def __init__(self):
        self.pending = {}
        self.callbacks = {}
        self.cancelled = []
        self.next_id = 0
        self.high_water = 0

    def after(self, delay, callback):
        self.next_id += 1
        timer = f"after-{self.next_id}"
        self.pending[timer] = (delay, callback)
        self.callbacks[timer] = callback
        self.high_water = max(self.high_water, len(self.pending))
        return timer

    def after_cancel(self, timer):
        self.cancelled.append(timer)
        self.pending.pop(timer, None)

    def step(self):
        timer = next(iter(self.pending))
        _, callback = self.pending.pop(timer)
        callback()

    def drain(self):
        for _ in range(100):
            if not self.pending:
                return
            self.step()
        raise AssertionError("Playback scheduled an endless timer chain")


class Canvas:
    def __init__(self):
        self.deleted = []

    def delete(self, tag):
        self.deleted.append(tag)

    def winfo_width(self):
        return 750

    def winfo_height(self):
        return 300


def game_with_foe(values=(15, 2), level=1, guardian=False):
    game = Game(seed=7)
    game.player.level = level
    if guardian:
        game.position = game.dungeon.boss_position
    game.room.visited = True
    game.room.enemy = Enemy("Test sentinel", 100, 1 if guardian else 100,
                            12, 3, (1, 6), 1, 50, 7, boss=guardian)
    game.rng = ExactRandom(values)
    game.begin_turn()
    return game


class PlaybackTests(unittest.TestCase):
    def window(self, game=None):
        """Keep real UI methods and engine; replace only Tk and image painting."""
        game = game or game_with_foe()
        window = DungeonWindow.__new__(DungeonWindow)
        window.root = Scheduler()
        window.session = DesktopSession(seed=7)
        window.session.game, window.session.scene = game, "dungeon"
        window.seed, window.floors = 7, 5
        window.screen = "dungeon"
        window._torch_after_id = None
        window._attack_after_id = None
        window._attack_queue = []
        window._attack_event = None
        window._attack_frame = None
        window._attack_context = None
        window._attack_token = 0
        window._attack_step = 0
        window.view_canvas = Canvas()
        window.view_state = {}
        window.view_facing = "north"
        window._view_location = None
        window._view_game = None
        window.turn_left_button, window.turn_right_button = Mock(), Mock()
        window.view_caption = Mock()
        window.command_entry = Mock()
        window.command_var = Mock()
        window.append_messages = Mock()
        window.history, window.history_index = [], 0
        window.frames = {name: Mock() for name in ("title", "creation", "dungeon")}
        window.refresh_dungeon = lambda: window.refresh_view(window.session.get_state())
        window.rendered = []

        def render(canvas, width, height, view, *, animation=None):
            window.rendered.append({"view": deepcopy(view), "frame": deepcopy(animation),
                                    "event_id": window._attack_event.get("id")
                                    if window._attack_event else None})

        painter = patch("desktop_ui.draw_dungeon_view", side_effect=render)
        painter.start()
        self.addCleanup(painter.stop)
        window.refresh_dungeon()
        return window

    def test_extra_attack_plays_both_events_in_order_with_only_one_timer(self):
        game = game_with_foe(values=(15, 2, 16, 3), level=5)
        window = self.window(game)
        window.send_command("attack")
        self.assertEqual(game.visual_sequence, 2)
        self.assertEqual(window._attack_event["id"], 1)
        self.assertEqual([event["id"] for event in window._attack_queue], [2])
        self.assertEqual(len(window.root.pending), 1)
        resolved_state, rng_calls = deepcopy(game.get_state()), list(game.rng.calls)
        window.root.drain()
        active = [item for item in window.rendered if item["event_id"] is not None]
        self.assertEqual([item["event_id"] for item in active], [1] * 9 + [2] * 9)
        self.assertEqual([item["frame"]["progress"] for item in active[:9]],
                         [i / 8 for i in range(9)])
        self.assertEqual(window.root.high_water, 1)
        self.assertIsNone(window._attack_after_id)
        self.assertIsNone(window._attack_event)
        self.assertEqual(window._attack_queue, [])
        self.assertEqual(game.get_state(), resolved_state)
        self.assertEqual(game.rng.calls, rng_calls)

    def test_replacement_attack_cancels_old_timer_and_rejects_stale_callback(self):
        game = game_with_foe(values=(15, 2, 16, 3))
        window = self.window(game)
        window.send_command("attack")
        old_timer = window._attack_after_id
        stale = window.root.callbacks[old_timer]
        game.begin_turn()
        window.send_command("attack")
        new_timer = window._attack_after_id
        self.assertIn(old_timer, window.root.cancelled)
        self.assertNotEqual(old_timer, new_timer)
        self.assertEqual(window._attack_event["id"], 2)
        rendered_count = len(window.rendered)
        stale()
        self.assertEqual(len(window.rendered), rendered_count)
        self.assertEqual(window._attack_after_id, new_timer)
        self.assertEqual(list(window.root.pending), [new_timer])
        window.root.drain()
        self.assertEqual(window.root.high_water, 1)

    def test_information_and_invalid_commands_never_replay_previous_attack(self):
        game = game_with_foe()
        window = self.window(game)
        window.send_command("attack")
        window.root.drain()
        sequence, rng_calls = game.visual_sequence, list(game.rng.calls)
        for command in ("look", "help", "stats", "inventory", "not-a-command", "cast impossible"):
            with self.subTest(command=command):
                before = len(window.rendered)
                window.send_command(command)
                self.assertFalse(window.root.pending)
                self.assertIsNone(window._attack_event)
                self.assertTrue(all(item["frame"] is None for item in window.rendered[before:]))
                self.assertEqual(game.visual_sequence, sequence)
                self.assertEqual(game.rng.calls, rng_calls)

    def test_information_during_playback_cancels_overlay_and_queued_hit(self):
        window = self.window(game_with_foe(values=(15, 2, 16, 3), level=5))
        window.send_command("attack")
        stale = window.root.callbacks[window._attack_after_id]
        window.send_command("look")
        self.assertFalse(window.root.pending)
        self.assertEqual(window._attack_queue, [])
        self.assertIsNone(window._attack_event)
        self.assertIsNone(window._attack_frame)
        self.assertIn(FX_TAG, window.view_canvas.deleted)
        before = len(window.rendered)
        stale()
        self.assertEqual(len(window.rendered), before)

    def test_refresh_invalidates_animation_on_room_floor_shop_or_game_change(self):
        for change in ("room", "floor", "shop", "game"):
            with self.subTest(change=change):
                window = self.window()
                window.send_command("attack")
                stale = window.root.callbacks[window._attack_after_id]
                state = window.session.get_state()
                if change == "room":
                    state["position"] = [99, 99]
                elif change == "floor":
                    state["floor"] += 1
                elif change == "shop":
                    state["scene"] = "shop"
                else:
                    window.session.game = Game(seed=8)
                    state = window.session.get_state()
                window.refresh_view(state)
                self.assertFalse(window.root.pending)
                self.assertIsNone(window._attack_context)
                self.assertIsNone(window.rendered[-1]["frame"])
                before = len(window.rendered)
                stale()
                self.assertEqual(len(window.rendered), before)

    def test_timer_checks_context_even_if_no_refresh_has_run(self):
        for change in ("screen", "location", "game"):
            with self.subTest(change=change):
                window = self.window()
                window.send_command("attack")
                if change == "screen":
                    window.screen = "creation"
                elif change == "location":
                    window._view_location = (2, "dungeon", window._view_location[2])
                else:
                    window.session.game = Game(seed=8)
                window.root.step()
                self.assertFalse(window.root.pending)
                self.assertIsNone(window._attack_event)
                self.assertIsNone(window.rendered[-1]["frame"])

    def test_defeated_guardian_is_visible_until_collapse_finishes_then_portal_returns(self):
        game = game_with_foe(values=(15, 8), guardian=True)
        window = self.window(game)
        window.send_command("attack")
        self.assertIsNone(game.enemy)
        self.assertIsNone(window.view_state["enemy"])
        self.assertTrue(window.view_state["portal"])
        final_view = deepcopy(window.view_state)
        window.root.drain()
        active = [item for item in window.rendered if item["frame"] is not None]
        self.assertTrue(active)
        for item in active:
            self.assertEqual(item["view"]["enemy"]["name"], "Test sentinel")
            self.assertTrue(item["view"]["in_combat"])
            self.assertFalse(item["view"]["portal"])
            self.assertFalse(item["view"]["loot"])
            self.assertFalse(item["view"]["note"])
        self.assertEqual(active[-1]["frame"]["enemy_opacity"], 0)
        self.assertIsNone(window.rendered[-1]["frame"])
        self.assertEqual(window.rendered[-1]["view"], final_view)
        self.assertEqual(window.view_state, final_view)

    def test_leaving_screen_or_destroying_window_stops_playback(self):
        for action in ("leave", "destroy"):
            with self.subTest(action=action):
                window = self.window()
                window.send_command("attack")
                if action == "leave":
                    window.show_screen("creation")
                    self.assertEqual(window.screen, "creation")
                else:
                    window._on_destroy(SimpleNamespace(widget=window.root))
                self.assertFalse(window.root.pending)
                self.assertIsNone(window._attack_event)
                self.assertIsNone(window._attack_frame)
                self.assertIn(FX_TAG, window.view_canvas.deleted)

    def test_new_adventure_discards_old_events_timer_and_view(self):
        window = self.window()
        window.send_command("attack")
        stale = window.root.callbacks[window._attack_after_id]
        window.session.game.player.hp = 0
        window.name_var, window.class_var, window.creation_message = Mock(), Mock(), Mock()
        window.terminal = Mock()
        window.refresh_creation = Mock()
        window.show_screen = Mock()
        new_session = DesktopSession(seed=7)
        with patch("desktop_ui.DesktopSession", return_value=new_session):
            window.new_adventure()
        self.assertIs(window.session, new_session)
        self.assertIsNone(window.session.game)
        self.assertFalse(window.root.pending)
        self.assertIsNone(window._attack_event)
        self.assertIsNone(window._attack_context)
        self.assertIsNone(window._view_location)
        self.assertIsNone(window._view_game)
        self.assertEqual(window.view_state, {})
        self.assertEqual(window.history, [])
        self.assertIn(VIEW_TAG, window.view_canvas.deleted)
        window.show_screen.assert_called_once_with("title")
        before = len(window.rendered)
        stale()
        self.assertEqual(len(window.rendered), before)


if __name__ == "__main__":
    unittest.main()
