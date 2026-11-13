"""First-person drawings disclose only visible facts and never change a run."""

import copy
import json
import unittest

from equipment import make_equipment
from game import Game
from loot_library import Loot
from room import Enemy
from ui_controller import DesktopSession
from view_model import first_person_data


class FirstPersonViewTests(unittest.TestCase):
    def state(self):
        return {
            "scene": "dungeon", "floor": 2, "theme": "Rootbound Depths",
            "position": [0, 0], "player": {"class_id": "rogue", "hp": 10, "dead": False},
            "encounter": {"hidden": False}, "portal_open": False, "portal_position": None,
            "over": False, "won": False,
            "rooms": [{"position": [0, 0], "visited": True, "name": "Known chamber",
                       "exits": {"north": [0, 1], "west": [1, 0]},
                       "enemy": None, "loot": None, "note": None,
                       "note_collected": False}],
        }

    def test_exits_rotate_relative_to_all_four_facings(self):
        expected = {
            "north": {"front": True, "left": True, "right": False, "back": False},
            "east": {"front": False, "left": True, "right": False, "back": True},
            "south": {"front": False, "left": False, "right": True, "back": True},
            "west": {"front": True, "left": False, "right": True, "back": False},
        }
        for facing, exits in expected.items():
            with self.subTest(facing=facing):
                view = first_person_data(self.state(), facing)
                self.assertEqual(view["facing"], facing)
                self.assertEqual(view["exits"], exits)

    def test_facing_normalization_and_fallback_are_presentation_only(self):
        state = self.state()
        before = copy.deepcopy(state)
        self.assertEqual(first_person_data(state, " WEST ")["facing"], "west")
        for invalid in ("up", "", None, 42):
            with self.subTest(facing=invalid):
                self.assertEqual(first_person_data(state, invalid)["facing"], "north")
        self.assertEqual(state, before)

    def test_unvisited_current_room_metadata_is_ignored_even_if_supplied(self):
        state = self.state()
        state["rooms"][0].update(
            visited=False, name="SECRET ROOM", description="SECRET LORE",
            enemy={"name": "SECRET FOE", "hp": "malformed", "boss": True},
            loot={"gold": 98765}, note={"title": "SECRET NOTE"},
            exits={"east": [9, 9]})
        state.update(portal_open=True, portal_position=[0, 0])
        view = first_person_data(state)
        self.assertEqual(view["room_name"], "Unexplored chamber")
        self.assertEqual(view["exits"], dict.fromkeys(("front", "left", "right", "back"), False))
        self.assertFalse(any(view[key] for key in ("enemy", "loot", "note", "portal", "in_combat")))
        self.assertNotIn("SECRET", json.dumps(view))
        self.assertNotIn("98765", json.dumps(view))

    def test_neighbor_content_is_never_copied_even_if_already_explored(self):
        state = self.state()
        for visited in (False, True):
            state["rooms"].append({
                "position": [1, 0], "visited": visited, "name": "SECRET ADJACENT",
                "enemy": {"name": "SECRET NEIGHBOR", "hp": 777, "boss": True},
                "loot": {"gold": 98765}, "note": {"title": "SECRET DOCUMENT"},
                "exits": {"east": [99, 99]},
            })
        result = first_person_data(state)
        self.assertEqual(result["room_name"], "Known chamber")
        self.assertNotIn("SECRET", json.dumps(result))
        self.assertIsNone(result["enemy"])
        self.assertFalse(result["loot"])
        self.assertFalse(result["note"])

    def test_living_foe_hides_room_features_and_exposes_no_numeric_stats(self):
        state = self.state()
        state["rooms"][0].update(
            enemy={"name": "Rootcoil Viper", "hp": 241, "max_hp": 300,
                   "armor_class": 47, "attack_bonus": 36, "boss": True},
            loot={"weapon_name": "SECRET BLADE", "gold": 98765},
            note={"title": "SECRET NOTE"})
        state.update(portal_open=True, portal_position=[0, 0])
        view = first_person_data(state)
        self.assertEqual(view["enemy"], {"name": "Rootcoil Viper", "boss": True,
                                        "archetype": "serpent"})
        self.assertTrue(view["in_combat"])
        self.assertFalse(any(view[key] for key in ("loot", "note", "portal")))
        self.assertEqual(set(view["enemy"]), {"name", "boss", "archetype"})
        self.assertNotIn("SECRET", json.dumps(view))

    def test_after_combat_only_vague_feature_flags_are_revealed(self):
        state = self.state()
        state["rooms"][0].update(
            enemy={"name": "Defeated foe", "hp": 0},
            loot={"gold": 98765, "equipment": [{"id": "SECRET_BLADE_3"}]},
            note={"title": "SECRET DOCUMENT", "id": "SECRET_NOTE"})
        state.update(portal_open=True, portal_position=[0, 0])
        view = first_person_data(state)
        self.assertIsNone(view["enemy"])
        self.assertFalse(view["in_combat"])
        self.assertTrue(all(view[key] for key in ("loot", "note", "portal")))
        self.assertNotIn("SECRET", json.dumps(view))
        self.assertNotIn("98765", json.dumps(view))

    def test_portal_requires_matching_current_room_and_open_flag(self):
        state = self.state()
        for opened, location, expected in (
                (False, [0, 0], False), (True, [1, 0], False),
                (True, None, False), (True, [0, 0], True)):
            with self.subTest(opened=opened, location=location):
                state.update(portal_open=opened, portal_position=location)
                self.assertEqual(first_person_data(state)["portal"], expected)

    def test_sanctuary_does_not_reuse_the_underlying_dungeon_room(self):
        state = self.state()
        state["scene"] = "shop"
        state["won"] = True
        state["encounter"]["hidden"] = True
        state["rooms"][0].update(
            enemy={"name": "SECRET OLD FOE", "hp": 100},
            loot={"gold": 98765}, note={"title": "SECRET OLD NOTE"})
        state.update(portal_open=True, portal_position=[0, 0])
        view = first_person_data(state, "east")
        self.assertEqual(view["scene"], "shop")
        self.assertEqual(view["room_name"], "The Lantern Between Worlds")
        self.assertTrue(view["won"])
        self.assertFalse(any(view[key] for key in (
            "enemy", "loot", "note", "portal", "in_combat", "hidden")))
        self.assertFalse(any(view["exits"].values()))
        self.assertNotIn("SECRET", json.dumps(view))

    def test_dead_character_keeps_visible_room_but_combat_is_over(self):
        state = self.state()
        state["player"].update(hp=0, dead=True)
        state["over"] = True
        state["rooms"][0]["enemy"] = {"name": "Crypt Rat", "hp": 2}
        view = first_person_data(state)
        self.assertTrue(view["dead"])
        self.assertFalse(view["in_combat"])
        self.assertEqual(view["enemy"]["name"], "Crypt Rat")
        self.assertEqual(view["room_name"], "Known chamber")

    def test_empty_treasure_and_collected_documents_are_not_drawn(self):
        state = self.state()
        state["rooms"][0].update(
            loot={"gold": 0, "potions": 0, "equipment": [], "items": [],
                  "weapon_bonus": 3},
            note={"title": "Already read"}, note_collected=True)
        view = first_person_data(state)
        self.assertFalse(view["loot"])
        self.assertFalse(view["note"])

    def test_visible_names_choose_generic_original_shapes(self):
        names = {
            "Crypt Rat": "rat", "Amber Mantis": "insect",
            "Rootcoil Viper": "serpent", "Starless Leech": "serpent",
            "Slime": "ooze", "Crown Wisp": "wisp",
            "Restless Knight": "armored", "Hollow Acolyte": "humanoid",
        }
        state = self.state()
        for name, archetype in names.items():
            with self.subTest(name=name):
                state["rooms"][0]["enemy"] = {"name": name, "hp": 1}
                self.assertEqual(first_person_data(state)["enemy"]["archetype"], archetype)

    def test_model_handles_title_and_malformed_unknown_rooms_without_metadata_leaks(self):
        self.assertEqual(first_person_data(DesktopSession(seed=7).get_state())["room_name"],
                         "Unexplored chamber")
        state = self.state()
        state["rooms"] = [None, "SECRET", 99, {
            "position": [0, 0], "visited": "False", "name": "SECRET",
            "enemy": {"hp": object()}, "exits": object()}]
        view = first_person_data(state)
        self.assertNotIn("SECRET", json.dumps(view))
        self.assertFalse(view["in_combat"])

    def test_all_floor_and_class_variants_keep_their_visible_identity(self):
        for floor in range(1, 6):
            for class_id in ("fighter", "rogue", "wizard"):
                with self.subTest(floor=floor, class_id=class_id):
                    state = self.state()
                    state["floor"] = floor
                    state["player"]["class_id"] = class_id
                    view = first_person_data(state)
                    self.assertEqual((view["floor"], view["class_id"]), (floor, class_id))
        state["floor"] = True
        state["player"]["class_id"] = "unknown"
        self.assertEqual(first_person_data(state)["floor"], 1)
        self.assertEqual(first_person_data(state)["class_id"], "fighter")

    def test_real_equipment_loot_remains_only_a_presence_flag_until_collected(self):
        game = Game(seed=7)
        game.room.enemy = None
        game.room.note = None
        game.room.loot = Loot(equipment=(make_equipment("longsword", 3),))
        view = first_person_data(game.get_state())
        self.assertTrue(view["loot"])
        self.assertNotIn("longsword", json.dumps(view).lower())
        game.room.looted = True
        self.assertFalse(first_person_data(game.get_state())["loot"])

    def test_real_engine_views_and_output_mutation_do_not_change_state_or_rng(self):
        for class_id in ("fighter", "rogue", "wizard"):
            with self.subTest(class_id=class_id):
                game = Game(seed=7, class_id=class_id)
                game.room.enemy = Enemy("Crypt Rat", 5, 5, 11, 2, (1, 4), 1, 50, 4)
                state, rng = game.get_state(), game.rng.getstate()
                original = copy.deepcopy(state)
                for direction in ("north", "east", "south", "west"):
                    view = first_person_data(state, direction)
                    self.assertEqual(view["class_id"], class_id)
                    self.assertTrue(view["in_combat"])
                    json.dumps(view)
                    view["exits"].clear()
                    view["enemy"]["name"] = "CHANGED"
                self.assertEqual(state, original)
                self.assertEqual(game.get_state(), original)
                self.assertEqual(game.rng.getstate(), rng)

    def test_equipped_two_handed_weapon_controls_foreground_without_rng(self):
        game = Game(seed=7, class_id="fighter")
        rng = game.rng.getstate()
        one_handed = game.player.equipped_weapon
        self.assertFalse(first_person_data(game.get_state())["two_handed"])
        greatsword = make_equipment("greatsword", 1)
        game.player.collect_equipment(greatsword, auto_equip=False)
        self.assertFalse(first_person_data(game.get_state())["two_handed"],
                         "A carried spare must not change the displayed grip.")
        self.assertTrue(game.player.equip_equipment(greatsword))
        state = game.get_state()
        self.assertTrue(first_person_data(state)["two_handed"])
        self.assertEqual(game.get_state(), state)
        self.assertTrue(game.player.equip_equipment(one_handed))
        self.assertFalse(first_person_data(game.get_state())["two_handed"])
        self.assertEqual(game.rng.getstate(), rng)

    def test_all_views_return_fresh_nested_structures(self):
        state = self.state()
        state["rooms"][0]["enemy"] = {"name": "Bone Sentry", "hp": 8}
        first = first_person_data(state)
        second = first_person_data(state)
        self.assertEqual(first, second)
        self.assertIsNot(first["exits"], second["exits"])
        self.assertIsNot(first["enemy"], second["enemy"])
        first["enemy"]["name"] = "CHANGED"
        first["exits"]["front"] = False
        self.assertNotEqual(first, second)
        self.assertEqual(first_person_data(state), second)


if __name__ == "__main__":
    unittest.main()
