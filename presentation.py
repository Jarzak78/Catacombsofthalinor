"""Semantic colors for desktop and console adapters; engine messages stay plain.

Classifying or rendering text never reads adventure state or consumes dice.
Redirected console output remains plain for logs, launchers, and screen readers.
"""

import os
import re
import sys

from floor_lore import LORE
from loot_flavor import discovery_description, preview_description
from room import Room


TAG_COLORS = {
    "room": "#81d98e",
    "item": "#9ddcff",
    "dialogue": "#d6b8ff",
    "combat": "#ffb08d",
    "healing": "#9ce4c5",
    "command": "#dfb565",
    "notice": "#c5d1df",
    "log": "#dce2e7",
}

_ANSI = {
    "room": "\033[92m",
    "item": "\033[96m",
    "dialogue": "\033[95m",
    "combat": "\033[91m",
    "healing": "\033[92m",
    "command": "\033[93m",
    "notice": "\033[97m",
    "log": "\033[37m",
}
_RESET = "\033[0m"


def _authored_room_text() -> frozenset[str]:
    text = set()
    for floor, lore in enumerate(LORE, 1):
        text.update((lore.arrival, lore.revelation))
        for name, description in (lore.entrance, lore.sanctum, *lore.rooms):
            text.update((name, description))
            room = Room((0, 0), name, description, {})
            text.update((discovery_description(room, floor), preview_description(room, floor)))
    # Unknown-room fixtures and future room templates retain the authored
    # fallback color without inspecting their hidden contents.
    room = Room((0, 0), "", "", {})
    text.update((discovery_description(room, 0), preview_description(room, 0)))
    return frozenset(text)


_ROOM_TEXT = _authored_room_text()
_ITEM_PREFIXES = (
    "Description:", "Item:", "Damage dice:", "Damage:", "Slot:", "Rarity:",
    "Protection:", "Buff:", "Buffs:", "Properties:", "Proficiency:",
    "Enchantment:", "Sell value:", "Price:", "Weapon:", "Armor:",
    "You find ", "You uncover ", "You collect ", "Bought ", "You equip ",
)
_ITEM_ROW = re.compile(r"^[a-z][a-z0-9_]*: \S")
_COMBAT = re.compile(
    r"\bhits?\b|\bmiss(?:es)?\b|\bcritical\b|\bfumble\b|\b\d+ damage\b",
    re.IGNORECASE,
)


def classify_message(line: str) -> str:
    """Identify a message's display role from authored text and stable labels."""
    line = line.strip()
    if line.startswith("> "):
        return "command"
    if line.startswith("Mira:"):
        return "dialogue"
    if line in _ROOM_TEXT or line.startswith((
        "Floor ", "Exits:", "Among the dusty belongings, you glimpse ",
        "Something here may be worth a closer search.", "You spot a document:",
        "A glowing portal is open.",
    )):
        return "room"
    if line.startswith(_ITEM_PREFIXES) or _ITEM_ROW.match(line):
        return "item"
    lower = line.casefold()
    if ("restore" in lower or "recover" in lower or "regain" in lower
            or "heals you" in lower) and ("hp" in lower or "spell slot" in lower
                                          or "resources" in lower):
        return "healing"
    if _COMBAT.search(line) or line.startswith((
        "Sneak Attack:", "Initiative:", "Opening Hide:", "Stealth:",
        "Perception check:", "Perception save:", "Combat:",
    )) or "blocks your way!" in line or "You die in the catacombs" in line:
        return "combat"
    if line.startswith(("Use '", "Type '", "Browse with '", "Buy with '",
                        "Sell ", "Equip ", "Menu:", "Sanctuary menu", "Mira's sanctuary")):
        return "command"
    if not line or line.startswith(("Gold:", "Mira's stock", "Inventory", "Your pack")):
        return "notice"
    return "log"


def format_message(line: str, color: bool = False) -> str:
    """Apply a console color only when the caller has an interactive console."""
    if not color or not line:
        return line
    return _ANSI[classify_message(line)] + line + _RESET


def _enable_windows_vt(stream) -> bool:
    """Enable ANSI for this process's console handle without persistent changes."""
    try:
        import ctypes
        from ctypes import wintypes
        import msvcrt

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetConsoleMode.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        kernel.GetConsoleMode.restype = wintypes.BOOL
        kernel.SetConsoleMode.argtypes = (wintypes.HANDLE, wintypes.DWORD)
        kernel.SetConsoleMode.restype = wintypes.BOOL
        handle = wintypes.HANDLE(msvcrt.get_osfhandle(stream.fileno()))
        mode = wintypes.DWORD()
        if not kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel.SetConsoleMode(handle, mode.value | 0x0004))
    except (AttributeError, ImportError, OSError, ValueError):
        return False


def enable_terminal_colors(stream=None, environ=None) -> bool:
    """Respect NO_COLOR and leave redirected output free of escape sequences."""
    stream = sys.stdout if stream is None else stream
    environ = os.environ if environ is None else environ
    if stream is None or "NO_COLOR" in environ:
        return False
    try:
        if not stream.isatty():
            return False
    except (AttributeError, OSError, ValueError):
        return False
    if os.name == "nt":
        return _enable_windows_vt(stream)
    return environ.get("TERM") != "dumb"


def print_messages(lines, stream=None) -> None:
    """Print an engine response with line-specific colors on interactive stdout."""
    stream = sys.stdout if stream is None else stream
    if stream is None:
        return
    color = enable_terminal_colors(stream)
    rendered = (format_message(line, color) for message in lines for line in message.split("\n"))
    print("\n".join(rendered), file=stream)
