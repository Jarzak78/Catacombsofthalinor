"""Original raster sprites with smooth, alpha-aware scaling using only stdlib.

Art remains separate from gameplay.  Decoded atlas pixels and a bounded set of
Tk images are cached, and each Canvas keeps its own image references alive.
"""

from collections import OrderedDict
from functools import lru_cache
from pathlib import Path
import base64
import math
import struct
import zlib


ASSET_ROOT = Path(__file__).resolve().parent / "assets" / "realistic"
SPRITE_CELLS = {
    "sword_shield": ("hands.png", 1, 3, 0),
    "rogue_rapier": ("hands.png", 1, 3, 1),
    "wizard_staff": ("hands.png", 1, 3, 2),
    "greatsword": ("weapons.png", 1, 3, 0),
    "rogue_dagger": ("weapons.png", 1, 3, 1),
    "greataxe": ("weapons.png", 1, 3, 2),
    **{key: ("enemies.png", 3, 3, index) for index, key in enumerate((
        "skeleton", "rat", "armored", "beetle", "serpent", "wisp",
        "fungal", "construct", "ooze"))},
    **{key: ("guardians.png", 3, 2, index) for index, key in enumerate((
        "warden", "sentinel", "colossus", "void_knight", "hollow_king", "mira"))},
}
# Authored separators differ slightly from the nominal grid: the greatsword
# ends at y=565, and the wizard begins just after a one-row grip fragment.
# Normalized regions preserve those boundaries at any atlas resolution.
SPRITE_REGIONS = {
    "greatsword": (0, 0, 1, 565 / 1536),
    "rogue_dagger": (0, 565 / 1536, 1, 1024 / 1536),
    "wizard_staff": (0, 1025 / 1536, 1, 1),
}
_MAX_IMAGES = 48
_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def hand_sprite_key(view):
    """Choose a supplied grip from the character's public equipped-weapon ID."""
    weapon = view.get("weapon_id", "")
    if weapon == "greataxe":
        return "greataxe"
    if weapon == "dagger":
        return "rogue_dagger"
    if view.get("class_id") == "wizard":
        return "wizard_staff"
    if view.get("two_handed"):
        return "greatsword"
    if view.get("class_id") == "rogue":
        return "rogue_rapier"
    return "sword_shield"


def enemy_sprite_key(enemy, floor):
    """Select an original avatar using only already-visible foe information."""
    if enemy.get("boss"):
        index = floor - 1 if type(floor) is int and 1 <= floor <= 5 else 0
        return ("warden", "sentinel", "colossus", "void_knight", "hollow_king")[index]
    kind = str(enemy.get("archetype", "humanoid")).casefold()
    name = str(enemy.get("name", "")).casefold()
    if kind == "rat":
        return "rat"
    if kind == "insect":
        return "beetle"
    if kind == "serpent":
        return "serpent"
    if kind == "ooze":
        return "ooze"
    if any(word in name for word in ("automaton", "colossus", "forge sentinel")) or kind == "construct":
        return "construct"
    if any(word in name for word in ("mold", "fung", "briar", "rootbound", "effigy")):
        return "fungal"
    if kind in ("wisp", "specter", "spectre", "shadow"):
        return "wisp"
    if any(word in name for word in ("bone", "skeleton", "remnant", "ghoul", "revenant")):
        return "skeleton"
    return "armored"


def _asset_path(key):
    name = SPRITE_CELLS[key][0]
    path = ASSET_ROOT / name
    if not path.is_file():
        path = ASSET_ROOT / (name + ".b64")
    info = path.stat()
    return path, info.st_mtime_ns, info.st_size


def _paeth(a, b, c):
    guess = a + b - c
    da, db, dc = abs(guess - a), abs(guess - b), abs(guess - c)
    return a if da <= db and da <= dc else b if db <= dc else c


def _decode_png(data):
    """Read the non-interlaced 8-bit PNG formats used by the supplied art."""
    if not data.startswith(_SIGNATURE):
        raise ValueError("Sprite is not a PNG")
    offset, compressed, palette, transparency = 8, bytearray(), b"", b""
    width = height = channels = color = None
    while offset + 12 <= len(data):
        length = struct.unpack_from(">I", data, offset)[0]
        kind = data[offset + 4:offset + 8]
        end = offset + 8 + length
        if end + 4 > len(data):
            raise ValueError("Truncated sprite PNG")
        payload = data[offset + 8:end]
        if zlib.crc32(kind + payload) & 0xffffffff != struct.unpack_from(">I", data, end)[0]:
            raise ValueError("Sprite PNG checksum failed")
        if kind == b"IHDR":
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(color)
            if (depth != 8 or channels is None or compression or filtering or interlace
                    or not 0 < width <= 8192 or not 0 < height <= 8192
                    or width * height > 16_777_216):
                raise ValueError("Unsupported sprite PNG format")
        elif kind == b"PLTE":
            palette = payload
        elif kind == b"tRNS":
            transparency = payload
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
        offset = end + 4
    if channels is None:
        raise ValueError("Sprite PNG has no header")
    stride = width * channels
    packed = zlib.decompress(compressed)
    if len(packed) != (stride + 1) * height:
        raise ValueError("Unexpected sprite PNG pixel count")
    pixels, previous = bytearray(), bytearray(stride)
    for row in range(height):
        start = row * (stride + 1)
        filtering = packed[start]
        current = bytearray(packed[start + 1:start + 1 + stride])
        if filtering not in range(5):
            raise ValueError("Unsupported sprite PNG filter")
        if filtering:
            for index in range(stride):
                left = current[index - channels] if index >= channels else 0
                above = previous[index]
                upper_left = previous[index - channels] if index >= channels else 0
                correction = (left if filtering == 1 else above if filtering == 2 else
                              (left + above) // 2 if filtering == 3 else _paeth(left, above, upper_left))
                current[index] = (current[index] + correction) & 255
        pixels.extend(current)
        previous = current
    if color == 6:
        return width, height, bytes(pixels)
    rgba = bytearray()
    transparent_rgb = tuple(struct.unpack(">HHH", transparency)) if color == 2 and len(transparency) == 6 else None
    transparent_gray = struct.unpack(">H", transparency)[0] if color == 0 and len(transparency) == 2 else None
    for index in range(0, len(pixels), channels):
        if color == 2:
            rgb = tuple(pixels[index:index + 3])
            rgba.extend((*rgb, 0 if rgb == transparent_rgb else 255))
        elif color == 3:
            entry = pixels[index]
            rgb = palette[entry * 3:entry * 3 + 3]
            if len(rgb) != 3:
                raise ValueError("Invalid sprite PNG palette")
            rgba.extend((*rgb, transparency[entry] if entry < len(transparency) else 255))
        else:
            gray = pixels[index]
            alpha = pixels[index + 1] if color == 4 else 0 if gray == transparent_gray else 255
            rgba.extend((gray, gray, gray, alpha))
    return width, height, bytes(rgba)


@lru_cache(maxsize=4)
def _atlas(path, modified, size):
    data = Path(path).read_bytes()
    if str(path).endswith(".b64"):
        data = base64.b64decode(data, validate=False)
    return _decode_png(data)


@lru_cache(maxsize=24)
def _sprite_pixels(key, path, modified, size):
    width, height, pixels = _atlas(path, modified, size)
    _, columns, rows, index = SPRITE_CELLS[key]
    column, row = index % columns, index // columns
    left, right = width * column // columns, width * (column + 1) // columns
    top, bottom = height * row // rows, height * (row + 1) // rows
    if key in SPRITE_REGIONS:
        x1, y1, x2, y2 = SPRITE_REGIONS[key]
        left, right = (max(0, min(width, round(value * width))) for value in (x1, x2))
        top, bottom = (max(0, min(height, round(value * height))) for value in (y1, y2))
        if left >= right or top >= bottom:
            raise ValueError("Sprite source region is empty")
    # Trim empty tile margins without changing any nontransparent artwork.
    x1, y1, x2, y2 = right, bottom, left - 1, top - 1
    for y in range(top, bottom):
        for x in range(left, right):
            if pixels[(y * width + x) * 4 + 3] > 0:
                x1, x2 = min(x1, x), max(x2, x)
                y1, y2 = min(y1, y), max(y2, y)
    if x2 < x1 or y2 < y1:
        raise ValueError("Sprite cell is transparent")
    cropped = b"".join(pixels[(y * width + x1) * 4:(y * width + x2 + 1) * 4]
                       for y in range(y1, y2 + 1))
    return x2 - x1 + 1, y2 - y1 + 1, cropped


def _resize_rgba(width, height, pixels, output_width, output_height):
    """Bilinear filtering in premultiplied alpha prevents dark edge halos."""
    if (width, height) == (output_width, output_height):
        return pixels
    output = bytearray(output_width * output_height * 4)
    horizontal = []
    for x in range(output_width):
        source = max(0, min(width - 1, (x + .5) * width / output_width - .5))
        first = int(source)
        horizontal.append((first * 4, min(first + 1, width - 1) * 4, source - first))
    for y in range(output_height):
        source = max(0, min(height - 1, (y + .5) * height / output_height - .5))
        first = int(source)
        row1, row2, fy = first * width * 4, min(first + 1, height - 1) * width * 4, source - first
        for x, (x1, x2, fx) in enumerate(horizontal):
            locations = (row1 + x1, row1 + x2, row2 + x1, row2 + x2)
            weights = ((1 - fx) * (1 - fy), fx * (1 - fy), (1 - fx) * fy, fx * fy)
            alpha_weights = tuple(pixels[position + 3] * weight
                                  for position, weight in zip(locations, weights))
            alpha = sum(alpha_weights)
            destination = (y * output_width + x) * 4
            if alpha:
                for channel in range(3):
                    output[destination + channel] = round(sum(
                        pixels[position + channel] * weight
                        for position, weight in zip(locations, alpha_weights)) / alpha)
            output[destination + 3] = round(alpha)
    return bytes(output)


def _encode_png(width, height, rgba):
    def chunk(kind, payload):
        return (struct.pack(">I", len(payload)) + kind + payload
                + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff))
    rows = b"".join(b"\0" + rgba[y * width * 4:(y + 1) * width * 4]
                    for y in range(height))
    return (_SIGNATURE + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b""))


def render_sprite_png(key, target_width, target_height):
    """Return a smoothly scaled transparent PNG, fitted inside the target box."""
    if (not math.isfinite(target_width) or not math.isfinite(target_height)
            or target_width <= 0 or target_height <= 0):
        raise ValueError("Sprite target must have positive finite dimensions")
    path, modified, size = _asset_path(key)
    width, height, pixels = _sprite_pixels(key, str(path), modified, size)
    scale = min(min(target_width, 2048) / width, min(target_height, 2048) / height)
    output_width, output_height = max(1, round(width * scale)), max(1, round(height * scale))
    scaled = _resize_rgba(width, height, pixels, output_width, output_height)
    return _encode_png(output_width, output_height, scaled)


def draw_sprite(canvas, key, x, y, target_width, target_height, anchor="center", tags=()):
    """Draw a cached raster sprite or return False for the vector fallback."""
    if not hasattr(canvas, "tk") or not hasattr(canvas, "create_image") or key not in SPRITE_CELLS:
        return False
    try:
        import tkinter as tk
        path, modified, size = _asset_path(key)
        width, height = round(target_width), round(target_height)
        cache_key = (key, width, height, str(path), modified, size)
        images = getattr(canvas, "_dungeon_sprite_images", None)
        if images is None:
            images = canvas._dungeon_sprite_images = OrderedDict()
        if cache_key not in images:
            encoded = render_sprite_png(key, width, height)
            images[cache_key] = tk.PhotoImage(master=canvas, data=encoded, format="png")
        images.move_to_end(cache_key)
        while len(images) > _MAX_IMAGES:
            images.popitem(last=False)
        canvas.create_image(x, y, image=images[cache_key], anchor=anchor,
                            tags=(*tags, "view-sprite", "sprite-" + key))
        return True
    except (OSError, ValueError, KeyError, OverflowError, struct.error, zlib.error, tk.TclError):
        return False
