"""A restricted, read-only first-person view of the adventurer's current room.

The canvas receives these public facts, never a dungeon object or loot records.
A drawing cannot reveal the contents of a neighboring or unexplored room.
"""

from collections.abc import Mapping

from equipment import EQUIPMENT


DIRECTIONS = ("north", "east", "south", "west")
_TREASURE_KEYS = ("gold", "potions", "weapon_name", "armor_name", "items", "equipment")


def _position(value):
    if (isinstance(value, (tuple, list)) and len(value) == 2
            and all(type(part) is int for part in value)):
        return tuple(value)
    return None


def _foe_archetype(name: str) -> str:
    """Choose an original generic silhouette from an already visible name."""
    name = name.casefold()
    groups = (
        ("rat", ("rat",)),
        ("insect", ("beetle", "mantis", "scuttler", "crawler")),
        ("serpent", ("viper", "serpent", "leech")),
        ("ooze", ("ooze", "slime")),
        ("armored", ("knight", "warden", "sentry", "automaton", "colossus",
                     "jailer", "usher", "harrier", "sentinel", "king")),
        ("wisp", ("wisp", "echo", "shardling", "choir", "fragment", "witness",
                  "hunger", "shadow")),
    )
    return next((kind for kind, words in groups if any(word in name for word in words)),
                "humanoid")


def first_person_data(state: dict, facing: str = "north") -> dict:
    """Return detached visual facts without advancing time, actions, or RNG.

    Only the current *visited* room is eligible. Its open exits become relative
    directions; exit destinations are never copied. A live foe hides room
    features until the room is safe. Loot is a vague presence flag, never a
    concrete item, quantity, value, enchantment, or container contents.
    """
    facing = facing.strip().casefold() if isinstance(facing, str) else "north"
    if facing not in DIRECTIONS:
        facing = "north"
    direction = DIRECTIONS.index(facing)
    player = state.get("player")
    player = player if isinstance(player, Mapping) else {}
    class_id = player.get("class_id", "fighter")
    if class_id not in ("fighter", "rogue", "wizard"):
        class_id = "fighter"
    weapon_id = player.get("weapon_id")
    weapon = EQUIPMENT.get(weapon_id) if isinstance(weapon_id, str) else None
    two_handed = bool(weapon is not None and weapon.kind == "weapon" and weapon.two_handed)
    hp = player.get("hp")
    dead = bool(player.get("dead", False)) or (
        isinstance(hp, (int, float)) and not isinstance(hp, bool) and hp <= 0)
    floor = state.get("floor", 1)
    if type(floor) is not int or not 1 <= floor <= 5:
        floor = 1
    theme = state.get("theme", "Dungeon")
    theme = theme if isinstance(theme, str) else "Dungeon"
    scene = "shop" if state.get("scene") == "shop" else "dungeon"
    encounter = state.get("encounter")
    encounter = encounter if isinstance(encounter, Mapping) else {}
    result = {
        "scene": scene, "floor": floor, "theme": theme, "facing": facing,
        "room_name": "Unexplored chamber",
        "exits": dict.fromkeys(("front", "left", "right", "back"), False),
        "enemy": None, "loot": False, "note": False, "portal": False,
        "class_id": class_id,
        "weapon_id": weapon_id if weapon is not None and weapon.kind == "weapon" else "",
        "two_handed": two_handed,
        "dead": dead, "won": bool(state.get("won", False)),
        "hidden": scene == "dungeon" and bool(encounter.get("hidden", False)),
        "in_combat": False,
    }
    if scene == "shop":
        result["room_name"] = "The Lantern Between Worlds"
        return result

    current = _position(state.get("position"))
    rooms = state.get("rooms", ())
    if current is None or not isinstance(rooms, (tuple, list)):
        return result
    room = next((candidate for candidate in rooms
                 if isinstance(candidate, Mapping)
                 and candidate.get("visited") is True
                 and _position(candidate.get("position")) == current), None)
    if room is None:
        return result
    name = room.get("name", "Dungeon chamber")
    result["room_name"] = name if isinstance(name, str) else "Dungeon chamber"
    exits = room.get("exits")
    exits = exits if isinstance(exits, Mapping) else {}
    result["exits"] = {
        relative: DIRECTIONS[(direction + offset) % 4] in exits
        for relative, offset in (("front", 0), ("left", -1), ("right", 1), ("back", 2))
    }

    enemy = room.get("enemy")
    hp = enemy.get("hp") if isinstance(enemy, Mapping) else None
    living_foe = (isinstance(hp, (int, float))
                  and not isinstance(hp, bool) and hp > 0)
    if living_foe:
        name = enemy.get("name")
        name = name if isinstance(name, str) and name else "Unknown foe"
        result["enemy"] = {"name": name, "boss": bool(enemy.get("boss", False)),
                           "archetype": _foe_archetype(name)}
        result["in_combat"] = not dead and not bool(state.get("over", False))
        return result

    loot = room.get("loot")
    result["loot"] = (isinstance(loot, Mapping)
                      and any(bool(loot.get(key)) for key in _TREASURE_KEYS))
    result["note"] = bool(room.get("note")) and not bool(room.get("note_collected", False))
    result["portal"] = (bool(state.get("portal_open", False))
                        and _position(state.get("portal_position")) == current)
    return result
