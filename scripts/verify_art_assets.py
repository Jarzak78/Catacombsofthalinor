"""Stage and verify the original raster artwork used by the desktop build.

The release preserves the generated files and their provenance. PNG inspection
uses the standard library; it does not add a runtime imaging dependency.
"""

import base64
import binascii
import hashlib
import json
from pathlib import Path
import shutil
import struct
import zlib


REQUIRED_ATLASES = {
    "hands.png": (1, 3),
    "weapons.png": (1, 3),
    "enemies.png": (3, 3),
    "guardians.png": (3, 2),
}
REQUIRED_ROOM_ATLASES = {f"floor_{floor}.png": (2, 6) for floor in range(1, 6)}
DOORWAY_ATLAS = "doorways.png"
DOORWAY_GRID = (3, 5)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class AssetError(RuntimeError):
    """A required artwork file, provenance record, or embedded copy is invalid."""


def png_info(data: bytes, source: str, *, require_transparency: bool = True) -> dict:
    """Inspect the complete PNG container, not just its identifying bytes."""
    if not data.startswith(PNG_SIGNATURE):
        raise AssetError(f"Artwork is not a PNG: {source}")
    cursor = len(PNG_SIGNATURE)
    dimensions = None
    has_data = False
    has_transparency = False
    while cursor < len(data):
        if len(data) - cursor < 12:
            raise AssetError(f"Truncated PNG artwork: {source}")
        size = struct.unpack_from(">I", data, cursor)[0]
        end = cursor + 12 + size
        if end > len(data):
            raise AssetError(f"Truncated PNG artwork: {source}")
        kind = data[cursor + 4:cursor + 8]
        payload = data[cursor + 8:cursor + 8 + size]
        crc = struct.unpack_from(">I", data, cursor + 8 + size)[0]
        if zlib.crc32(kind + payload) & 0xFFFFFFFF != crc:
            raise AssetError(f"PNG artwork has an invalid checksum: {source}")
        if dimensions is None:
            if kind != b"IHDR" or size != 13:
                raise AssetError(f"PNG artwork is missing its header: {source}")
            width, height, depth, color, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", payload)
            if (not 0 < width <= 8192 or not 0 < height <= 8192
                    or depth not in (1, 2, 4, 8, 16)
                    or color not in (0, 2, 3, 4, 6)
                    or compression != 0 or filtering != 0 or interlace not in (0, 1)):
                raise AssetError(f"PNG artwork has an unsupported header: {source}")
            dimensions = {"width": width, "height": height}
            has_transparency = color in (4, 6)
        elif kind == b"IHDR":
            raise AssetError(f"PNG artwork has duplicate headers: {source}")
        if kind == b"IDAT":
            has_data = has_data or bool(payload)
        elif kind == b"tRNS":
            has_transparency = bool(payload)
        elif kind == b"IEND":
            if size != 0 or end != len(data) or not has_data:
                raise AssetError(f"PNG artwork is incomplete: {source}")
            if require_transparency and not has_transparency:
                raise AssetError(f"PNG sprite artwork needs transparency: {source}")
            return dimensions
        cursor = end
    raise AssetError(f"PNG artwork has no end marker: {source}")


def _provenance(manifest: Path) -> dict:
    try:
        provenance = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise AssetError(f"A valid artwork provenance record is required: {manifest}") from error
    if not isinstance(provenance, dict) or not provenance:
        raise AssetError(f"The artwork provenance record is empty: {manifest}")
    return provenance


def _room_provenance(manifest: Path) -> dict[str, dict]:
    provenance = _provenance(manifest)
    atlases = provenance.get("atlases")
    if not isinstance(atlases, list) or len(atlases) != len(REQUIRED_ROOM_ATLASES):
        raise AssetError(f"Room artwork provenance must identify all five atlases: {manifest}")
    records = {}
    for record in atlases:
        if not isinstance(record, dict):
            raise AssetError(f"Invalid room artwork provenance entry: {manifest}")
        name = record.get("file")
        floor = record.get("floor")
        digest = record.get("sha256")
        if (not isinstance(name, str) or name not in REQUIRED_ROOM_ATLASES
                or name in records or type(floor) is not int
                or name != f"floor_{floor}.png"
                or record.get("columns") != 2 or record.get("rows") != 6
                or not isinstance(digest, str) or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)):
            raise AssetError(f"Invalid or duplicate room artwork provenance entry: {manifest}")
        records[name] = record
    if set(records) != set(REQUIRED_ROOM_ATLASES):
        raise AssetError(f"Room artwork provenance omits a required atlas: {manifest}")
    doorway = provenance.get("doorways")
    digest = doorway.get("sha256") if isinstance(doorway, dict) else None
    if (not isinstance(doorway, dict) or doorway.get("file") != DOORWAY_ATLAS
            or doorway.get("columns") != DOORWAY_GRID[0]
            or doorway.get("rows") != DOORWAY_GRID[1]
            or not isinstance(digest, str) or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)):
        raise AssetError(f"Valid transparent doorway artwork provenance is required: {manifest}")
    records[DOORWAY_ATLAS] = doorway
    return records


def _read_atlas(path: Path) -> bytes:
    data = path.read_bytes()
    if path.name.endswith(".b64"):
        try:
            data = base64.b64decode(b"".join(data.split()), validate=True)
        except (binascii.Error, ValueError) as error:
            raise AssetError(f"Artwork has invalid base64 data: {path}") from error
    return data


def stage_art_assets(root: Path, destination: Path) -> tuple[Path, list[dict]]:
    """Require sprites, sixty room portraits, and the themed doorway cutouts."""
    source = root / "assets"
    _provenance(source / "realistic" / "asset_sources.json")
    room_sources = _room_provenance(source / "rooms" / "asset_sources.json")
    records = []
    required = [("realistic", name, grid) for name, grid in REQUIRED_ATLASES.items()]
    required += [("rooms", name, grid) for name, grid in REQUIRED_ROOM_ATLASES.items()]
    required.append(("rooms", DOORWAY_ATLAS, DOORWAY_GRID))
    for directory, name, (columns, rows) in required:
        candidates = [source / directory / name, source / directory / (name + ".b64")]
        present = [path for path in candidates if path.is_file()]
        if not present:
            raise AssetError(f"Required original artwork is missing: assets/{directory}/{name}")
        png = _read_atlas(present[0])
        if len(present) > 1 and _read_atlas(present[1]) != png:
            raise AssetError(f"Native and base64 artwork copies disagree: {name}")
        dimensions = png_info(png, str(present[0]),
                              require_transparency=directory == "realistic" or name == DOORWAY_ATLAS)
        if dimensions["width"] < columns * 64 or dimensions["height"] < rows * 64:
            raise AssetError(f"Artwork is too small for its sprite grid: {name}")
        if directory == "rooms":
            if name != DOORWAY_ATLAS and dimensions["width"] != dimensions["height"]:
                raise AssetError(f"Room artwork must use the authored square 2-column, 6-row atlas: {name}")
            if hashlib.sha256(png).hexdigest() != room_sources[name]["sha256"]:
                raise AssetError(f"Room artwork does not match its provenance hash: {name}")
        records.append({"path": present[0].relative_to(root).as_posix(),
                        "sha256": hashlib.sha256(present[0].read_bytes()).hexdigest(),
                        "png_sha256": hashlib.sha256(png).hexdigest(),
                        "columns": columns, "rows": rows, **dimensions})
    if destination.exists():
        shutil.rmtree(destination)
    staged = destination / "assets"
    shutil.copytree(source, staged)
    return staged, records


def verify_embedded_art(executable: Path, staged: Path) -> None:
    """Verify artwork and its source record are embedded byte-for-byte."""
    from PyInstaller.archive.readers import CArchiveReader

    archive = CArchiveReader(str(executable))
    paths = {name.replace("\\", "/"): name for name in archive.toc}
    for source in sorted(staged.rglob("*")):
        if not source.is_file():
            continue
        relative = "assets/" + source.relative_to(staged).as_posix()
        if relative not in paths or archive.extract(paths[relative]) != source.read_bytes():
            raise AssetError(f"Required artwork is missing or altered in {executable.name}: {relative}")
