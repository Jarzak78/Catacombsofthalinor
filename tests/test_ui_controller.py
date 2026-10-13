"""Desktop flow preserves game rules, one reroll, and map secrecy."""

import copy
import json
import random
import unittest
from unittest.mock import Mock, patch

from character_creation import ABILITY_NAMES
from equipment import make_equipment
from game import Game
from loot_library import Loot
from player import Player
from ui_controller import DesktopSession, minimap_data


class DesktopSessionTests(unittest.TestCase):
    def creation(self, class_id="fighter"):
        session = DesktopSession(seed=7)
        session.begin_creation()
        session.choose_class(class_id)
        session.stat_rng = Mock(wraps=random.Random(7))
        return session

    def adventure(self, class_id="fighter"):
        session = self.creation(class_id)
        session.roll_stats()
        session.accept_character()
        session.enter_dungeon()
        return session

    def test_title_and_creation_wait_for_roll_button(self):
        session = DesktopSession(seed=7)
        session.stat_rng = Mock(wraps=random.Random(7))
        self.assertEqual(session.snapshot()["scene"], "title")
        session.begin_creation()
        session.choose_class("wizard")
        for _ in range(3):
            state = session.snapshot()
            self.assertIsNone(state["rolls"])
            self.assertIsNone(state["preview"])
        session.stat_rng.randint.assert_not_called()

    def test_initial_roll_uses_24_dice_and_only_one_reroll_is_allowed(self):
        session = self.creation()
        rolls = session.roll_stats()
        self.assertEqual(session.stat_rng.randint.call_count, 24)
        self.assertEqual(tuple(roll.stat for roll in rolls), ABILITY_NAMES)
        for roll in rolls:
            self.assertEqual(roll.dropped, min(roll.dice))
            self.assertEqual(roll.total, sum(roll.dice) - min(roll.dice))
        with self.assertRaisesRegex(ValueError, "already rolled"):
            session.roll_stats()
        self.assertEqual(session.stat_rng.randint.call_count, 24)
        replacement = session.reroll_stats()
        self.assertEqual(session.stat_rng.randint.call_count, 48)
        self.assertFalse(session.snapshot()["reroll_available"])
        with self.assertRaisesRegex(ValueError, "one reroll"):
            session.reroll_stats()
        self.assertEqual(session.stat_rng.randint.call_count, 48)
        self.assertEqual(session.rolls, replacement)

    def test_back_and_class_changes_cannot_grant_extra_rolls(self):
        session = self.creation()
        session.roll_stats()
        rolls = session.reroll_stats()
        session.show_title()
        session.begin_creation()
        session.choose_class("rouge")
        self.assertEqual(session.class_id, "rogue")
        self.assertEqual(session.rolls, rolls)
        self.assertTrue(session.reroll_used)
        with self.assertRaises(ValueError):
            session.reroll_stats()
        with self.assertRaises(ValueError):
            session.roll_stats()
        self.assertEqual(session.stat_rng.randint.call_count, 48)

    def test_invalid_creation_transitions_do_not_roll(self):
        session = self.creation()
        for operation in (session.reroll_stats, session.accept_character, session.enter_dungeon):
            with self.assertRaises(ValueError):
                operation()
        with self.assertRaises(ValueError):
            session.choose_class("paladin")
        self.assertEqual(session.class_id, "fighter")
        session.stat_rng.randint.assert_not_called()
        session.show_title()
        for operation in (session.roll_stats, session.reroll_stats, session.accept_character):
            with self.assertRaises(ValueError):
                operation()
        session.stat_rng.randint.assert_not_called()

    def test_all_classes_use_rolled_scores_to_derive_starting_hp(self):
        for class_id, expected_hp in (("warrior", 12), ("rouge", 10), ("wizard", 8)):
            with self.subTest(class_id=class_id):
                session = self.creation(class_id)
                session.stat_rng.randint.side_effect = [6, 5, 4, 1] * 6
                session.set_name("  Tarin  ")
                session.roll_stats()
                preview = session.snapshot()["preview"]
                player = session.accept_character()
                self.assertEqual(player.name, "Tarin")
                self.assertEqual(player.max_hp, expected_hp)
                self.assertEqual({stat: getattr(player, stat) for stat in ABILITY_NAMES},
                                 dict.fromkeys(ABILITY_NAMES, 15))
                self.assertEqual(preview["armor_class"], player.armor_class)
                self.assertEqual(preview["attack_bonus"], player.attack_bonus)

    def test_acceptance_locks_scores_class_and_name_without_rolling(self):
        session = self.creation()
        session.roll_stats()
        player = session.accept_character()
        self.assertIs(session.accept_character(), player)
        for operation in (session.roll_stats, session.reroll_stats,
                          lambda: session.choose_class("wizard"),
                          lambda: session.set_name("Another name")):
            with self.assertRaisesRegex(ValueError, "accepted"):
                operation()
        self.assertEqual(session.stat_rng.randint.call_count, 24)
        self.assertFalse(session.snapshot()["reroll_available"])

    def test_class_change_preserves_scores_and_updates_preview(self):
        session = self.creation()
        session.roll_stats()
        before = session.snapshot()
        session.choose_class("wizard")
        after = session.snapshot()
        self.assertEqual(before["rolls"], after["rolls"])
        self.assertEqual(after["preview"]["class_id"], "wizard")
        self.assertEqual(after["preview"]["max_hp"],
                         max(1, 6 + (next(roll.total for roll in session.rolls
                                           if roll.stat == "constitution") - 10) // 2))
        self.assertIsNotNone(after["preview"]["spell_save_dc"])
        self.assertEqual(session.stat_rng.randint.call_count, 24)

    def test_entering_constructs_one_game_and_cannot_restart_it(self):
        session = self.creation("wizard")
        session.roll_stats()
        player = session.accept_character()
        with patch("ui_controller.Game", wraps=Game) as constructor:
            messages = session.enter_dungeon()
            game = session.game
            self.assertIn("CATACOMBS OF THALINOR", messages)
            self.assertIs(game.player, player)
            self.assertEqual(session.scene, "dungeon")
            with self.assertRaisesRegex(ValueError, "already begun"):
                session.enter_dungeon()
            self.assertEqual(constructor.call_count, 1)
            self.assertIs(session.game, game)
        for operation in (session.show_title, session.begin_creation):
            with self.assertRaises(ValueError):
                operation()

    def test_stat_reroll_does_not_change_dungeon_generation(self):
        first = self.creation("rogue")
        second = self.creation("rogue")
        first.roll_stats()
        second.roll_stats()
        second.reroll_stats()
        for session in (first, second):
            session.accept_character()
            session.enter_dungeon()
        self.assertIsNot(first.stat_rng, first.game.rng)
        self.assertEqual(first.game.get_state()["rooms"], second.game.get_state()["rooms"])
        self.assertEqual(first.game.rng.getstate(), second.game.rng.getstate())

    def test_commands_use_same_engine_behavior_as_terminal(self):
        for class_id in ("fighter", "rogue", "wizard"):
            with self.subTest(class_id=class_id):
                session = self.adventure(class_id)
                reference = Game(player=copy.deepcopy(session.game.player), seed=7)
                commands = ["look", "skills", "inventory", "loot", "journal", "read", "map",
                            next(iter(session.game.room.exits)), "examine", "attack", "end"]
                for command in commands:
                    self.assertEqual(session.submit_command(command), reference.handle_command(command))
                    self.assertEqual(session.snapshot(), reference.get_state())

    def test_creation_and_game_snapshots_are_detached_and_read_only(self):
        session = self.creation("wizard")
        session.roll_stats()
        before = session.snapshot()
        dice_before = session.stat_rng.getstate()
        modified = session.snapshot()
        modified["rolls"][0]["dice"][0] = 99
        modified["rolls"][0]["total"] = 99
        modified["preview"]["hp"] = 99
        self.assertEqual(session.snapshot(), before)
        self.assertEqual(session.stat_rng.getstate(), dice_before)
        session.accept_character()
        session.enter_dungeon()
        before = session.snapshot()
        game_rng = session.game.rng.getstate()
        state = session.snapshot()
        state["player"]["name"] = "Changed"
        state["rooms"][0]["exits"].clear()
        self.assertEqual(session.snapshot(), before)
        self.assertEqual(session.game.rng.getstate(), game_rng)
        json.dumps(session.snapshot())

    def test_commands_before_start_are_rejected(self):
        session = DesktopSession()
        with self.assertRaisesRegex(ValueError, "Enter the dungeon"):
            session.submit_command("look")
        session.begin_creation()
        with self.assertRaises(ValueError):
            session.submit_command("look")


class MinimapTests(unittest.TestCase):
    def test_unknown_metadata_and_connections_are_not_exposed(self):
        state = {
            "scene": "dungeon", "position": [0, 0], "floor": 2, "theme": "Roots",
            "rooms": [
                {"position": [0, 0], "visited": True, "name": "Entrance",
                 "exits": {"east": [1, 0]}},
                {"position": [1, 0], "visited": False, "name": "SECRET NAME",
                 "description": "SECRET STORY", "enemy": {"hp": 5, "boss": True},
                 "loot": {"gold": 900}, "note": {"title": "SECRET NOTE"},
                 "exits": {"east": [2, 0]}},
                {"position": [2, 0], "visited": False},
            ],
        }
        before = copy.deepcopy(state)
        result = minimap_data(state)
        self.assertEqual(result["nodes"][1], {"x": 1, "y": 0, "visited": False, "marker": "?"})
        self.assertEqual(result["edges"], [{"start": [0, 0], "end": [1, 0]}])
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertNotIn("900", json.dumps(result))
        self.assertEqual(state, before)
        self.assertEqual((result["width"], result["height"]), (3, 1))

    def test_bidirectional_visited_passages_are_rendered_once(self):
        state = {
            "position": [0, 0], "rooms": [
                {"position": [1, 0], "visited": True, "exits": {"west": [0, 0]}},
                {"position": [0, 0], "visited": True, "exits": {"east": [1, 0]}},
            ],
        }
        self.assertEqual(minimap_data(state)["edges"], [{"start": [0, 0], "end": [1, 0]}])

    def test_room_markers_follow_enemy_treasure_note_priority(self):
        details = [
            ({"enemy": {"hp": 1, "boss": True}}, "B"),
            ({"enemy": {"hp": 1}, "loot": {"gold": 1}}, "E"),
            ({"enemy": {"hp": 0}, "loot": {"gold": 1}}, "$"),
            ({"loot": {"potions": 1}}, "$"),
            ({"loot": {"armor_name": "Runic leather"}}, "$"),
            ({"loot": {"items": [{"name": "Gem"}]}}, "$"),
            ({"loot": {"weapon_name": "Sword"}}, "$"),
            ({"loot": {"gold": 0}, "note": {"title": "Note"}}, "N"),
            ({"note": {"title": "Note"}, "note_collected": True}, "."),
            ({"loot": None}, "."),
        ]
        for room_details, expected in details:
            with self.subTest(room_details=room_details):
                room = {"position": [0, 0], "visited": True, **room_details}
                state = {"position": [9, 9], "rooms": [room]}
                self.assertEqual(minimap_data(state)["nodes"][0]["marker"], expected)
                state["position"] = [0, 0]
                self.assertEqual(minimap_data(state)["nodes"][0]["marker"], "@")

    def test_vendor_hides_floor_map(self):
        session = DesktopSessionTests().adventure()
        session.game.in_shop = True
        result = minimap_data(session.snapshot())
        self.assertFalse(result["visible"])
        self.assertEqual(result["label"], "The Lantern Between Worlds")
        self.assertEqual(result["nodes"], [])
        self.assertEqual(result["edges"], [])

    def test_equipment_only_cache_marks_a_visited_room_without_revealing_item_details(self):
        game = Game(seed=7)
        direction, position = next(iter(game.room.exits.items()))
        room = game.dungeon.get_room(position)
        room.enemy = None
        room.note = None
        room.visited = True
        room.loot = Loot(equipment=(make_equipment("longsword", 3),))
        before, rng_before = game.get_state(), game.rng.getstate()
        map_data = minimap_data(before)
        node = next(node for node in map_data["nodes"]
                    if (node["x"], node["y"]) == position)
        self.assertEqual(node["marker"], "$")
        self.assertNotIn("Longsword", json.dumps(map_data))
        self.assertNotIn("longsword", json.dumps(map_data))
        self.assertEqual(game.get_state(), before)
        self.assertEqual(game.rng.getstate(), rng_before)
        room.visited = False
        node = next(node for node in minimap_data(game.get_state())["nodes"]
                    if (node["x"], node["y"]) == position)
        self.assertEqual(node["marker"], "?")

    def test_live_engine_minimap_reads_do_not_advance_any_game_state(self):
        session = DesktopSessionTests().adventure()
        before = session.snapshot()
        rng_state = session.game.rng.getstate()
        first = minimap_data(before)
        for _ in range(4):
            self.assertEqual(minimap_data(session.snapshot()), first)
        self.assertEqual(session.snapshot(), before)
        self.assertEqual(session.game.rng.getstate(), rng_state)
        self.assertEqual((first["width"], first["height"]), (4, 3))
        self.assertEqual(sum(node["visited"] for node in first["nodes"]), 1)
        self.assertEqual(sum(node["marker"] == "?" for node in first["nodes"]), 11)


if __name__ == "__main__":
    unittest.main()
