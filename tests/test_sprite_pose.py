"""Pixel-level pose checks without requiring a graphical desktop."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import sprite_art
from dungeon_view import draw_dungeon_view


class ImageCanvas:
    tk = object()

    def __init__(self):
        self.images = []

    def create_image(self, x, y, **options):
        self.images.append((x, y, options))


class SpritePoseTests(unittest.TestCase):
    def test_quarter_turn_preserves_every_pixel_and_keeps_the_feet_pivot(self):
        colors = [(r, 60, 100, 255) for r in (20, 40, 80, 100, 140, 180)]
        pixels = bytes(channel for color in colors for channel in color)
        width, height, actual, left, top = sprite_art._affine_rgba(
            2, 3, pixels, 90, 1, 1, 1, "s")
        self.assertEqual((width, height, left, top), (3, 2, 0, -1))
        actual = [tuple(actual[i:i + 4]) for i in range(0, len(actual), 4)]
        self.assertEqual(actual, [colors[i] for i in (4, 2, 0, 5, 3, 1)])

    def test_opacity_changes_alpha_without_tinting_the_supplied_art(self):
        color = (91, 173, 218, 255)
        width, height, pixels, left, top = sprite_art._affine_rgba(
            4, 6, bytes(color) * 24, 0, .5, 1, 1, "s")
        self.assertEqual((width, height, left, top), (4, 6, -2, -6))
        self.assertEqual(set(tuple(pixels[i:i + 4]) for i in range(0, len(pixels), 4)),
                         {(91, 173, 218, 128)})

    def test_rotated_edges_are_transparent_and_alpha_aware_without_clipping(self):
        color = (90, 170, 220, 255)
        width, height, pixels, _, _ = sprite_art._affine_rgba(
            20, 30, bytes(color) * 600, 36, 1, 1, 1, "s")
        self.assertGreater(width, 20)
        self.assertGreater(height, 30)
        actual = [tuple(pixels[i:i + 4]) for i in range(0, len(pixels), 4)]
        self.assertTrue(any(pixel[3] == 0 for pixel in actual))
        self.assertTrue(any(0 < pixel[3] < 255 for pixel in actual))
        self.assertTrue(all(pixel[:3] == color[:3] for pixel in actual if pixel[3]))
        self.assertAlmostEqual(sum(pixel[3] for pixel in actual) / 255, 600, delta=2)

    def test_stagger_stretch_is_about_the_bottom_anchor(self):
        width, height, _, left, top = sprite_art._affine_rgba(
            20, 30, bytes((120, 130, 140, 255)) * 600, 0, 1, 1.2, .6, "s")
        self.assertEqual((width, height, left, top), (24, 18, -12, -18))
        self.assertEqual(top + height, 0)

    def test_real_single_hand_layers_split_only_at_a_verified_transparent_gap(self):
        for key in ("sword_shield", "rogue_rapier"):
            with self.subTest(key=key):
                path, modified, size = sprite_art._asset_path(key)
                width, height, original = sprite_art._sprite_pixels(key, str(path), modified, size)
                self.assertFalse(any(original[(y * width + width // 2) * 4 + 3] for y in range(height)))
                layers = [sprite_art._hand_layer_pixels(key, str(path), modified, size, layer)
                          for layer in ("offhand", "weapon")]
                self.assertTrue(all(layer[:2] == (width, height) for layer in layers))
                left, right = layers[0][2], layers[1][2]
                self.assertEqual(sum(left[3::4]) + sum(right[3::4]), sum(original[3::4]))
                self.assertFalse(any(a and b for a, b in zip(left[3::4], right[3::4])))
                self.assertTrue(any(left[3::4]))
                self.assertTrue(any(right[3::4]))
                scaled = [sprite_art._decode_png(sprite_art.render_sprite_png(
                    key, 720, 248, layer=layer))[2] for layer in (None, "offhand", "weapon")]
                for i in range(0, len(scaled[0]), 4):
                    original_pixel = scaled[0][i:i + 4]
                    actual = scaled[1][i:i + 4] if scaled[1][i + 3] else scaled[2][i:i + 4]
                    if original_pixel[3]:
                        self.assertEqual(actual, original_pixel)

    def test_explicit_forearm_pivot_stays_in_place_during_rotation(self):
        pixels = bytearray(10 * 10 * 4)
        pixels[(9 * 10 + 8) * 4:(9 * 10 + 9) * 4] = bytes((80, 170, 230, 255))
        width, _, actual, left, top = sprite_art._affine_rgba(
            10, 10, pixels, 90, 1, 1, 1, "center", pivot=(.85, .95))
        points = [(left + (i // 4) % width + .5, top + (i // 4) // width + .5)
                  for i in range(0, len(actual), 4) if actual[i + 3]]
        self.assertEqual(points, [(3.5, 4.5)])

    def test_raised_weapon_sleeve_continues_past_the_viewport_bottom(self):
        path, modified, size = sprite_art._asset_path("sword_shield")
        width, height, original = sprite_art._scaled_sprite(
            "sword_shield", 720, 248, str(path), modified, size, "weapon")
        extended_height, extended = sprite_art._continue_forearm(width, height, original)
        self.assertEqual(extended[:len(original)], original)
        bottom_alpha = original[(height - 1) * width * 4 + 3:height * width * 4:4]
        for row in range(height, extended_height):
            self.assertEqual(extended[row * width * 4 + 3:(row + 1) * width * 4:4], bottom_alpha)
        png, left, top = sprite_art._posed_sprite(
            "sword_shield", 720, 248, str(path), modified, size,
            -24, 1, 1, 1, "s", "weapon", (.88, 1))
        output_width, _, pixels = sprite_art._decode_png(png)
        lowest = max((i // 4) // output_width for i in range(0, len(pixels), 4) if pixels[i + 3])
        self.assertGreater(333 + top + lowest, 420)
        png, left, top = sprite_art._posed_sprite(
            "sword_shield", 720, 248, str(path), modified, size,
            0, 1, 1, 1, "s", "weapon", (.88, 1))
        output_width, _, pixels = sprite_art._decode_png(png)
        self.assertEqual(pixels[:len(original)], original)
        self.assertEqual((left, top), (-width / 2, -height))
        lowest = max((i // 4) // output_width for i in range(0, len(pixels), 4) if pixels[i + 3])
        self.assertGreater(389 + top + lowest, 420)

    def test_real_tk_shield_and_weapon_use_independent_images_and_motion(self):
        import tkinter as tk
        try:
            window = tk.Tk()
        except tk.TclError as error:
            self.skipTest(f"A Tk display is required for the independent arm check: {error}")
        self.addCleanup(window.destroy)
        window.withdraw()
        canvas = tk.Canvas(window, width=1000, height=400)
        view = {"scene": "dungeon", "class_id": "fighter", "floor": 1}
        draw_dungeon_view(canvas, 1000, 400, view)
        shield = canvas.find_withtag("view-offhand")[0]
        weapon = canvas.find_withtag("view-weapon")[0]
        initial_shield = (canvas.coords(shield), canvas.itemcget(shield, "image"))
        initial_weapon = (canvas.coords(weapon), canvas.itemcget(weapon, "image"))
        draw_dungeon_view(canvas, 1000, 400, view, animation={
            "hands_dx": -34, "hands_dy": -70, "hands_angle": -24})
        shield = canvas.find_withtag("view-offhand")[0]
        weapon = canvas.find_withtag("view-weapon")[0]
        self.assertEqual((canvas.coords(shield), canvas.itemcget(shield, "image")), initial_shield)
        self.assertNotEqual((canvas.coords(weapon), canvas.itemcget(weapon, "image")), initial_weapon)
        draw_dungeon_view(canvas, 1000, 400, view, animation={
            "hands_dx": -34, "hands_dy": -70, "hands_angle": -24,
            "offhand_dx": -18, "offhand_dy": 24, "offhand_angle": -6, "offhand_scale": .9})
        shield = canvas.find_withtag("view-offhand")[0]
        self.assertNotEqual((canvas.coords(shield), canvas.itemcget(shield, "image")), initial_shield)
        self.assertEqual(canvas.find_withtag("view-shield"), (shield,))
        self.assertEqual(len(canvas.find_withtag("sprite-sword_shield")), 2)

    def test_quantized_pose_reuses_native_images_and_both_caches_are_bounded(self):
        pose_cache = sprite_art._posed_sprite
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pose_fixture.png").write_bytes(sprite_art._encode_png(
                2, 3, bytes((65, 112, 173, 255)) * 6))
            with patch.object(sprite_art, "ASSET_ROOT", root), patch.dict(
                    sprite_art.SPRITE_CELLS, {"pose_fixture": ("pose_fixture.png", 1, 1, 0)}), patch(
                    "tkinter.PhotoImage", side_effect=lambda **kwargs: object()), patch.object(
                    sprite_art, "_posed_sprite", wraps=sprite_art._posed_sprite) as posed:
                canvas = ImageCanvas()
                for x, angle in ((20, 13), (23, 14)):
                    self.assertTrue(sprite_art.draw_sprite(
                        canvas, "pose_fixture", x, 40, 20, 30, anchor="s",
                        angle=angle, opacity=.8, stretch_x=1.03))
                self.assertEqual(posed.call_count, 1)
                self.assertIs(canvas.images[0][2]["image"], canvas.images[1][2]["image"])
                self.assertEqual(canvas.images[0][2]["anchor"], "nw")
                self.assertEqual(canvas.images[1][0] - canvas.images[0][0], 3)
                for width in range(21, 81):
                    self.assertTrue(sprite_art.draw_sprite(
                        canvas, "pose_fixture", 0, 0, width, 30, angle=12, anchor="s"))
                self.assertLessEqual(len(canvas._dungeon_sprite_images), sprite_art._MAX_IMAGES)
                self.assertLessEqual(pose_cache.cache_info().currsize, sprite_art._MAX_POSES)

    def test_fully_faded_pose_does_not_create_an_image_or_vector_fallback(self):
        canvas = ImageCanvas()
        with patch.object(sprite_art, "_asset_path", return_value=(Path("unused"), 1, 1)), patch(
                "tkinter.PhotoImage") as photo:
            self.assertTrue(sprite_art.draw_sprite(canvas, "rat", 50, 50, 30, 20, opacity=0))
            photo.assert_not_called()
        self.assertFalse(canvas.images)


if __name__ == "__main__":
    unittest.main()
