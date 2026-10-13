"""Treasure carried by the forgotten chambers of Thalinor."""

from dataclasses import dataclass

from equipment import (
    ARMOR_SLOTS, DEFAULT_ARMOR, DEFAULT_WEAPONS, EquipmentItem,
    armor_affix_options, equipment_options, make_equipment,
)


# Every category receives its own roll. A room can contain several categories,
# or nothing at all; neither a potion nor a magic item is guaranteed.
ROOM_LOOT_CHANCES = {
    "cache": {"gold": 0.75, "potions": 0.35, "valuable": 0.40, "trinket": 0.15, "equipment": 0.30},
    "monster": {"gold": 0.30, "potions": 0.15, "valuable": 0.20, "trinket": 0.10, "equipment": 0.15},
    "guardian": {"gold": 0.70, "potions": 0.35, "valuable": 0.50, "trinket": 0.25, "equipment": 0.30},
}

# These are conditional on finding equipment, not chances per room. Mundane
# equipment is always possible. A +3 item on floor one is exceptionally rare:
# 0.1% of equipment finds, or 0.03% of ordinary cache searches.
ENCHANTMENT_WEIGHTS = {
    1: {0: 70000, 1: 27000, 2: 2900, 3: 100},
    2: {0: 55000, 1: 35000, 2: 9500, 3: 500},
    3: {0: 40000, 1: 40000, 2: 18000, 3: 2000},
    4: {0: 25000, 1: 42000, 2: 28000, 3: 5000},
    5: {0: 15000, 1: 40000, 2: 35000, 3: 10000},
}

# Conditional on finding an enchanted armor piece; otherwise it has its normal
# AC enchantment alone. The affix increases a score/check by the gear's +1..+3.
ARMOR_AFFIX_CHANCES = {1: 0.20, 2: 0.30, 3: 0.40}


def _validate_floor(floor: int) -> None:
    if not isinstance(floor, int) or isinstance(floor, bool) or not 1 <= floor <= 5:
        raise ValueError("Invalid treasure floor.")


def _validate_class(class_id: str) -> None:
    if class_id not in ("fighter", "rogue", "wizard"):
        raise ValueError("Invalid treasure class.")


def _validate_bonus(bonus: int) -> None:
    if not isinstance(bonus, int) or isinstance(bonus, bool) or not 0 <= bonus <= 3:
        raise ValueError("Equipment enchantment must be between +0 and +3.")


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
    equipment: tuple[EquipmentItem, ...] = ()

    def __post_init__(self) -> None:
        amounts = (self.gold, self.potions, self.weapon_bonus, self.armor_bonus)
        if any(not isinstance(amount, int) or isinstance(amount, bool) or amount < 0
               for amount in amounts):
            raise ValueError("Loot amounts must be nonnegative whole numbers.")
        _validate_bonus(self.weapon_bonus)
        _validate_bonus(self.armor_bonus)
        for name in (self.weapon_name, self.armor_name):
            if name is not None and (not isinstance(name, str) or not name.strip()):
                raise ValueError("Equipment names cannot be empty.")
        if self.weapon_bonus and not self.weapon_name:
            raise ValueError("A weapon bonus needs a weapon name.")
        if self.armor_bonus and not self.armor_name:
            raise ValueError("An armor bonus needs an armor name.")
        if not isinstance(self.items, tuple) or any(not isinstance(item, TreasureItem) for item in self.items):
            raise ValueError("Loot items must be a tuple of TreasureItem objects.")
        if (not isinstance(self.equipment, tuple)
                or any(not isinstance(item, EquipmentItem) for item in self.equipment)):
            raise ValueError("Loot equipment must be a tuple of EquipmentItem objects.")

    @property
    def has_treasure(self) -> bool:
        return bool(self.gold or self.potions or self.weapon_name or self.items
                    or self.armor_name or self.equipment)


def suitable_weapon_name(class_id: str, bonus: int) -> str:
    """Name the class's default weapon; retained for legacy callers."""
    _validate_class(class_id)
    _validate_bonus(bonus)
    return make_equipment(DEFAULT_WEAPONS[class_id], bonus).name


def suitable_armor_name(class_id: str, bonus: int) -> str:
    _validate_class(class_id)
    _validate_bonus(bonus)
    return make_equipment(DEFAULT_ARMOR[class_id], bonus).name


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
    _validate_floor(floor)
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
    """Legacy fields for one equipment find, including possible mundane gear.

    New room generation uses ``roll_room_loot`` and concrete EquipmentItem
    objects so weapon damage and armor profiles survive collection.
    """
    item = roll_equipment(rng, floor, class_id)
    return {f"{item.kind}_name": item.name, f"{item.kind}_bonus": item.bonus}


def roll_enchantment(rng, floor: int) -> int:
    """Select +0 through +3 using the floor's cumulative rarity table."""
    _validate_floor(floor)
    weights = ENCHANTMENT_WEIGHTS[floor]
    roll = rng.randrange(sum(weights.values()))
    cumulative = 0
    for bonus, weight in weights.items():
        cumulative += weight
        if roll < cumulative:
            return bonus
    raise RuntimeError("The enchantment table does not cover its random range.")


def roll_equipment(rng, floor: int, class_id: str) -> EquipmentItem:
    """Find a usable weapon or armor, then roll its enchantment separately."""
    _validate_floor(floor)
    _validate_class(class_id)
    kind = "weapon" if rng.random() < 0.5 else "armor"
    options = equipment_options(class_id, kind)
    if kind == "armor":
        slot = rng.choice(ARMOR_SLOTS)
        options = tuple(spec for spec in options if spec.slot == slot)
    spec = rng.choice(options)
    bonus = roll_enchantment(rng, floor)
    affix = ""
    if kind == "armor" and bonus and rng.random() < ARMOR_AFFIX_CHANCES[bonus]:
        affix = rng.choice(armor_affix_options(class_id))
    return make_equipment(spec.id, bonus, affix)


def roll_room_loot(rng, floor: int, class_id: str, source: str = "cache") -> Loot:
    """Roll a room's discoverable contents once, without guaranteed upgrades.

    ``cache`` means a room without a foe. ``monster`` and ``guardian`` describe
    their rooms' searchable treasure, separate from a defeated foe's fixed
    combat reward. The caller stores this result so ``look`` and ``loot`` do
    not reroll it. Empty bundles are legitimate results.
    """
    _validate_floor(floor)
    _validate_class(class_id)
    if not isinstance(source, str) or source not in ROOM_LOOT_CHANCES:
        raise ValueError("Invalid room treasure source.")

    found = {category: rng.random() < chance
             for category, chance in ROOM_LOOT_CHANCES[source].items()}
    gold_ranges = {"cache": (8, 20), "monster": (4, 10), "guardian": (12, 30)}
    minimum, maximum = gold_ranges[source]
    gold = rng.randint(minimum * floor, maximum * floor) if found["gold"] else 0
    potions = 1 if found["potions"] else 0
    items = []
    if found["valuable"]:
        items.append(valuable(floor, rng.randrange(4)))
    if found["trinket"]:
        items.append(ember_stone() if rng.random() < 0.5 else mana_draught())
    equipment = (roll_equipment(rng, floor, class_id),) if found["equipment"] else ()
    return Loot(gold=gold, potions=potions, items=tuple(items), equipment=equipment)


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
