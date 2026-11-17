"""The desktop ships complete original art and its provenance from any source form."""

import base64
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zlib

from scripts.verify_art_assets import (
    AssetError, REQUIRED_ATLASES, REQUIRED_ROOM_ATLASES, png_info, stage_art_assets, verify_embedded_art,
)
from scripts import build_windows


def png(width=192, height=192, *, alpha=True, shade=0):
    """A small real PNG fixture produced entirely with the standard library."""
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))
    color = 6 if alpha else 2
    channels = 4 if alpha else 3
    header = struct.pack(">IIBBBBB", width, height, 8, color, 0, 0, 0)
    pixels = b"".join(b"\0" + bytes((shade,)) * (width * channels) for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b""))


def project(root):
    art = root / "assets" / "realistic"
    art.mkdir(parents=True)
    manifest = {"source": "Original generated art fixture", "license_scope": "Project-specific"}
    (art / "asset_sources.json").write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    for name in REQUIRED_ATLASES:
        (art / name).write_bytes(png())
    rooms = root / "assets" / "rooms"
    rooms.mkdir()
    atlases = []
    for floor, name in enumerate(REQUIRED_ROOM_ATLASES, 1):
        data = png(384, 384, alpha=False, shade=floor)
        (rooms / name).write_bytes(data)
        atlases.append({"file": name, "floor": floor, "columns": 2, "rows": 6,
                        "sha256": hashlib.sha256(data).hexdigest()})
    doorways = png(192, 320, alpha=True, shade=7)
    (rooms / "doorways.png").write_bytes(doorways)
    (rooms / "asset_sources.json").write_text(json.dumps({
        "source": "Original generated room fixture", "atlases": atlases,
        "doorways": {"file": "doorways.png", "columns": 3, "rows": 5,
                     "sha256": hashlib.sha256(doorways).hexdigest()}}), encoding="utf-8")
    return art


class AssetPackagingTests(unittest.TestCase):
    def test_all_atlases_and_provenance_are_preserved_byte_for_byte(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = project(root)
            staged, records = stage_art_assets(root, root / "build" / "artwork")
            self.assertEqual(len(records), 10)
            for original in (root / "assets").rglob("*"):
                if not original.is_file():
                    continue
                self.assertEqual(original.read_bytes(),
                                 (staged / original.relative_to(root / "assets")).read_bytes())
            for record in records:
                data = (root / record["path"]).read_bytes()
                self.assertEqual(record["sha256"], hashlib.sha256(data).hexdigest())
                self.assertEqual(record["png_sha256"], record["sha256"])
                size = ((192, 320) if record["path"].endswith("doorways.png") else
                        (384, 384) if "/rooms/" in record["path"] else (192, 192))
                self.assertEqual((record["width"], record["height"]), size)

    def test_base64_source_form_is_supported_without_changing_the_art(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = project(root)
            original = (source / "hands.png").read_bytes()
            (source / "hands.png").unlink()
            encoded = base64.encodebytes(original)
            (source / "hands.png.b64").write_bytes(encoded)
            staged, records = stage_art_assets(root, root / "build" / "artwork")
            record = next(row for row in records if row["path"].endswith("hands.png.b64"))
            self.assertEqual(record["sha256"], hashlib.sha256(encoded).hexdigest())
            self.assertEqual(record["png_sha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual((staged / "realistic/hands.png.b64").read_bytes(), encoded)

    def test_missing_required_atlas_prevents_a_partial_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = project(root)
            (source / "enemies.png").unlink()
            destination = root / "build" / "artwork"
            with self.assertRaisesRegex(AssetError, "enemies.png"):
                stage_art_assets(root, destination)
            self.assertFalse(destination.exists())

    def test_missing_empty_or_invalid_provenance_prevents_release(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = project(root)
            manifest = source / "asset_sources.json"
            for invalid in (b"", b"{}", b"[]", b"not JSON"):
                with self.subTest(data=invalid):
                    manifest.write_bytes(invalid)
                    with self.assertRaises(AssetError):
                        stage_art_assets(root, root / "build/artwork")
            manifest.unlink()
            with self.assertRaises(AssetError):
                stage_art_assets(root, root / "build/artwork")

    def test_truncated_corrupted_or_opaque_pngs_are_rejected(self):
        original = png()
        corrupted = bytearray(original)
        corrupted[-6] ^= 1
        for data in (b"not a PNG", original[:33], original[:-1], bytes(corrupted), png(alpha=False)):
            with self.subTest(size=len(data)), self.assertRaises(AssetError):
                png_info(data, "fixture.png")

    def test_invalid_base64_and_disagreeing_duplicate_sources_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = project(root)
            fallback = source / "hands.png.b64"
            fallback.write_bytes(b"%%% not base64 %%%")
            with self.assertRaisesRegex(AssetError, "base64"):
                stage_art_assets(root, root / "build/artwork")
            fallback.write_bytes(base64.b64encode(png(200, 192)))
            with self.assertRaisesRegex(AssetError, "disagree"):
                stage_art_assets(root, root / "build/artwork")

    def test_opaque_room_atlases_are_allowed_but_character_sprites_still_need_alpha(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = project(root)
            staged, records = stage_art_assets(root, root / "build/artwork")
            self.assertEqual(sum("/rooms/floor_" in record["path"] for record in records), 5)
            self.assertTrue((staged / "rooms/floor_5.png").is_file())
            (source / "hands.png").write_bytes(png(alpha=False))
            with self.assertRaisesRegex(AssetError, "transparency"):
                stage_art_assets(root, root / "build/artwork")

    def test_missing_room_atlas_or_provenance_stops_release_before_staging(self):
        for name in ("floor_1.png", "floor_5.png", "doorways.png", "asset_sources.json"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                project(root)
                (root / "assets/rooms" / name).unlink()
                destination = root / "build/artwork"
                with self.assertRaisesRegex(AssetError, name):
                    stage_art_assets(root, destination)
                self.assertFalse(destination.exists())

    def test_room_hashes_reject_changed_or_swapped_floor_art(self):
        for replace in ("changed", "swapped"):
            with self.subTest(replace=replace), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                project(root)
                rooms = root / "assets/rooms"
                data = (rooms / "floor_2.png").read_bytes() if replace == "swapped" else png(384, 384, alpha=False, shade=99)
                (rooms / "floor_1.png").write_bytes(data)
                with self.assertRaisesRegex(AssetError, "provenance hash"):
                    stage_art_assets(root, root / "build/artwork")

    def test_room_provenance_rejects_incomplete_duplicate_or_wrong_grid_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project(root)
            path = root / "assets/rooms/asset_sources.json"
            original = json.loads(path.read_text())
            for change in ("missing", "duplicate", "grid", "floor", "digest", "nondict"):
                with self.subTest(change=change):
                    record = json.loads(json.dumps(original))
                    if change == "missing":
                        record["atlases"].pop()
                    elif change == "duplicate":
                        record["atlases"][1] = record["atlases"][0]
                    elif change == "grid":
                        record["atlases"][0]["rows"] = 5
                    elif change == "floor":
                        record["atlases"][0]["floor"] = 2
                    elif change == "digest":
                        record["atlases"][0]["sha256"] = "z" * 64
                    else:
                        record["atlases"][0] = "floor_1.png"
                    path.write_text(json.dumps(record), encoding="utf-8")
                    with self.assertRaises(AssetError):
                        stage_art_assets(root, root / "build/artwork")

    def test_room_atlas_dimensions_and_corruption_are_checked_before_hashes(self):
        for data, error in ((png(256, 256, alpha=False), "too small"),
                            (png(384, 768, alpha=False), "square"),
                            (png(384, 384, alpha=False)[:-1], "Truncated")):
            with self.subTest(error=error), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                project(root)
                (root / "assets/rooms/floor_1.png").write_bytes(data)
                with self.assertRaisesRegex(AssetError, error):
                    stage_art_assets(root, root / "build/artwork")

    def test_base64_room_atlases_preserve_decoded_provenance_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project(root)
            path = root / "assets/rooms/floor_1.png"
            original = path.read_bytes()
            path.unlink()
            path.with_suffix(".png.b64").write_bytes(base64.encodebytes(original))
            staged, records = stage_art_assets(root, root / "build/artwork")
            record = next(row for row in records if row["path"].endswith("floor_1.png.b64"))
            self.assertEqual(record["png_sha256"], hashlib.sha256(original).hexdigest())
            self.assertEqual((staged / "rooms/floor_1.png.b64").read_bytes(), base64.encodebytes(original))

    def test_doorway_portrait_requires_transparency_size_and_matching_hash(self):
        for replacement, error in ((png(192, 320, alpha=False), "transparency"),
                                   (png(96, 96), "too small"),
                                   (png(192, 320, alpha=True, shade=99), "provenance hash")):
            with self.subTest(error=error), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                project(root)
                (root / "assets/rooms/doorways.png").write_bytes(replacement)
                with self.assertRaisesRegex(AssetError, error):
                    stage_art_assets(root, root / "build/artwork")

    def test_doorway_provenance_requires_the_authored_cutout_grid(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project(root)
            path = root / "assets/rooms/asset_sources.json"
            original = json.loads(path.read_text())
            for change in ("missing", "file", "grid", "hash"):
                with self.subTest(change=change):
                    record = json.loads(json.dumps(original))
                    if change == "missing":
                        del record["doorways"]
                    elif change == "file":
                        record["doorways"]["file"] = "floor_1.png"
                    elif change == "grid":
                        record["doorways"]["columns"] = 2
                    else:
                        record["doorways"]["sha256"] = "invalid"
                    path.write_text(json.dumps(record), encoding="utf-8")
                    with self.assertRaisesRegex(AssetError, "doorway"):
                        stage_art_assets(root, root / "build/artwork")

    def test_an_atlas_must_have_room_for_each_sprite_cell(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = project(root)
            (source / "enemies.png").write_bytes(png(96, 96))
            with self.assertRaisesRegex(AssetError, "too small"):
                stage_art_assets(root, root / "build/artwork")

    def test_every_embedded_atlas_and_its_provenance_must_match(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project(root)
            staged, _ = stage_art_assets(root, root / "build/artwork")
            entries = {("assets/" + file.relative_to(staged).as_posix()).replace("/", "\\"): file.read_bytes()
                       for file in staged.rglob("*") if file.is_file()}
            archive = SimpleNamespace(toc=entries, extract=lambda name: entries[name])
            readers = SimpleNamespace(CArchiveReader=lambda _path: archive)
            with patch.dict("sys.modules", {"PyInstaller.archive.readers": readers}):
                verify_embedded_art(Path("game.exe"), staged)
                entries["assets\\realistic\\asset_sources.json"] = b"changed"
                with self.assertRaisesRegex(AssetError, "missing or altered"):
                    verify_embedded_art(Path("game.exe"), staged)
                del entries["assets\\realistic\\asset_sources.json"]
                with self.assertRaisesRegex(AssetError, "missing or altered"):
                    verify_embedded_art(Path("game.exe"), staged)

    def test_windows_build_embeds_art_only_in_desktop_and_retains_readable_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = project(root)
            notices = root / "build" / "license-bundle"
            (notices / "legal").mkdir(parents=True)
            (notices / "CREDITS.txt").write_bytes(b"SRD credit fixture")
            (notices / "legal" / "license.txt").write_bytes(b"License fixture")
            calls = []

            def run(arguments, **_kwargs):
                calls.append(arguments)
                if "PyInstaller" in arguments:
                    name = arguments[arguments.index("--name") + 1]
                    executable = root / "dist" / (name + ".exe")
                    executable.parent.mkdir(exist_ok=True)
                    executable.write_bytes(("packaged " + name).encode())
                return SimpleNamespace(stdout=b"System Reference Document", returncode=0)

            with patch.object(build_windows, "ROOT", root), \
                    patch.object(build_windows.sys, "platform", "win32"), \
                    patch.object(build_windows.sys, "version_info", (3, 12, 10)), \
                    patch.object(build_windows, "version", return_value="6.16.0"), \
                    patch.object(build_windows, "collect_notices", return_value=notices), \
                    patch.object(build_windows, "verify_embedded_notices"), \
                    patch.object(build_windows, "verify_embedded_art") as verify, \
                    patch.object(build_windows, "audit_analysis", return_value=[]), \
                    patch("sys.stdout", new_callable=io.StringIO), \
                    patch.object(build_windows.subprocess, "run", side_effect=run):
                self.assertEqual(build_windows.main(), 0)
            builds = [arguments for arguments in calls if "PyInstaller" in arguments]
            self.assertEqual(len(builds), 2)
            self.assertTrue(any(str(argument).endswith(":assets") for argument in builds[0]))
            self.assertFalse(any(str(argument).endswith(":assets") for argument in builds[1]))
            verify.assert_called_once()
            self.assertEqual((source / "asset_sources.json").read_bytes(),
                             (root / "dist/legal/artwork-sources.json").read_bytes())
            self.assertEqual((root / "assets/rooms/asset_sources.json").read_bytes(),
                             (root / "dist/legal/room-artwork-sources.json").read_bytes())
            manifest = json.loads((root / "dist/build-manifest.json").read_text())
            self.assertEqual(len(manifest["executables"][0]["artwork"]), 10)
            self.assertEqual(manifest["executables"][1]["artwork"], [])
            self.assertEqual(manifest["artwork_provenance"]["sha256"],
                             hashlib.sha256((source / "asset_sources.json").read_bytes()).hexdigest())
            self.assertEqual(manifest["room_artwork_provenance"]["sha256"],
                             hashlib.sha256((root / "assets/rooms/asset_sources.json").read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
