"""D&D-inspired equipment definitions, independent of characters and loot.

Weapons and armor use familiar tabletop damage dice, armor classes, and
enchantment bonuses. Prices suit this five-floor solo campaign rather than
the tabletop economy. The three wizard vestments are homebrew clothing;
they remain unarmored so Mage Armor can improve their base protection.
"""

from dataclasses import dataclass
import re


MAX_ENCHANTMENT = 3
RARITIES = ("mundane", "uncommon", "rare", "very rare")
ARMOR_RARITIES = ("mundane", "rare", "very rare", "legendary")
_CLASS_IDS = ("fighter", "rogue", "wizard")
_WEAPON_SURCHARGES = (0, 35, 80, 140)
_ARMOR_SURCHARGES = (0, 30, 65, 115)


@dataclass(frozen=True)
class EquipmentSpec:
    """One mundane equipment type and the classes proficient with it."""

    id: str
    name: str
    kind: str
    classes: tuple[str, ...]
    base_price: int
    description: str
    damage_dice: tuple[int, int] = (1, 4)
    finesse: bool = False
    two_handed: bool = False
    mastery: str = ""
    base_ac: int = 10
    dex_cap: int | None = None
    unarmored: bool = False
    stealth_disadvantage: bool = False
    focus: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not re.fullmatch(r"[a-z]+(?:_[a-z]+)*", self.id):
            raise ValueError("Equipment IDs must contain lowercase words joined by underscores.")
        if self.kind not in ("weapon", "armor"):
            raise ValueError("Equipment kind must be weapon or armor.")
        if not isinstance(self.classes, tuple) or not self.classes:
            raise ValueError("Equipment must specify a tuple of proficient classes.")
        if any(class_id not in _CLASS_IDS for class_id in self.classes):
            raise ValueError("Equipment classes must be fighter, rogue, or wizard.")
        if len(set(self.classes)) != len(self.classes):
            raise ValueError("Equipment classes cannot contain duplicates.")
        if type(self.base_price) is not int or self.base_price < 1:
            raise ValueError("Equipment price must be a positive integer.")
        if (not isinstance(self.damage_dice, tuple) or len(self.damage_dice) != 2
                or any(type(die) is not int or die < 1 for die in self.damage_dice)):
            raise ValueError("Equipment damage dice must be two positive integers.")
        if self.mastery not in ("", "sap", "vex"):
            raise ValueError("Equipment mastery must be sap, vex, or empty.")
        if type(self.base_ac) is not int or self.base_ac < 0:
            raise ValueError("Equipment base AC must be a nonnegative integer.")
        if self.dex_cap is not None and (type(self.dex_cap) is not int or self.dex_cap < 0):
            raise ValueError("Equipment Dexterity cap must be nonnegative or None.")


EQUIPMENT: dict[str, EquipmentSpec] = {
    "longsword": EquipmentSpec(
        "longsword", "Longsword", "weapon", ("fighter",), 10,
        "A balanced steel blade, wielded one-handed. Sap hinders a struck foe's next attack.",
        damage_dice=(1, 8), mastery="sap"),
    "battleaxe": EquipmentSpec(
        "battleaxe", "Battleaxe", "weapon", ("fighter",), 10,
        "A broad-headed, one-handed axe for powerful cleaving strikes.",
        damage_dice=(1, 8)),
    "warhammer": EquipmentSpec(
        "warhammer", "Warhammer", "weapon", ("fighter",), 10,
        "A one-handed hammer with a heavy iron head for crushing blows.",
        damage_dice=(1, 8)),
    "greatsword": EquipmentSpec(
        "greatsword", "Greatsword", "weapon", ("fighter",), 35,
        "A massive two-handed blade. Its broad cuts roll two damage dice; it cannot use a shield.",
        damage_dice=(2, 6), two_handed=True),
    "greataxe": EquipmentSpec(
        "greataxe", "Greataxe", "weapon", ("fighter",), 30,
        "A heavy two-handed axe with a wide damage range; it cannot use a shield.",
        damage_dice=(1, 12), two_handed=True),
    "mace": EquipmentSpec(
        "mace", "Mace", "weapon", ("fighter",), 5,
        "A simple one-handed crushing weapon. Sap hinders a struck foe's next attack.",
        damage_dice=(1, 6), mastery="sap"),
    "spear": EquipmentSpec(
        "spear", "Spear", "weapon", ("fighter",), 4,
        "A sturdy one-handed spear used for close thrusts in narrow passages.",
        damage_dice=(1, 6)),
    "rapier": EquipmentSpec(
        "rapier", "Rapier", "weapon", ("fighter", "rogue"), 12,
        "A precise finesse blade. Vex grants advantage on the next attack against a struck foe.",
        damage_dice=(1, 8), finesse=True, mastery="vex"),
    "shortsword": EquipmentSpec(
        "shortsword", "Shortsword", "weapon", ("fighter", "rogue"), 7,
        "A compact finesse blade. Vex grants advantage on the next attack against a struck foe.",
        damage_dice=(1, 6), finesse=True, mastery="vex"),
    "dagger": EquipmentSpec(
        "dagger", "Dagger", "weapon", _CLASS_IDS, 2,
        "A light finesse blade, carried as a close-combat weapon rather than a spell focus.",
        damage_dice=(1, 4), finesse=True),
    "scimitar": EquipmentSpec(
        "scimitar", "Scimitar", "weapon", ("fighter", "rogue"), 10,
        "A curved finesse blade suited to quick, close cuts.",
        damage_dice=(1, 6), finesse=True),
    "quarterstaff": EquipmentSpec(
        "quarterstaff", "Quarterstaff", "weapon", ("fighter", "wizard"), 3,
        "A wooden staff used one-handed. Enchantment improves its physical strikes, not spells.",
        damage_dice=(1, 6)),
    "arcane_staff": EquipmentSpec(
        "arcane_staff", "Arcane Staff", "weapon", ("wizard",), 15,
        "A staff with an inset crystal focus. An enchanted version improves weapon and spell attacks.",
        damage_dice=(1, 6), focus=True),
    "padded": EquipmentSpec(
        "padded", "Padded Armor", "armor", ("fighter", "rogue"), 5,
        "Quilted light armor adds Dexterity to AC; its bulky folds hinder stealth.",
        base_ac=11, stealth_disadvantage=True),
    "leather": EquipmentSpec(
        "leather", "Leather Armor", "armor", ("fighter", "rogue"), 8,
        "Flexible light armor adds the full Dexterity modifier to AC.",
        base_ac=11),
    "studded_leather": EquipmentSpec(
        "studded_leather", "Studded Leather", "armor", ("fighter", "rogue"), 20,
        "Reinforced light armor adds the full Dexterity modifier to AC without hindering stealth.",
        base_ac=12),
    "scale_mail": EquipmentSpec(
        "scale_mail", "Scale Mail", "armor", ("fighter",), 25,
        "Overlapping scales add up to +2 Dexterity to AC and hinder stealth.",
        base_ac=14, dex_cap=2, stealth_disadvantage=True),
    "breastplate": EquipmentSpec(
        "breastplate", "Breastplate", "armor", ("fighter",), 45,
        "A fitted medium breastplate adds up to +2 Dexterity to AC without hindering stealth.",
        base_ac=14, dex_cap=2),
    "half_plate": EquipmentSpec(
        "half_plate", "Half Plate", "armor", ("fighter",), 70,
        "Partial plate armor adds up to +2 Dexterity to AC and hinders stealth.",
        base_ac=15, dex_cap=2, stealth_disadvantage=True),
    "chain_mail": EquipmentSpec(
        "chain_mail", "Chain Mail", "armor", ("fighter",), 25,
        "Heavy interlocked rings provide fixed protection and hinder stealth; Dexterity does not alter AC.",
        base_ac=16, dex_cap=0, stealth_disadvantage=True),
    "splint": EquipmentSpec(
        "splint", "Splint Armor", "armor", ("fighter",), 65,
        "Heavy metal strips provide fixed protection and hinder stealth; Dexterity does not alter AC.",
        base_ac=17, dex_cap=0, stealth_disadvantage=True),
    "plate": EquipmentSpec(
        "plate", "Plate Armor", "armor", ("fighter",), 120,
        "A full heavy harness provides fixed protection and hinders stealth; Dexterity does not alter AC.",
        base_ac=18, dex_cap=0, stealth_disadvantage=True),
    "robes": EquipmentSpec(
        "robes", "Robes", "armor", ("wizard",), 5,
        "Ordinary unarmored clothing adds Dexterity to AC and permits Mage Armor.",
        base_ac=10, unarmored=True),
    "warded_robes": EquipmentSpec(
        "warded_robes", "Warded Robes", "armor", ("wizard",), 15,
        "Homebrew protective vestments add Dexterity to AC and remain unarmored for Mage Armor.",
        base_ac=11, unarmored=True),
    "battlemage_robes": EquipmentSpec(
        "battlemage_robes", "Battlemage Robes", "armor", ("wizard",), 30,
        "Homebrew reinforced vestments add Dexterity to AC and remain unarmored for Mage Armor.",
        base_ac=12, unarmored=True),
}

DEFAULT_WEAPONS = {"fighter": "longsword", "rogue": "rapier", "wizard": "quarterstaff"}
DEFAULT_ARMOR = {"fighter": "chain_mail", "rogue": "studded_leather", "wizard": "robes"}


@dataclass(frozen=True)
class EquipmentItem:
    """A serializable equipment instance with a mundane or magical bonus."""

    base_id: str
    bonus: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.base_id, str) or self.base_id not in EQUIPMENT:
            raise ValueError("Unknown equipment type.")
        if type(self.bonus) is not int or not 0 <= self.bonus <= MAX_ENCHANTMENT:
            raise ValueError(f"Equipment bonus must be an integer from 0 to {MAX_ENCHANTMENT}.")

    @property
    def id(self) -> str:
        return f"{self.base_id}_{self.bonus}" if self.bonus else self.base_id

    @property
    def name(self) -> str:
        return f"{self.spec.name} +{self.bonus}" if self.bonus else self.spec.name

    @property
    def spec(self) -> EquipmentSpec:
        return EQUIPMENT[self.base_id]

    @property
    def kind(self) -> str:
        return self.spec.kind

    @property
    def rarity(self) -> str:
        rarities = RARITIES if self.kind == "weapon" else ARMOR_RARITIES
        return rarities[self.bonus]

    @property
    def sale_value(self) -> int:
        return max(1, equipment_price(self) // 2)

    @property
    def description(self) -> str:
        if not self.bonus:
            return self.spec.description
        effect = (f"+{self.bonus} to attack and damage rolls"
                  if self.kind == "weapon" else f"+{self.bonus} to AC")
        if self.kind == "weapon" and self.spec.focus:
            effect += ", also applied to wizard spell attacks and spell save DC"
        return f"{self.spec.description} Magical enchantment: {effect}."


def _canonical_class(class_id: str) -> str:
    if not isinstance(class_id, str):
        raise ValueError("Choose warrior, rogue, or wizard.")
    normalized = class_id.strip().lower()
    normalized = {"warrior": "fighter", "rouge": "rogue"}.get(normalized, normalized)
    if normalized not in _CLASS_IDS:
        raise ValueError("Choose warrior, rogue, or wizard.")
    return normalized


def equipment_options(class_id: str, kind: str | None = None) -> tuple[EquipmentSpec, ...]:
    """Return the class's proficient equipment, optionally filtered by kind."""
    canonical_class = _canonical_class(class_id)
    if kind not in (None, "weapon", "armor"):
        raise ValueError("Equipment kind must be weapon, armor, or None.")
    return tuple(spec for spec in EQUIPMENT.values()
                 if canonical_class in spec.classes and (kind is None or spec.kind == kind))


def make_equipment(base_id: str, bonus: int = 0) -> EquipmentItem:
    """Construct and validate an equipment item without mutating a character."""
    return EquipmentItem(base_id, bonus)


def equipment_price(item: EquipmentItem) -> int:
    """Return Mira's campaign price; recovered equipment sells for half."""
    if not isinstance(item, EquipmentItem):
        raise ValueError("An EquipmentItem is required to determine its price.")
    surcharges = _WEAPON_SURCHARGES if item.kind == "weapon" else _ARMOR_SURCHARGES
    return item.spec.base_price + surcharges[item.bonus]


def resolve_equipment_id(text: str) -> str | None:
    """Recognize a catalog ID or full display name without guessing unknown items."""
    if not isinstance(text, str):
        return None
    candidate = text.strip().casefold()
    if not candidate:
        return None
    normalized = re.sub(r"\s+", "_", candidate)
    for base_id, spec in EQUIPMENT.items():
        for bonus in range(MAX_ENCHANTMENT + 1):
            item = EquipmentItem(base_id, bonus)
            if candidate == item.id or candidate == item.name.casefold():
                return item.id
            if normalized == item.id:
                return item.id
            # Short armor names remain useful alongside their full display names.
            if bonus and candidate == f"{base_id.replace('_', ' ')} +{bonus}":
                return item.id
    return None
