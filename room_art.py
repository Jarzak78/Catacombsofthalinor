"""Cached, description-matched room backgrounds without an imaging dependency.

The public room-art identifier selects one authored atlas cell.  This module
never receives a dungeon, room contents, an enemy, or the adventure's RNG.
"""

import base64
from collections import OrderedDict
from functools import lru_cache
import math
from pathlib import Path
import struct
import zlib

from room_art_catalog import ATLAS_COLUMNS, ATLAS_ROWS, room_art_by_id
from sprite_art import _decode_png, _encode_png, _resize_rgba


ASSET_ROOT = Path(__file__).resolve().parent / "assets" / "rooms"
ROOM_ART_TAG = "view-room-art"
EXIT_ART_TAG = "view-exit-art"
_MAX_IMAGES = 8
_EXIT_COLUMNS = 3
_EXIT_ROWS = 5
_EXIT_DIRECTIONS = ("left", "front", "right")


def _asset_path(atlas):
    path = ASSET_ROOT / atlas
    if not path.is_file():
        path = ASSET_ROOT / (atlas + ".b64")
    info = path.stat()
    return path, info.st_mtime_ns, info.st_size


def _dimensions(width, height):
    if (not isinstance(width, (int, float)) or isinstance(width, bool)
            or not isinstance(height, (int, float)) or isinstance(height, bool)
            or not math.isfinite(width) or not math.isfinite(height)
            or not 0 < width <= 4096 or not 0 < height <= 2048):
        raise ValueError("Room artwork needs positive, finite viewport dimensions")
    width, height = max(1, round(width)), max(1, round(height))
    if width * height > 4_194_304:
        raise ValueError("Room artwork viewport is too large")
    return width, height


@lru_cache(maxsize=2)
def _atlas_pixels(path, modified, size):
    data = Path(path).read_bytes()
    if path.endswith(".b64"):
        data = base64.b64decode(b"".join(data.split()), validate=True)
    return _decode_png(data)


@lru_cache(maxsize=12)
def _room_pixels(path, modified, size, cell):
    return _grid_pixels(path, modified, size, cell, ATLAS_COLUMNS, ATLAS_ROWS)


def _grid_pixels(path, modified, size, cell, columns, rows):
    width, height, rgba = _atlas_pixels(path, modified, size)
    if width < columns or height < rows:
        raise ValueError("Room artwork is too small for its grid")
    column, row = cell % columns, cell // columns
    left, right = column * width // columns, (column + 1) * width // columns
    top, bottom = row * height // rows, (row + 1) * height // rows
    cropped = b"".join(rgba[(y * width + left) * 4:(y * width + right) * 4]
                       for y in range(top, bottom))
    return right - left, bottom - top, cropped


@lru_cache(maxsize=15)
def _exit_pixels(path, modified, size, cell):
    width, height, rgba = _grid_pixels(path, modified, size, cell, _EXIT_COLUMNS, _EXIT_ROWS)
    # A transparent gutter belongs to the atlas layout, not to the doorway's
    # target footprint. Trim only transparent pixels after isolating its cell.
    left, top, right, bottom = width, height, -1, -1
    for y in range(height):
        for x in range(width):
            if rgba[(y * width + x) * 4 + 3]:
                left, top, right, bottom = min(left, x), min(top, y), max(right, x), max(bottom, y)
    if right < left or bottom < top:
        raise ValueError("Doorway artwork cell is transparent")
    pixels = b"".join(rgba[(y * width + left) * 4:(y * width + right + 1) * 4]
                      for y in range(top, bottom + 1))
    return right - left + 1, bottom - top + 1, pixels


@lru_cache(maxsize=18)
def _rendered_exit_png(path, modified, size, cell, target_width, target_height):
    width, height, rgba = _exit_pixels(path, modified, size, cell)
    scale = min(target_width / width, target_height / height)
    output_width, output_height = max(1, round(width * scale)), max(1, round(height * scale))
    return _encode_png(output_width, output_height,
                       _resize_rgba(width, height, rgba, output_width, output_height))


def _cover_region(width, height, target_width, target_height):
    if width * target_height > height * target_width:
        crop_width = max(1, min(width, round(height * target_width / target_height)))
        crop_height = height
    else:
        crop_width = width
        crop_height = max(1, min(height, round(width * target_height / target_width)))
    left, top = (width - crop_width) // 2, (height - crop_height) // 2
    return left, top, crop_width, crop_height


def _cover_pixels(width, height, rgba, target_width, target_height):
    """Crop within one cell before resizing, so adjacent rooms cannot bleed in."""
    left, top, crop_width, crop_height = _cover_region(width, height, target_width, target_height)
    pixels = b"".join(rgba[(y * width + left) * 4:(y * width + left + crop_width) * 4]
                      for y in range(top, top + crop_height))
    return _resize_rgba(crop_width, crop_height, pixels, target_width, target_height)


@lru_cache(maxsize=12)
def _rendered_room_png(path, modified, size, cell, width, height):
    source_width, source_height, rgba = _room_pixels(path, modified, size, cell)
    pixels = _cover_pixels(source_width, source_height, rgba, width, height)
    return _encode_png(width, height, pixels)


def render_room_png(room_art_id, width, height):
    """Render one known room's opaque artwork to fill a viewport exactly."""
    spec = room_art_by_id(room_art_id)
    if spec is None:
        raise ValueError("Unknown room artwork identifier")
    width, height = _dimensions(width, height)
    path, modified, size = _asset_path(spec.atlas)
    return _rendered_room_png(str(path), modified, size, spec.cell, width, height)


def draw_room_art(canvas, width, height, room_art_id, *, tags=()):
    """Draw the authorized room backdrop, or let the caller use its fallback."""
    spec = room_art_by_id(room_art_id)
    if spec is None or not hasattr(canvas, "tk") or not hasattr(canvas, "create_image"):
        return False
    try:
        import tkinter as tk
        width, height = _dimensions(width, height)
        path, modified, size = _asset_path(spec.atlas)
        cache_key = (spec.id, width, height, str(path), modified, size)
        images = getattr(canvas, "_room_art_images", None)
        if images is None:
            images = canvas._room_art_images = OrderedDict()
        if cache_key not in images:
            encoded = _rendered_room_png(str(path), modified, size, spec.cell, width, height)
            images[cache_key] = tk.PhotoImage(master=canvas, data=encoded, format="png")
        images.move_to_end(cache_key)
        while len(images) > _MAX_IMAGES:
            images.popitem(last=False)
        canvas.create_image(0, 0, image=images[cache_key], anchor="nw",
                            tags=(*tags, ROOM_ART_TAG, "room-art-" + spec.id))
        return True
    except (OSError, ValueError, TypeError, KeyError, OverflowError,
            struct.error, zlib.error, tk.TclError):
        return False


def exit_art_placement(floor, relative, room_art_id=None):
    """Use an authored clear wall, never a room's props, for its far passage."""
    if type(floor) is not int or not 1 <= floor <= _EXIT_ROWS or relative not in _EXIT_DIRECTIONS:
        return None
    spec = room_art_by_id(room_art_id) if room_art_id is not None else None
    if room_art_id is not None and (spec is None or spec.floor != floor):
        return None
    if relative == "front":
        return spec.front_passage if spec is not None else (.5, .775, .16, .60)
    return (0 if relative == "left" else 1, 1.06, .34, 1.05)


def _project_front_passage(spec, width, height, placement):
    """Keep the passage on its painted wall when a viewport crops the scene."""
    path, modified, size = _asset_path(spec.atlas)
    source_width, source_height, _ = _room_pixels(str(path), modified, size, spec.cell)
    left, top, crop_width, crop_height = _cover_region(source_width, source_height, width, height)
    center, bottom, passage_width, passage_height = placement
    return ((center * source_width - left) / crop_width,
            (bottom * source_height - top) / crop_height,
            passage_width * source_width / crop_width,
            passage_height * source_height / crop_height)


def draw_exit_art(canvas, width, height, floor, relative, *, tags=(), room_art_id=None):
    """Blend a matching textured passage into a known room's actual exit."""
    placement = exit_art_placement(floor, relative, room_art_id)
    if placement is None:
        spec = room_art_by_id(room_art_id)
        # A reviewed painting may show a solid landmark across the far wall.
        # Its route remains available in the controls/map; no fake opening is
        # cut through that obstruction and no procedural door replaces it.
        return (type(floor) is int and relative == "front" and spec is not None
                and spec.floor == floor and spec.front_passage is None)
    if not hasattr(canvas, "tk") or not hasattr(canvas, "create_image"):
        return False
    try:
        import tkinter as tk
        width, height = _dimensions(width, height)
        if relative == "front" and room_art_id is not None:
            placement = _project_front_passage(room_art_by_id(room_art_id), width, height, placement)
        path, modified, size = _asset_path("doorways.png")
        cell = (floor - 1) * _EXIT_COLUMNS + _EXIT_DIRECTIONS.index(relative)
        center, bottom, relative_width, relative_height = placement
        # Near-side passages continue beyond the camera's edge. Showing an
        # entire small freestanding arch here would read as a room prop.
        box_width = max(1, round(width * relative_width))
        box_height = max(1, round(height * relative_height))
        cache_key = (floor, relative, box_width, box_height, str(path), modified, size)
        images = getattr(canvas, "_room_exit_images", None)
        if images is None:
            images = canvas._room_exit_images = OrderedDict()
        if cache_key not in images:
            encoded = _rendered_exit_png(str(path), modified, size, cell, box_width, box_height)
            images[cache_key] = tk.PhotoImage(master=canvas, data=encoded, format="png")
        images.move_to_end(cache_key)
        while len(images) > 12:
            images.popitem(last=False)
        x, y = center * width, bottom * height
        canvas.create_image(x, y, image=images[cache_key], anchor="s",
                            tags=(*tags, EXIT_ART_TAG, "exit-art-" + relative))
        return True
    except (OSError, ValueError, TypeError, KeyError, OverflowError,
            struct.error, zlib.error, tk.TclError):
        return False
