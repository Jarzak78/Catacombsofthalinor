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
_MAX_POSES = 48
_SPLIT_HANDS = frozenset(("sword_shield", "rogue_rapier"))
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


@lru_cache(maxsize=8)
def _hand_layer_pixels(key, path, modified, size, layer):
    """Separate disjoint arms while retaining their shared original rectangle.

    The supplied two single-hand grips have a fully transparent center column.
    Check that separation against alpha before splitting; no visible pixels are
    cut, moved, recolored, or resized independently in the idle composition.
    """
    if key not in _SPLIT_HANDS or layer not in ("offhand", "weapon"):
        raise ValueError("Sprite has no separate hand layer")
    width, height, pixels = _sprite_pixels(key, path, modified, size)
    split = width // 2
    if any(pixels[(y * width + split) * 4 + 3] for y in range(height)):
        raise ValueError("Hand layers have no transparent center separation")
    output = bytearray(pixels)
    for y in range(height):
        left, right = ((split, width) if layer == "offhand" else (0, split))
        start, end = (y * width + left) * 4, (y * width + right) * 4
        output[start:end] = bytes(end - start)
    return width, height, bytes(output)


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


@lru_cache(maxsize=24)
def _scaled_sprite(key, target_width, target_height, path, modified, size, layer=None):
    """Share the expensive base resize between all poses of an avatar."""
    width, height, pixels = (_hand_layer_pixels(key, path, modified, size, layer) if layer
                             else _sprite_pixels(key, path, modified, size))
    scale = min(min(target_width, 2048) / width, min(target_height, 2048) / height)
    output_width, output_height = max(1, round(width * scale)), max(1, round(height * scale))
    return (output_width, output_height,
            _resize_rgba(width, height, pixels, output_width, output_height))


def _target_size(target_width, target_height):
    if (not math.isfinite(target_width) or not math.isfinite(target_height)
            or target_width <= 0 or target_height <= 0):
        raise ValueError("Sprite target must have positive finite dimensions")


def render_sprite_png(key, target_width, target_height, *, layer=None):
    """Return a smoothly scaled transparent PNG, fitted inside the target box."""
    _target_size(target_width, target_height)
    path, modified, size = _asset_path(key)
    width, height, pixels = _scaled_sprite(key, target_width, target_height, str(path), modified, size, layer)
    return _encode_png(width, height, pixels)


def _pose_values(angle, opacity, stretch_x, stretch_y):
    """A few reusable key poses keep animation out of the PNG decoder hot path."""
    if not all(math.isfinite(value) for value in (angle, opacity, stretch_x, stretch_y)):
        raise ValueError("Sprite pose must be finite")
    if stretch_x <= 0 or stretch_y <= 0:
        raise ValueError("Sprite stretch must be positive")
    return (round(max(-90, min(90, angle)) / 6) * 6,
            round(max(0, min(1, opacity)) * 4) / 4,
            max(.1, round(min(2.5, stretch_x) * 10) / 10),
            max(.1, round(min(2.5, stretch_y) * 10) / 10))


def _affine_rgba(width, height, pixels, angle, opacity, stretch_x, stretch_y, anchor="center", *,
                 pivot=None, layout_height=None):
    """Rotate/stretch around the Canvas anchor without clipping or dark halos.

    The returned offset positions the expanded PNG relative to that unchanged
    anchor.  Feet stay planted when a foe leans, and grips pivot at the screen
    edge.  Transparent pixels contribute alpha rather than dark edge colors.
    """
    anchors = {"center": (.5, .5), "n": (.5, 0), "s": (.5, 1),
               "e": (1, .5), "w": (0, .5), "ne": (1, 0), "nw": (0, 0),
               "se": (1, 1), "sw": (0, 1)}
    ax, ay = anchors.get(anchor, anchors["center"])
    layout_height = height if layout_height is None else layout_height
    anchor_x, anchor_y = width * ax, layout_height * ay
    if angle == 0 and stretch_x == 1 and stretch_y == 1:
        if opacity != 1:
            output = bytearray(pixels)
            output[3::4] = bytes(round(alpha * opacity) for alpha in pixels[3::4])
            pixels = bytes(output)
        return width, height, pixels, -anchor_x, -anchor_y
    pivot_x, pivot_y = ((width * pivot[0], layout_height * pivot[1]) if pivot
                        else (anchor_x, anchor_y))
    shift_x, shift_y = pivot_x - anchor_x, pivot_y - anchor_y
    radians = math.radians(angle)
    cosine, sine = math.cos(radians), math.sin(radians)
    cosine = 0 if abs(cosine) < 1e-10 else cosine
    sine = 0 if abs(sine) < 1e-10 else sine
    corners = []
    for x, y in ((0, 0), (width, 0), (width, height), (0, height)):
        x, y = (x - pivot_x) * stretch_x, (y - pivot_y) * stretch_y
        corners.append((x * cosine - y * sine + shift_x, x * sine + y * cosine + shift_y))
    left = math.floor(min(point[0] for point in corners) + 1e-8)
    top = math.floor(min(point[1] for point in corners) + 1e-8)
    right = math.ceil(max(point[0] for point in corners) - 1e-8)
    bottom = math.ceil(max(point[1] for point in corners) - 1e-8)
    output_width, output_height = max(1, right - left), max(1, bottom - top)
    output = bytearray(output_width * output_height * 4)
    step_x, step_y = cosine / stretch_x, -sine / stretch_y
    for y in range(output_height):
        wx, wy = left + .5 - shift_x, top + y + .5 - shift_y
        source_x = (wx * cosine + wy * sine) / stretch_x + pivot_x - .5
        source_y = (-wx * sine + wy * cosine) / stretch_y + pivot_y - .5
        for x in range(output_width):
            x1, y1 = math.floor(source_x), math.floor(source_y)
            fx, fy = source_x - x1, source_y - y1
            destination = (y * output_width + x) * 4
            if 0 <= x1 < width - 1 and 0 <= y1 < height - 1:
                p1 = (y1 * width + x1) * 4
                p2, p3, p4 = p1 + 4, p1 + width * 4, p1 + width * 4 + 4
                a1 = pixels[p1 + 3] * (1 - fx) * (1 - fy)
                a2 = pixels[p2 + 3] * fx * (1 - fy)
                a3 = pixels[p3 + 3] * (1 - fx) * fy
                a4 = pixels[p4 + 3] * fx * fy
                alpha = a1 + a2 + a3 + a4
                if alpha:
                    for channel in range(3):
                        output[destination + channel] = round((pixels[p1 + channel] * a1
                            + pixels[p2 + channel] * a2 + pixels[p3 + channel] * a3
                            + pixels[p4 + channel] * a4) / alpha)
                    output[destination + 3] = round(alpha * opacity)
            elif -1 <= x1 < width and -1 <= y1 < height:
                samples = []
                for px, py, weight in ((x1, y1, (1 - fx) * (1 - fy)),
                                       (x1 + 1, y1, fx * (1 - fy)),
                                       (x1, y1 + 1, (1 - fx) * fy),
                                       (x1 + 1, y1 + 1, fx * fy)):
                    if weight > 1e-10 and 0 <= px < width and 0 <= py < height:
                        position = (py * width + px) * 4
                        samples.append((position, pixels[position + 3] * weight))
                alpha = sum(weight for _, weight in samples)
                if alpha:
                    for channel in range(3):
                        output[destination + channel] = round(sum(
                            pixels[position + channel] * weight for position, weight in samples) / alpha)
                    output[destination + 3] = round(alpha * opacity)
            source_x += step_x
            source_y += step_y
    return output_width, output_height, bytes(output), left, top


def _continue_forearm(width, height, pixels):
    """Continue the cropped sleeve with its own texture beneath the viewport.

    Raising an arm exposes the atlas's straight bottom crop.  Reuse a short,
    mirrored band of that same sleeve below the cut so the arm remains joined
    to the screen edge throughout its reach, with its original alpha silhouette.
    """
    depth = max(1, round(height * .8))
    band = max(1, min(24, height - 1))
    edge = pixels[(height - 1) * width * 4:height * width * 4]
    output = bytearray(pixels)
    for y in range(depth):
        phase = y % (band * 2)
        source_y = height - 1 - (phase if phase < band else band * 2 - 1 - phase)
        row = bytearray(edge)
        source = source_y * width * 4
        for x in range(width):
            i = x * 4
            if edge[i + 3] and pixels[source + i + 3]:
                row[i:i + 3] = pixels[source + i:source + i + 3]
        output.extend(row)
    return height + depth, bytes(output)


@lru_cache(maxsize=_MAX_POSES)
def _posed_sprite(key, width, height, path, modified, size, angle, opacity,
                  stretch_x, stretch_y, anchor, layer=None, pivot=None):
    width, height, pixels = _scaled_sprite(key, width, height, path, modified, size, layer)
    layout_height = height
    if layer == "weapon":
        height, pixels = _continue_forearm(width, height, pixels)
    width, height, pixels, left, top = _affine_rgba(
        width, height, pixels, angle, opacity, stretch_x, stretch_y, anchor,
        pivot=pivot, layout_height=layout_height)
    return _encode_png(width, height, pixels), left, top


def draw_sprite(canvas, key, x, y, target_width, target_height, anchor="center", tags=(), *,
                angle=0, opacity=1, stretch_x=1, stretch_y=1, layer=None, pivot=None):
    """Draw a cached raster sprite or return False for the vector fallback."""
    if not hasattr(canvas, "tk") or not hasattr(canvas, "create_image") or key not in SPRITE_CELLS:
        return False
    try:
        import tkinter as tk
        _target_size(target_width, target_height)
        if pivot is not None:
            if len(pivot) != 2 or not all(math.isfinite(value) and 0 <= value <= 1 for value in pivot):
                raise ValueError("Sprite pivot must be inside its original rectangle")
            pivot = tuple(pivot)
        path, modified, size = _asset_path(key)
        width, height = round(target_width), round(target_height)
        pose = _pose_values(angle, opacity, stretch_x, stretch_y)
        if pose[1] == 0:
            return True
        posed = layer == "weapon" or pose != (0, 1, 1, 1)
        cache_key = (key, width, height, str(path), modified, size, pose, anchor, layer, pivot)
        images = getattr(canvas, "_dungeon_sprite_images", None)
        if images is None:
            images = canvas._dungeon_sprite_images = OrderedDict()
        if cache_key not in images:
            if posed:
                encoded, left, top = _posed_sprite(
                    key, width, height, str(path), modified, size, *pose, anchor, layer, pivot)
            else:
                encoded, left, top = render_sprite_png(key, width, height, layer=layer), 0, 0
            images[cache_key] = (tk.PhotoImage(master=canvas, data=encoded, format="png"), left, top)
        images.move_to_end(cache_key)
        while len(images) > _MAX_IMAGES:
            images.popitem(last=False)
        photo, left, top = images[cache_key]
        canvas.create_image(x + left, y + top, image=photo, anchor="nw" if posed else anchor,
                            tags=(*tags, "view-sprite", "sprite-" + key))
        return True
    except (OSError, ValueError, KeyError, OverflowError, struct.error, zlib.error, tk.TclError):
        return False
