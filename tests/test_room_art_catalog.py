"""A shuffled dungeon keeps the painting authored for each room's identity."""

from dataclasses import FrozenInstanceError
import random
import unittest

from dungeon import Dungeon
from floor_lore import LORE
from room_art_catalog import (
    ATLAS_COLUMNS, ATLAS_ROWS, ROOM_ART_BY_ID, ROOM_ART_BY_ROOM,
    room_art_by_id, room_art_for,
)


class RoomArtCatalogTests(unittest.TestCase):
    def test_every_authored_room_has_one_distinct_atlas_panel(self):
        self.assertEqual((ATLAS_COLUMNS, ATLAS_ROWS), (2, 6))
        self.assertEqual(len(ROOM_ART_BY_ID), 60)
        self.assertEqual(len(ROOM_ART_BY_ROOM), 60)
        for floor, lore in enumerate(LORE, 1):
            rooms = (lore.entrance, *lore.rooms, lore.sanctum)
            specs = [room_art_for(floor, name) for name, _ in rooms]
            self.assertEqual({spec.cell for spec in specs}, set(range(12)))
            self.assertEqual({spec.atlas for spec in specs}, {f"floor_{floor}.png"})
            for (name, description), spec in zip(rooms, specs):
                with self.subTest(floor=floor, room=name):
                    self.assertEqual((spec.name, spec.description), (name, description))
                    self.assertIs(room_art_by_id(spec.id), spec)
                    self.assertTrue(spec.landmarks)
                    self.assertTrue(all(isinstance(feature, str) and feature
                                        for feature in spec.landmarks))

    def test_key_landmarks_resolve_to_their_authored_panels(self):
        references = (
            (1, "The Broken Stair", 0, "moonlight"),
            (1, "The Echoing Well", 7, "central dry well"),
            (1, "The Warden's Sanctum", 11, "blue fire"),
            (2, "The Gardener's Crypt", 2, "kneeling skeleton"),
            (2, "The Heartwood Cage", 11, "cracked furnace hatch"),
            (3, "The Quenching Chamber", 5, "frosted silver chain"),
            (4, "The Mirror Prison", 6, "covered mirrors"),
            (5, "The Chamber of the Offering", 3, "dried handprint"),
            (5, "The Hollow Throne", 11, "bedrock throne"),
        )
        for floor, name, cell, feature in references:
            with self.subTest(floor=floor, room=name):
                spec = room_art_for(floor, name)
                self.assertEqual(spec.cell, cell)
                self.assertIn(feature, spec.landmarks)

    def test_selection_follows_room_identity_after_map_shuffling(self):
        placements = set()
        for floor in range(1, 6):
            for seed in (7, 42, 817):
                dungeon = Dungeon(random.Random(seed), floor=floor)
                selected = []
                for room in dungeon.rooms.values():
                    spec = room_art_for(floor, room.name)
                    self.assertIsNotNone(spec)
                    self.assertEqual(spec.description, room.description)
                    selected.append(spec.id)
                    if floor == 1 and room.name == "The Echoing Well":
                        placements.add(room.position)
                        self.assertEqual(spec.id, "floor_1_room_07")
                self.assertEqual(len(set(selected)), 12)
        self.assertGreater(len(placements), 1)

    def test_only_exact_room_and_floor_match_without_keyword_guessing(self):
        for floor, name in ((2, "The Broken Stair"), (1, "the broken stair"),
                            (1, "The Broken Stair "), (1, "A room with roots"),
                            (1, "The Echoing Well and a throne"),
                            (0, "The Broken Stair"), (True, "The Broken Stair"),
                            (1.0, "The Broken Stair"), (1, None), (1, [])):
            with self.subTest(floor=floor, room=name):
                self.assertIsNone(room_art_for(floor, name))
        for invalid in (None, [], {}, "floor_1_room_99", "FLOOR_1_ROOM_00"):
            self.assertIsNone(room_art_by_id(invalid))

    def test_shared_catalog_and_its_specs_cannot_be_mutated(self):
        spec = room_art_for(1, "The Broken Stair")
        with self.assertRaises(TypeError):
            ROOM_ART_BY_ID[spec.id] = None
        with self.assertRaises(TypeError):
            ROOM_ART_BY_ROOM[(1, spec.name)] = None
        with self.assertRaises(FrozenInstanceError):
            spec.cell = 99
        self.assertIsInstance(spec.landmarks, tuple)

    def test_catalog_reads_do_not_draw_random_numbers(self):
        before = random.getstate()
        for spec in ROOM_ART_BY_ID.values():
            self.assertIs(room_art_for(spec.floor, spec.name), spec)
            self.assertIs(room_art_by_id(spec.id), spec)
        self.assertEqual(random.getstate(), before)

    def test_every_front_passage_is_an_immutable_bounded_footprint(self):
        for spec in ROOM_ART_BY_ID.values():
            with self.subTest(room=spec.name):
                if spec.front_passage is None:
                    continue
                self.assertIsInstance(spec.front_passage, tuple)
                x, bottom, width, height = spec.front_passage
                self.assertGreater(width, 0)
                self.assertGreater(height, 0)
                self.assertGreaterEqual(x - width / 2, 0)
                self.assertLessEqual(x + width / 2, 1)
                self.assertGreaterEqual(bottom - height, 0)
                self.assertLessEqual(bottom, 1)

    def test_doorways_leave_prominent_room_landmarks_intact(self):
        # Painting-space horizontal bounds of defining objects. The exit must
        # occupy peripheral masonry rather than cut through these landmarks.
        protected = (
            (1, "Chapel of the Last Light", .34, .70),
            (1, "The Sunken Gallery", .32, .94),
            (1, "The Scribe's Tomb", .00, .88),
            (1, "The Echoing Well", .30, .70),
            (2, "The Hollow Oak", .35, .88),
            (2, "The Heartwood Cage", .26, .88),
            (3, "The Broken Anvil", .24, .56),
            (5, "The Chamber of the Offering", .32, .70),
            (5, "The Hollow Throne", .32, .76),
        )
        for floor, name, left, right in protected:
            with self.subTest(room=name):
                placement = room_art_for(floor, name).front_passage
                if placement is None:
                    continue
                x, _, width, _ = placement
                self.assertTrue(x + width / 2 <= left or x - width / 2 >= right)
        anvil = room_art_for(3, "The Broken Anvil")
        x, bottom, width, _ = anvil.front_passage
        self.assertGreaterEqual(x - width / 2, .64)
        self.assertAlmostEqual(bottom, .70)
        # The Sealed Dawn already paints a low passage below its mosaic.
        _, bottom, _, height = room_art_for(5, "The Sealed Dawn").front_passage
        self.assertGreaterEqual(bottom - height, .60)

    def test_far_exits_are_not_painted_through_obscuring_architecture(self):
        self.assertEqual({(spec.floor, spec.name) for spec in ROOM_ART_BY_ID.values()
                          if spec.front_passage is None}, {
            (1, "The Starless Observatory"),
            (2, "The Drowned Nursery"), (2, "The Ember Well"),
            (3, "The Pressure Gallery"), (4, "The Silent Causeway"),
            (4, "The Oathbound Gate"),
            (5, "The Hollow Throne"),
        })


if __name__ == "__main__":
    unittest.main()
