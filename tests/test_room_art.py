"""Room atlas extraction, viewport coverage, caching, and failure isolation."""

import base64
from copy import deepcopy
from pathlib import Path
import random
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import room_art
from room_art_catalog import ROOM_ART_BY_ID
from sprite_art import _decode_png, _encode_png


class ImageCanvas:
    tk = object()

    def __init__(self):
        self.images = []

    def create_image(self, x, y, **options):
        self.images.append((x, y, options))


class RoomArtTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        asset_root = patch.object(room_art, "ASSET_ROOT", self.root)
        asset_root.start()
        self.addCleanup(asset_root.stop)
        for cache in (room_art._atlas_pixels, room_art._room_pixels, room_art._rendered_room_png,
                      room_art._exit_pixels, room_art._rendered_exit_png):
            cache.cache_clear()
            self.addCleanup(cache.cache_clear)

    def atlas(self, floor=1, width=14, height=30, encoded=False):
        colors = [(20 + cell * 12, 40 + floor * 13, 180 - cell * 7, 255)
                  for cell in range(12)]
        pixels = bytearray(width * height * 4)
        for cell, color in enumerate(colors):
            col, row = cell % 2, cell // 2
            for y in range(row * height // 6, (row + 1) * height // 6):
                for x in range(col * width // 2, (col + 1) * width // 2):
                    position = (y * width + x) * 4
                    pixels[position:position + 4] = bytes(color)
        data = _encode_png(width, height, pixels)
        path = self.root / (f"floor_{floor}.png.b64" if encoded else f"floor_{floor}.png")
        path.write_bytes(base64.b64encode(data) if encoded else data)
        return colors, data

    def doorway_atlas(self):
        width, height = 30, 50
        pixels = bytearray(width * height * 4)
        colors = [(25 + cell * 12, 140, 190 - cell * 8, 255) for cell in range(15)]
        for cell, color in enumerate(colors):
            col, row = cell % 3, cell // 3
            for y in range(row * 10 + 1, row * 10 + 9):
                for x in range(col * 10 + 3, col * 10 + 7):
                    position = (y * width + x) * 4
                    pixels[position:position + 4] = bytes(color)
            # A cutout corner stays transparent after the surrounding gutter
            # is trimmed and during smooth edge scaling.
            position = ((row * 10 + 1) * width + col * 10 + 3) * 4
            pixels[position:position + 4] = bytes(4)
        path = self.root / "doorways.png"
        path.write_bytes(_encode_png(width, height, pixels))
        return colors

    def test_doorways_select_each_floors_three_perspectives_and_keep_alpha(self):
        colors = self.doorway_atlas()
        path, modified, size = room_art._asset_path("doorways.png")
        for floor in range(1, 6):
            for index, relative in enumerate(("left", "front", "right")):
                cell = (floor - 1) * 3 + index
                with self.subTest(floor=floor, relative=relative):
                    width, height, pixels = room_art._exit_pixels(str(path), modified, size, cell)
                    self.assertEqual((width, height), (4, 8))
                    actual = set(tuple(pixels[i:i + 4]) for i in range(0, len(pixels), 4))
                    self.assertEqual(actual, {(0, 0, 0, 0), colors[cell]})
                    encoded = room_art._rendered_exit_png(str(path), modified, size, cell, 10, 20)
                    width, height, pixels = _decode_png(encoded)
                    self.assertEqual((width, height), (10, 20))
                    self.assertEqual(pixels[:4], bytes(4))
                    self.assertTrue(any(0 < alpha < 255 for alpha in pixels[3::4]))

    def test_doorway_placement_cache_and_tags_keep_side_passages_attached_to_edge(self):
        self.doorway_atlas()
        canvas = ImageCanvas()
        with patch("tkinter.PhotoImage", side_effect=lambda **kwargs: object()) as photo:
            for relative, expected in (("left", (0, 424)), ("front", (500, 310)),
                                       ("right", (1000, 424))):
                for _ in range(2):
                    self.assertTrue(room_art.draw_exit_art(canvas, 1000, 400, 3, relative,
                                                           tags=("view-exit",)))
                self.assertAlmostEqual(canvas.images[-1][0], expected[0])
                self.assertAlmostEqual(canvas.images[-1][1], expected[1])
                self.assertEqual(canvas.images[-1][2]["anchor"], "s")
                self.assertIn("view-exit", canvas.images[-1][2]["tags"])
                self.assertIn("view-exit-art", canvas.images[-1][2]["tags"])
                self.assertIn("exit-art-" + relative, canvas.images[-1][2]["tags"])
            self.assertEqual(photo.call_count, 3)
            for width in range(100, 140):
                self.assertTrue(room_art.draw_exit_art(canvas, width, 100, 3, "left"))
        self.assertLessEqual(len(canvas._room_exit_images), 12)
        self.assertLessEqual(room_art._rendered_exit_png.cache_info().currsize, 18)
        self.assertLessEqual(room_art._exit_pixels.cache_info().currsize, 15)

    def test_bad_or_unavailable_doorway_art_returns_to_fallback_without_partial_image(self):
        canvas = ImageCanvas()
        with patch.object(room_art, "_asset_path") as source:
            for floor, relative in ((0, "left"), (6, "right"), (True, "front"),
                                     (1, "back"), (1, "unknown")):
                self.assertFalse(room_art.draw_exit_art(canvas, 1000, 400, floor, relative))
            source.assert_not_called()
        self.assertFalse(room_art.draw_exit_art(canvas, 1000, 400, 1, "left"))
        (self.root / "doorways.png").write_bytes(b"broken")
        self.assertFalse(room_art.draw_exit_art(canvas, 1000, 400, 1, "left"))
        self.assertFalse(canvas.images)

    def test_anvil_far_passage_uses_a_clear_rear_wall_instead_of_the_anvil(self):
        self.doorway_atlas()
        self.atlas(floor=3, width=60, height=60)
        canvas, encoded = ImageCanvas(), []
        def image(**options):
            encoded.append(options["data"])
            return object()
        with patch("tkinter.PhotoImage", side_effect=image):
            self.assertTrue(room_art.draw_exit_art(canvas, 1000, 400, 3, "front",
                                                   room_art_id="floor_3_room_07"))
        x, bottom, _ = canvas.images[-1]
        width, height, _ = _decode_png(encoded[-1])
        self.assertGreaterEqual(x - width / 2, 650,
                                "The passage must stay to the right of the anvil's silhouette.")
        self.assertGreater(bottom, 250, "The footing must meet the painted rear-right floor.")
        self.assertLessEqual(bottom, 310)
        self.assertGreater(bottom - height, 0)
        self.assertEqual(room_art.exit_art_placement(3, "left", "floor_3_room_07"),
                         room_art.exit_art_placement(3, "left"))
        self.assertEqual(room_art.exit_art_placement(3, "right", "floor_3_room_07"),
                         room_art.exit_art_placement(3, "right"))

    def test_far_passage_tracks_its_painted_wall_through_horizontal_and_vertical_cover_crops(self):
        self.atlas(floor=3, width=60, height=60)
        spec = ROOM_ART_BY_ID["floor_3_room_07"]
        original = spec.front_passage
        for width, height in ((1000, 400), (650, 240), (1600, 400)):
            with self.subTest(viewport=(width, height)):
                x, bottom, passage_width, passage_height = room_art._project_front_passage(
                    spec, width, height, original)
                left, top, crop_width, crop_height = room_art._cover_region(30, 10, width, height)
                # Projecting back lands at the same original wall, rather than
                # sliding a passage onto the anvil when the room image crops.
                self.assertAlmostEqual((x * crop_width + left) / 30, original[0])
                self.assertAlmostEqual((bottom * crop_height + top) / 10, original[1])
                self.assertAlmostEqual(passage_width * crop_width / 30, original[2])
                self.assertAlmostEqual(passage_height * crop_height / 10, original[3])

    def test_art_context_requires_a_known_identifier_for_the_current_floor(self):
        canvas = ImageCanvas()
        with patch.object(room_art, "_asset_path") as source:
            for identifier in ("unknown", [], {"x": .9}, "floor_2_room_07"):
                with self.subTest(identifier=identifier):
                    self.assertFalse(room_art.draw_exit_art(canvas, 1000, 400, 3, "front",
                                                           room_art_id=identifier))
            source.assert_not_called()
        self.assertFalse(canvas.images)

    def test_reviewed_obstructed_wall_is_handled_without_cutting_a_fake_opening(self):
        spec = ROOM_ART_BY_ID["floor_3_room_10"]
        self.assertIsNone(spec.front_passage)
        canvas = ImageCanvas()
        with patch.object(room_art, "_asset_path") as source:
            self.assertTrue(room_art.draw_exit_art(canvas, 1000, 400, 3, "front",
                                                  room_art_id=spec.id))
            source.assert_not_called()
        self.assertFalse(canvas.images)

    def test_every_cell_is_exact_and_cannot_bleed_neighbor_pixels_when_resized(self):
        # Uneven dimensions exercise integer cell boundaries as well as cover
        # crops in both directions. Each of the sixty IDs must select its cell.
        for floor in range(1, 6):
            colors, _ = self.atlas(floor, width=15, height=31)
            for cell in range(12):
                for size in ((18, 6), (5, 20)):
                    with self.subTest(floor=floor, cell=cell, size=size):
                        width, height, pixels = _decode_png(room_art.render_room_png(
                            f"floor_{floor}_room_{cell:02d}", *size))
                        self.assertEqual((width, height), size)
                        self.assertEqual(set(tuple(pixels[i:i + 4]) for i in range(0, len(pixels), 4)),
                                         {colors[cell]})

    def test_cover_crop_preserves_proportions_and_fills_the_view(self):
        # A narrow viewport crops out the sides rather than squeezing them in.
        pixels = bytes((250, 0, 0, 255)) * 2 + bytes((0, 190, 0, 255)) * 2 + bytes((0, 0, 250, 255)) * 2
        image = pixels * 2
        actual = room_art._cover_pixels(6, 2, image, 2, 2)
        self.assertEqual(actual, bytes((0, 190, 0, 255)) * 4)

    def test_native_and_base64_atlases_produce_identical_art(self):
        self.atlas()
        expected = room_art.render_room_png("floor_1_room_07", 32, 12)
        (self.root / "floor_1.png").unlink()
        self.atlas(encoded=True)
        self.assertEqual(room_art.render_room_png("floor_1_room_07", 32, 12), expected)

    def test_unknown_identifier_and_bad_sizes_fail_before_reading_assets(self):
        with patch.object(room_art, "_asset_path") as path:
            for identifier in (None, "unknown", "../floor_1.png", [], {}):
                with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                    room_art.render_room_png(identifier, 32, 12)
            for size in ((0, 20), (20, -1), (float("nan"), 20),
                         (20, float("inf")), (True, 20), (5000, 20), (4096, 2048)):
                with self.subTest(size=size), self.assertRaises(ValueError):
                    room_art.render_room_png("floor_1_room_00", *size)
            path.assert_not_called()

    def test_missing_and_corrupt_atlas_return_to_the_callers_fallback(self):
        canvas = ImageCanvas()
        self.assertFalse(room_art.draw_room_art(canvas, 100, 40, "floor_1_room_00"))
        (self.root / "floor_1.png").write_bytes(b"not a PNG")
        self.assertFalse(room_art.draw_room_art(canvas, 100, 40, "floor_1_room_00"))
        self.assertFalse(canvas.images)
        self.assertFalse(room_art.draw_room_art(object(), 100, 40, "floor_1_room_00"))

    def test_repeated_combat_redraws_reuse_the_same_native_image_and_all_caches_are_bounded(self):
        self.atlas()
        canvas = ImageCanvas()
        with patch("tkinter.PhotoImage", side_effect=lambda **kwargs: object()) as photo:
            for _ in range(12):
                self.assertTrue(room_art.draw_room_art(canvas, 60, 20, "floor_1_room_03",
                                                       tags=("dungeon-view", "view-wall")))
            self.assertEqual(photo.call_count, 1)
            self.assertEqual({id(image[2]["image"]) for image in canvas.images},
                             {id(canvas.images[0][2]["image"])})
            self.assertEqual(canvas.images[0][0:2], (0, 0))
            self.assertEqual(canvas.images[0][2]["anchor"], "nw")
            self.assertIn("view-room-art", canvas.images[0][2]["tags"])
            self.assertIn("room-art-floor_1_room_03", canvas.images[0][2]["tags"])
            for width in range(61, 82):
                self.assertTrue(room_art.draw_room_art(canvas, width, 20, "floor_1_room_03"))
        self.assertLessEqual(len(canvas._room_art_images), room_art._MAX_IMAGES)
        self.assertLessEqual(room_art._rendered_room_png.cache_info().currsize, 12)
        self.assertLessEqual(room_art._room_pixels.cache_info().currsize, 12)
        self.assertLessEqual(room_art._atlas_pixels.cache_info().currsize, 2)

    def test_art_read_does_not_mutate_catalog_or_use_global_randomness(self):
        self.atlas()
        before = {key: deepcopy(value) for key, value in ROOM_ART_BY_ID.items()}
        state = random.getstate()
        for _ in range(3):
            room_art.render_room_png("floor_1_room_02", 80, 32)
        self.assertEqual(dict(ROOM_ART_BY_ID), before)
        self.assertEqual(random.getstate(), state)

    def test_replacing_a_source_atlas_invalidates_the_image_cache(self):
        self.atlas()
        canvas = ImageCanvas()
        with patch("tkinter.PhotoImage", side_effect=lambda **kwargs: object()) as photo:
            self.assertTrue(room_art.draw_room_art(canvas, 30, 12, "floor_1_room_00"))
            path = self.root / "floor_1.png"
            path.write_bytes(_encode_png(14, 30, bytes((240, 150, 10, 255)) * 420))
            self.assertTrue(room_art.draw_room_art(canvas, 30, 12, "floor_1_room_00"))
            self.assertEqual(photo.call_count, 2)
            self.assertIsNot(canvas.images[0][2]["image"], canvas.images[1][2]["image"])

    def test_real_tk_room_image_reuses_background_during_redraw_and_remains_bounded(self):
        import tkinter as tk
        try:
            root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"A Tk display is required: {error}")
        self.addCleanup(root.destroy)
        root.withdraw()
        self.atlas()
        canvas = tk.Canvas(root)
        for _ in range(2):
            self.assertTrue(room_art.draw_room_art(canvas, 120, 40, "floor_1_room_01"))
        items = canvas.find_withtag("view-room-art")
        self.assertEqual(canvas.itemcget(items[0], "image"), canvas.itemcget(items[1], "image"))
        photo = canvas._room_art_images[next(iter(canvas._room_art_images))]
        self.assertEqual((photo.width(), photo.height()), (120, 40))
        for width in range(121, 134):
            canvas.delete("all")
            self.assertTrue(room_art.draw_room_art(canvas, width, 40, "floor_1_room_01"))
        self.assertLessEqual(len(canvas._room_art_images), room_art._MAX_IMAGES)


if __name__ == "__main__":
    unittest.main()
