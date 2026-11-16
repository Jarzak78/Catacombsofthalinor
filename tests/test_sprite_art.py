"""Small real PNGs exercise sprite extraction and scaling independently of the art."""

import base64
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zlib

import sprite_art


def png_bytes(width, height, pixels, filtering=0):
    """Encode RGBA fixture pixels with the standard PNG structure and filters."""
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff))
    scanlines, previous = bytearray(), bytes(width * 4)
    for y in range(height):
        row = bytes(pixels[y * width * 4:(y + 1) * width * 4])
        scanlines.append(filtering)
        for index, value in enumerate(row):
            left = row[index - 4] if index >= 4 else 0
            above = previous[index]
            upper_left = previous[index - 4] if index >= 4 else 0
            if filtering == 4:
                estimate = left + above - upper_left
                distances = (abs(estimate - left), abs(estimate - above), abs(estimate - upper_left))
                predictor = (left, above, upper_left)[distances.index(min(distances))]
            else:
                predictor = (0, left, above, (left + above) // 2)[filtering]
            scanlines.append((value - predictor) & 255)
        previous = row
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b""))


def decoded_pixels(data):
    """Read ordinary 8-bit RGBA PNG output using the documented PNG filters."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError("Rendered sprite is not a PNG")
    offset, compressed = 8, bytearray()
    while offset < len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        kind, payload = data[offset + 4:offset + 8], data[offset + 8:offset + 8 + length]
        if kind == b"IHDR":
            width, height, depth, color, *_ = struct.unpack(">IIBBBBB", payload)
            if (depth, color) != (8, 6):
                raise AssertionError("Expected transparent RGBA PNG output")
        elif kind == b"IDAT":
            compressed.extend(payload)
        offset += length + 12
    rows, raw = [], zlib.decompress(compressed)
    stride = width * 4
    previous = bytes(stride)
    for y in range(height):
        start = y * (stride + 1)
        filtering = raw[start]
        row = bytearray(raw[start + 1:start + 1 + stride])
        for index in range(stride):
            left = row[index - 4] if index >= 4 else 0
            above = previous[index]
            upper_left = previous[index - 4] if index >= 4 else 0
            if filtering == 1:
                predictor = left
            elif filtering == 2:
                predictor = above
            elif filtering == 3:
                predictor = (left + above) // 2
            elif filtering == 4:
                estimate = left + above - upper_left
                distances = (abs(estimate - left), abs(estimate - above), abs(estimate - upper_left))
                predictor = (left, above, upper_left)[distances.index(min(distances))]
            elif filtering == 0:
                predictor = 0
            else:
                raise AssertionError("Unknown PNG filtering method")
            row[index] = (row[index] + predictor) & 255
        rows.append(bytes(row))
        previous = row
    return width, height, [tuple(row[index:index + 4])
                           for row in rows for index in range(0, stride, 4)]


class SpriteArtTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.asset_patch = patch.object(sprite_art, "ASSET_ROOT", self.root)
        self.asset_patch.start()
        self.addCleanup(self.asset_patch.stop)
        self.manifest_patch = patch.dict(sprite_art.SPRITE_CELLS, clear=False)
        self.manifest_patch.start()
        self.addCleanup(self.manifest_patch.stop)

    def fixture(self, key, width, height, pixels, *, columns=1, rows=1, index=0, encoded=False,
                filtering=0):
        filename = key + ".png"
        data = png_bytes(width, height, pixels, filtering)
        path = self.root / (filename + ".b64" if encoded else filename)
        path.write_bytes(base64.b64encode(data) if encoded else data)
        sprite_art.SPRITE_CELLS[key] = (filename, columns, rows, index)
        return path

    def test_atlas_cell_selection_does_not_mix_neighboring_avatars(self):
        pixels = bytes((200, 20, 20, 255)) * 2 + bytes((20, 40, 210, 255)) * 2
        pixels *= 2
        self.fixture("right_cell", 4, 2, pixels, columns=2, index=1)
        width, height, actual = decoded_pixels(sprite_art.render_sprite_png("right_cell", 40, 40))
        self.assertEqual((width, height), (40, 40))
        self.assertTrue(all(pixel == (20, 40, 210, 255) for pixel in actual))

    def test_irregular_atlas_regions_keep_extended_forearms_without_neighboring_art(self):
        clear, red, green = (0, 0, 0, 0), (200, 30, 40, 255), (20, 170, 60, 255)
        rows = [[clear] * 4, [clear] * 4,
                [clear, red, red, clear], [clear, red, red, clear],
                [clear] * 4, [green] * 4, [green] * 4, [green] * 4]
        pixels = bytes(channel for row in rows for pixel in row for channel in pixel)
        self.fixture("extended_forearm", 4, 8, pixels, rows=3)
        sprite_art.SPRITE_CELLS["neighboring_grip"] = ("extended_forearm.png", 1, 3, 1)
        regions = {"extended_forearm": (0, 0, 1, 5 / 8),
                   "neighboring_grip": (0, 5 / 8, 1, 1)}
        with patch.dict(sprite_art.SPRITE_REGIONS, regions):
            width, height, upper = decoded_pixels(
                sprite_art.render_sprite_png("extended_forearm", 12, 12))
            self.assertEqual((width, height), (12, 12))
            self.assertEqual(set(upper), {red})
            width, height, lower = decoded_pixels(
                sprite_art.render_sprite_png("neighboring_grip", 12, 12))
            self.assertEqual((width, height), (12, 9))
            self.assertEqual(set(lower), {green})

    def test_base64_source_assets_decode_like_the_png_release_asset(self):
        self.fixture("encoded_cell", 2, 2, bytes((51, 92, 130, 255)) * 4, encoded=True)
        width, height, actual = decoded_pixels(sprite_art.render_sprite_png("encoded_cell", 12, 12))
        self.assertEqual((width, height), (12, 12))
        self.assertEqual(set(actual), {(51, 92, 130, 255)})

    def test_standard_png_scanline_filters_preserve_the_generated_art_colors(self):
        expected = [(10, 30, 90, 255), (80, 160, 220, 255), (170, 100, 40, 255),
                    (20, 150, 50, 255), (200, 40, 90, 255), (255, 180, 70, 255)]
        pixels = bytes(channel for pixel in expected for channel in pixel)
        for filtering in range(5):
            with self.subTest(filtering=filtering):
                key = f"filtered_{filtering}"
                self.fixture(key, 3, 2, pixels, filtering=filtering)
                width, height, actual = decoded_pixels(sprite_art.render_sprite_png(key, 3, 2))
                self.assertEqual((width, height), (3, 2))
                self.assertEqual(actual, expected)

    def test_current_weapon_selects_its_supplied_hand_and_grip(self):
        choices = (
            ({"class_id": "fighter", "weapon_id": "longsword"}, "sword_shield"),
            ({"class_id": "fighter", "weapon_id": "greatsword", "two_handed": True}, "greatsword"),
            ({"class_id": "fighter", "weapon_id": "greataxe", "two_handed": True}, "greataxe"),
            ({"class_id": "rogue", "weapon_id": "rapier"}, "rogue_rapier"),
            ({"class_id": "rogue", "weapon_id": "dagger"}, "rogue_dagger"),
            ({"class_id": "wizard", "weapon_id": "arcane_staff"}, "wizard_staff"),
        )
        for view, expected in choices:
            with self.subTest(view=view):
                self.assertEqual(sprite_art.hand_sprite_key(view), expected)

    def test_visible_foe_types_and_each_guardian_select_distinct_supplied_avatars(self):
        guardians = [sprite_art.enemy_sprite_key({"boss": True}, floor) for floor in range(1, 6)]
        self.assertEqual(guardians, ["warden", "sentinel", "colossus", "void_knight", "hollow_king"])
        choices = (
            ({"name": "Crypt Rat", "archetype": "rat"}, "rat"),
            ({"name": "Bone Sentry", "archetype": "armored"}, "skeleton"),
            ({"name": "Sapglass Beetle", "archetype": "insect"}, "beetle"),
            ({"name": "Rootcoil Viper", "archetype": "serpent"}, "serpent"),
            ({"name": "Moldbound Keeper", "archetype": "humanoid"}, "fungal"),
            ({"name": "Bellows Automaton", "archetype": "armored"}, "construct"),
            ({"name": "Crown Wisp", "archetype": "wisp"}, "wisp"),
            ({"name": "Ooze", "archetype": "ooze"}, "ooze"),
        )
        for enemy, expected in choices:
            with self.subTest(enemy=enemy):
                self.assertEqual(sprite_art.enemy_sprite_key(enemy, 3), expected)

    def test_sprite_aspect_ratio_fits_the_requested_view_without_stretching(self):
        self.fixture("wide_cell", 8, 2, bytes((60, 80, 100, 255)) * 16)
        width, height, _ = decoded_pixels(sprite_art.render_sprite_png("wide_cell", 40, 40))
        self.assertEqual((width, height), (40, 10))

    def test_resizing_uses_alpha_aware_colors_instead_of_dark_edge_halos(self):
        self.fixture("alpha_edge", 2, 1,
                     bytes((100, 180, 220, 255, 250, 0, 250, 1)))
        width, height, actual = decoded_pixels(sprite_art.render_sprite_png("alpha_edge", 6, 3))
        self.assertEqual((width, height), (6, 3))
        red, green, blue, alpha = actual[width + 2]
        self.assertGreater(alpha, 1)
        self.assertLess(alpha, 255)
        self.assertLess(red, 120)
        self.assertGreater(green, 160)
        self.assertGreater(blue, 210)

    def test_missing_or_damaged_art_returns_fallback_without_partial_canvas_images(self):
        sprite_art.SPRITE_CELLS["missing_cell"] = ("missing.png", 1, 1, 0)
        with self.assertRaises((OSError, ValueError)):
            sprite_art.render_sprite_png("missing_cell", 20, 20)
        (self.root / "broken.png").write_bytes(b"not a PNG image")
        sprite_art.SPRITE_CELLS["broken_cell"] = ("broken.png", 1, 1, 0)
        with self.assertRaises((OSError, ValueError)):
            sprite_art.render_sprite_png("broken_cell", 20, 20)
        class VectorCanvas:
            pass
        self.assertFalse(sprite_art.draw_sprite(VectorCanvas(), "missing_cell", 0, 0, 20, 20))

    def test_invalid_dimensions_do_not_attempt_to_allocate_a_sprite(self):
        self.fixture("small_cell", 2, 2, bytes((10, 20, 30, 255)) * 4)
        for width, height in ((0, 20), (20, 0), (-1, 20), (20, -1)):
            with self.subTest(size=(width, height)), self.assertRaises((ValueError, OSError)):
                sprite_art.render_sprite_png("small_cell", width, height)

    def test_real_tk_images_are_reused_and_resize_cache_remains_bounded(self):
        import tkinter as tk
        try:
            window = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"A Tk display is required for the real image check: {error}")
        self.addCleanup(window.destroy)
        window.withdraw()
        canvas = tk.Canvas(window)
        self.fixture("cached_cell", 2, 2, bytes((31, 65, 98, 255)) * 4)
        self.assertTrue(sprite_art.draw_sprite(canvas, "cached_cell", 20, 20, 30, 30,
                                              tags=("visible-portrait",)))
        first = canvas.itemcget(canvas.find_withtag("visible-portrait")[0], "image")
        canvas.delete("all")
        self.assertTrue(sprite_art.draw_sprite(canvas, "cached_cell", 20, 20, 30, 30,
                                              tags=("visible-portrait",)))
        second = canvas.itemcget(canvas.find_withtag("visible-portrait")[0], "image")
        self.assertEqual(first, second)
        for size in range(31, 100):
            canvas.delete("all")
            self.assertTrue(sprite_art.draw_sprite(canvas, "cached_cell", 20, 20, size, size))
        self.assertLessEqual(len(canvas._dungeon_sprite_images), 48)
        self.assertGreater(len(canvas._dungeon_sprite_images), 1)


if __name__ == "__main__":
    unittest.main()
