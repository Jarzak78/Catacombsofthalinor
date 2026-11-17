"""Exercise original view geometry without creating a Tk root or a game."""

import math
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from dungeon_view import VIEW_TAG, draw_dungeon_view


class RecordingCanvas:
    """The Canvas drawing protocol, with realistic tag deletion semantics."""

    def __init__(self):
        self.items = []
        self.next_id = 0

    def delete(self, tag):
        self.items = [item for item in self.items if tag not in item["options"].get("tags", ())]

    def _create(self, kind, coordinates, options):
        self.next_id += 1
        self.items.append({"id": self.next_id, "kind": kind,
                           "coordinates": coordinates, "options": options})
        return self.next_id

    def create_polygon(self, *coordinates, **options):
        return self._create("polygon", coordinates, options)

    def create_rectangle(self, *coordinates, **options):
        return self._create("rectangle", coordinates, options)

    def create_oval(self, *coordinates, **options):
        return self._create("oval", coordinates, options)

    def create_line(self, *coordinates, **options):
        return self._create("line", coordinates, options)

    def tagged(self, tag):
        return [item for item in self.items if tag in item["options"].get("tags", ())]


def room_view(**changes):
    view = {"scene": "dungeon", "floor": 1, "theme": "Forgotten Catacombs",
            "facing": "north", "room_name": "Quiet Chamber",
            "exits": {"front": True, "left": False, "right": True, "back": True},
            "enemy": None, "loot": False, "note": False, "portal": False,
            "class_id": "fighter", "dead": False, "won": False,
            "hidden": False, "in_combat": False}
    view.update(changes)
    return view


class DungeonArtTests(unittest.TestCase):
    def test_all_floors_and_classes_render_at_small_default_and_large_sizes(self):
        backgrounds = set()
        for floor in range(1, 6):
            for class_id in ("fighter", "rogue", "wizard"):
                for width, height in ((250, 100), (650, 240), (1600, 640)):
                    with self.subTest(floor=floor, class_id=class_id, size=(width, height)):
                        canvas = RecordingCanvas()
                        draw_dungeon_view(canvas, width, height,
                                          room_view(floor=floor, class_id=class_id))
                        self.assertTrue(canvas.tagged("view-wall"))
                        self.assertTrue(canvas.tagged("view-hands"))
                        self.assertTrue(canvas.tagged("view-frame"))
                        backgrounds.add(canvas.items[0]["options"]["fill"])
                        for item in canvas.items:
                            self.assertIn(VIEW_TAG, item["options"]["tags"])
                            self.assertTrue(all(isinstance(v, (int, float)) and math.isfinite(v)
                                                for v in item["coordinates"]))
                            self.assertGreater(item["options"]["width"], 0)
        self.assertEqual(len(backgrounds), 5)

    def test_exits_only_draw_for_visible_front_left_or_right_connections(self):
        canvas = RecordingCanvas()
        draw_dungeon_view(canvas, 1000, 400,
                          room_view(exits={"back": True}))
        self.assertFalse(canvas.tagged("view-exit"))
        for direction in ("front", "left", "right"):
            with self.subTest(direction=direction):
                draw_dungeon_view(canvas, 1000, 400,
                                  room_view(exits={direction: True}))
                self.assertTrue(canvas.tagged("view-exit"))

    def test_foe_silhouettes_differ_and_guardians_have_distinct_markings(self):
        signatures = set()
        for archetype in ("rat", "insect", "serpent", "construct", "ooze", "specter", "skeleton", "humanoid"):
            canvas = RecordingCanvas()
            enemy = {"name": "Visible foe", "boss": False, "archetype": archetype}
            view = room_view(enemy=enemy, in_combat=True)
            draw_dungeon_view(canvas, 1000, 400, view)
            ordinary = canvas.tagged("view-enemy")
            self.assertTrue(ordinary)
            signature = tuple((item["kind"], item["coordinates"], item["options"]["fill"])
                              for item in ordinary)
            signatures.add(signature)
            enemy["boss"] = True
            draw_dungeon_view(canvas, 1000, 400, view)
            self.assertGreater(len(canvas.tagged("view-enemy")), len(ordinary))
        self.assertEqual(len(signatures), 8)

    def test_combat_never_draws_treasure_notes_or_portals(self):
        for enemy, combat in ((None, True),
                              ({"name": "Foe", "boss": False, "archetype": "humanoid"}, False)):
            with self.subTest(enemy=enemy, combat=combat):
                canvas = RecordingCanvas()
                draw_dungeon_view(canvas, 650, 240,
                                  room_view(enemy=enemy, in_combat=combat,
                                            loot=True, note=True, portal=True))
                for tag in ("view-loot", "view-note", "view-portal"):
                    self.assertFalse(canvas.tagged(tag))
        draw_dungeon_view(canvas, 650, 240,
                          room_view(loot=True, note=True, portal=True))
        for tag in ("view-loot", "view-note", "view-portal"):
            self.assertTrue(canvas.tagged(tag))

    def test_sanctuary_is_a_separate_scene_without_dungeon_foes_or_gear_hands(self):
        canvas = RecordingCanvas()
        draw_dungeon_view(canvas, 650, 240, room_view(
            scene="shop", portal=False, loot=True, note=True,
            enemy={"name": "Old dungeon foe", "boss": True, "archetype": "construct"}))
        self.assertTrue(canvas.tagged("view-sanctuary"))
        self.assertTrue(canvas.tagged("view-portal"))
        for tag in ("view-enemy", "view-loot", "view-note", "view-hands", "view-exit"):
            self.assertFalse(canvas.tagged(tag))

    def test_redraw_replaces_only_its_art_and_does_not_accumulate_shapes(self):
        canvas = RecordingCanvas()
        unrelated = canvas.create_rectangle(0, 0, 1, 1, tags=("unrelated",))
        view = room_view(loot=True, note=True)
        draw_dungeon_view(canvas, 650, 240, view)
        count = len(canvas.tagged(VIEW_TAG))
        for _ in range(12):
            draw_dungeon_view(canvas, 650, 240, view)
            self.assertEqual(len(canvas.tagged(VIEW_TAG)), count)
        self.assertEqual([item["id"] for item in canvas.tagged("unrelated")], [unrelated])

    def test_two_handed_weapon_removes_the_illustrated_shield(self):
        canvas = RecordingCanvas()
        draw_dungeon_view(canvas, 650, 240, room_view())
        self.assertTrue(canvas.tagged("view-shield"))
        draw_dungeon_view(canvas, 650, 240, room_view(two_handed=True))
        self.assertFalse(canvas.tagged("view-shield"))
        self.assertTrue(canvas.tagged("view-hands"))

    def test_nonpositive_sizes_clear_stale_art_without_touching_other_items(self):
        for width, height in ((0, 240), (650, 0), (-20, 240), (650, -20)):
            with self.subTest(size=(width, height)):
                canvas = RecordingCanvas()
                canvas.create_oval(0, 0, 2, 2, tags=("unrelated",))
                draw_dungeon_view(canvas, 650, 240, room_view())
                draw_dungeon_view(canvas, width, height, room_view())
                self.assertFalse(canvas.tagged(VIEW_TAG))
                self.assertEqual(len(canvas.tagged("unrelated")), 1)

    def test_idle_foreground_is_smaller_while_foe_art_keeps_its_original_size(self):
        enemy = {"name": "Bone Sentry", "archetype": "skeleton", "boss": False}
        for equipment, expected_box, expected_x in (({}, (720, 248), 500),
                ({"weapon_id": "greataxe", "two_handed": True}, (500, 240), 650)):
            with self.subTest(equipment=equipment), patch(
                    "dungeon_view.draw_sprite", return_value=True) as sprite:
                draw_dungeon_view(RecordingCanvas(), 1000, 400,
                                  room_view(enemy=enemy, **equipment))
                foe, hands = sprite.call_args_list
                self.assertEqual(foe.args[2:6], (500, 307, 385, 270))
                self.assertEqual(hands.args[2:6], (expected_x, 403, *expected_box))
                self.assertEqual(hands.kwargs["anchor"], "s")

    def test_vector_fallback_is_also_small_and_animates_without_moving_the_room(self):
        enemy = {"name": "Bone Sentry", "archetype": "skeleton", "boss": False}
        canvas = RecordingCanvas()
        draw_dungeon_view(canvas, 1000, 400, room_view(enemy=enemy))
        wall = [item["coordinates"] for item in canvas.tagged("view-wall")]
        before = [item["coordinates"] for item in canvas.tagged("view-enemy")]
        hands = canvas.tagged("view-hands")
        ys = [y for item in hands for y in item["coordinates"][1::2]]
        self.assertLess(max(ys) - min(ys), 150)
        animation = {"enemy_dx": 25, "enemy_dy": 4, "enemy_angle": 12,
                     "enemy_scale_x": .9, "enemy_scale_y": .8,
                     "hands_angle": -12, "hands_dx": -20}
        with patch.dict("sys.modules", {"combat_animation": SimpleNamespace(
                draw_combat_effects=lambda *args: None)}):
            draw_dungeon_view(canvas, 1000, 400, room_view(enemy=enemy), animation=animation)
        self.assertEqual(wall, [item["coordinates"] for item in canvas.tagged("view-wall")])
        self.assertNotEqual(before, [item["coordinates"] for item in canvas.tagged("view-enemy")])
        self.assertTrue(all(math.isfinite(value) for item in canvas.items for value in item["coordinates"]))

    def test_sprite_pose_uses_foe_feet_and_reduced_hand_grip_as_pivots(self):
        animation = {"enemy_dx": 30, "enemy_dy": 5, "enemy_angle": 12,
                     "enemy_scale_x": 1.1, "enemy_scale_y": .8, "enemy_opacity": .75,
                     "hands_dx": -20, "hands_dy": -15, "hands_angle": 24, "hands_scale": 1.1}
        with patch("dungeon_view.draw_sprite", return_value=True) as sprite, patch.dict(
                "sys.modules", {"combat_animation": SimpleNamespace(draw_combat_effects=lambda *args: None)}):
            draw_dungeon_view(RecordingCanvas(), 1000, 400, room_view(
                enemy={"name": "Foe", "archetype": "humanoid"}), animation=animation)
        foe, hands = sprite.call_args_list
        self.assertEqual(foe.args[2:6], (530, 312, 385, 270))
        self.assertEqual((foe.kwargs["angle"], foe.kwargs["stretch_x"],
                          foe.kwargs["stretch_y"], foe.kwargs["opacity"]), (12, 1.1, .8, .75))
        self.assertEqual(hands.args[2:6], (480, 388, 720, 248))
        self.assertEqual((hands.kwargs["angle"], hands.kwargs["stretch_x"]), (24, 1.1))

    def test_effects_are_replaced_and_cleared_on_idle_and_scene_changes(self):
        canvas = RecordingCanvas()

        def effect(canvas, width, height, animation):
            canvas.create_line(1, 2, 3, 4, tags=("combat-fx",))

        with patch.dict("sys.modules", {"combat_animation": SimpleNamespace(draw_combat_effects=effect)}):
            for _ in range(3):
                draw_dungeon_view(canvas, 650, 240, room_view(), animation={"pose": "dodge"})
                self.assertEqual(len(canvas.tagged("combat-fx")), 1)
            draw_dungeon_view(canvas, 650, 240, room_view())
            self.assertFalse(canvas.tagged("combat-fx"))
            draw_dungeon_view(canvas, 650, 240, room_view(scene="shop"), animation={"pose": "dodge"})
            self.assertFalse(canvas.tagged("combat-fx"))
            canvas.create_line(1, 2, 3, 4, tags=("combat-fx",))
            draw_dungeon_view(canvas, 0, 240, room_view())
            self.assertFalse(canvas.tagged("combat-fx"))


if __name__ == "__main__":
    unittest.main()
