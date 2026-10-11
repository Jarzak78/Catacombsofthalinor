"""Treasure carried by the forgotten chambers of Thalinor."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TreasureItem:
    """A carried valuable or usable trinket; value is gold per item."""

    id: str
    name: str
    description: str
    value: int
    kind: str
    amount: int = 1

    def __post_init__(self) -> None:
        if not self.id or not self.name or not self.description:
            raise ValueError("Treasure needs an id, name, and description.")
        if self.kind not in ("valuable", "ember", "mana"):
            raise ValueError("Unknown treasure kind.")
        if (not isinstance(self.value, int) or isinstance(self.value, bool)
                or not isinstance(self.amount, int) or isinstance(self.amount, bool)
                or self.value < 0 or self.amount < 1):
            raise ValueError("Treasure value cannot be negative and amount must be positive.")


@dataclass(frozen=True)
class Loot:
    """A treasure bundle that can be claimed once from its room."""

    gold: int = 0
    potions: int = 0
    weapon_name: str | None = None
    weapon_bonus: int = 0
    items: tuple[TreasureItem, ...] = ()
    armor_name: str | None = None
    armor_bonus: int = 0

    def __post_init__(self) -> None:
        amounts = (self.gold, self.potions, self.weapon_bonus, self.armor_bonus)
        if any(not isinstance(amount, int) or isinstance(amount, bool) or amount < 0
               for amount in amounts):
            raise ValueError("Loot amounts must be nonnegative whole numbers.")
        for name in (self.weapon_name, self.armor_name):
            if name is not None and (not isinstance(name, str) or not name.strip()):
                raise ValueError("Equipment names cannot be empty.")
        if self.weapon_bonus and not self.weapon_name:
            raise ValueError("A weapon bonus needs a weapon name.")
        if self.armor_bonus and not self.armor_name:
            raise ValueError("An armor bonus needs an armor name.")
        if not isinstance(self.items, tuple) or any(not isinstance(item, TreasureItem) for item in self.items):
            raise ValueError("Loot items must be a tuple of TreasureItem objects.")

    @property
    def has_treasure(self) -> bool:
        return bool(self.gold or self.potions or self.weapon_name or self.items or self.armor_name)


def suitable_weapon_name(class_id: str, bonus: int) -> str:
    """Name an upgrade that the selected adventurer can actually use."""
    names = {"fighter": "Thalinor Longsword", "rogue": "Thalinor Rapier", "wizard": "Runic Staff"}
    if class_id not in names or bonus < 0:
        raise ValueError("Invalid weapon class or bonus.")
    return f"{names[class_id]} +{bonus}"


def suitable_armor_name(class_id: str, bonus: int) -> str:
    names = {"fighter": "Runic mail", "rogue": "Runic leather", "wizard": "Runic robes"}
    if class_id not in names or bonus < 0:
        raise ValueError("Invalid armor class or bonus.")
    return f"{names[class_id]} +{bonus}"


# Valuables remain in the pack until sold. Deeper floors hold richer stones
# and jewelry, rather than immediately converting every discovery to gold.
_GEMS = (
    ("emerald", "Moss emerald", "A green stone threaded with the pale veins of buried roots.", 7),
    ("sapphire", "Twilight sapphire", "A blue gemstone that catches the lantern's light like deep water.", 10),
    ("onyx", "Polished onyx", "A jet-black stone polished smooth by an unknown artisan.", 14),
    ("moonstone", "Veiled moonstone", "A milky gemstone with a silver shimmer hidden beneath its surface.", 19),
    ("ruby", "Heartfire ruby", "A crimson stone whose center glows with the color of banked embers.", 25),
)
_JEWELRY = (
    ("silver_ring", "Engraved silver ring", "A silver band engraved with the crest of a forgotten house.", 9),
    ("amber_brooch", "Amber brooch", "An amber pin preserves a tiny golden leaf beneath its polished face.", 12),
    ("gold_locket", "Sealed gold locket", "A small gold locket bears a faded portrait behind its clasp.", 17),
)


def valuable(floor: int, variant: int = 0) -> TreasureItem:
    """Create one floor-themed gem or a piece of jewelry with a stable id."""
    if not 1 <= floor <= 5:
        raise ValueError("Invalid treasure floor.")
    if variant == 0:
        item_id, name, description, value = _GEMS[floor - 1]
    else:
        item_id, name, description, value = _JEWELRY[(variant - 1) % len(_JEWELRY)]
        value += 3 * (floor - 1)
        item_id += f"_f{floor}"
    return TreasureItem(item_id, name, description, value, "valuable")


def ember_stone() -> TreasureItem:
    return TreasureItem("ember", "Ember stone", "A warm red crystal: consume it as an action to deal 3d6 fire damage.", 9, "ember")


def mana_draught() -> TreasureItem:
    return TreasureItem("mana", "Mana draught", "A silver-blue draught that restores one spent first-level wizard spell slot.", 9, "mana")


def rare_equipment(rng, floor: int, class_id: str) -> dict:
    """Choose one class-appropriate upgrade; the caller controls rarity."""
    tier = min(floor + 1, 5)
    if rng.random() < 0.5:
        return {"weapon_name": suitable_weapon_name(class_id, tier), "weapon_bonus": tier}
    return {"armor_name": suitable_armor_name(class_id, tier), "armor_bonus": tier}


HEALER_CACHE = Loot(gold=4, potions=1)
TRAVELER_CACHE = Loot(gold=8, potions=1)
GUARDIAN_CACHE = Loot(gold=6, potions=1)
RUNEBLADE_CACHE = Loot(gold=12, weapon_name="Thalinor Longsword +1", weapon_bonus=1)

TREASURE_BUNDLES = (
    HEALER_CACHE,
    TRAVELER_CACHE,
    GUARDIAN_CACHE,
    RUNEBLADE_CACHE,
)
