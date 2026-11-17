"""Campaign content, independent of presentation and input devices."""
from dataclasses import dataclass
from equipment import (
    ARMOR_SLOTS,
    DEFAULT_ARMOR,
    DEFAULT_WEAPONS,
    EquipmentItem,
    MAX_ENCHANTMENT,
    equipment_options,
    equipment_price,
    make_equipment,
)

@dataclass(frozen=True)
class Floor:
    name: str
    guardian: str

FLOORS = (
    Floor("Forgotten Catacombs", "Warden of Thalinor"),
    Floor("Rootbound Depths", "Thornbound Sentinel"),
    Floor("Ashen Forge", "Ember Colossus"),
    Floor("Starless Vault", "Void Knight"),
    Floor("Thalinor's Heart", "The Hollow King"),
)

# Navigation labels belong to content; terminal and desktop clients decide
# which controls render them. The last-floor exit can be labelled "Leave" by
# the client rather than promising another floor after the Hollow King's fall.
SANCTUARY_MENU = (
    ("1", "Weapons"),
    ("2", "Armor"),
    ("3", "Supplies"),
    ("4", "Inventory"),
    ("5", "Sell spare items"),
    ("6", "Descend"),
)

_SANCTUARY_DIALOGUE = (
    "\"I'm Mira. I keep this sanctuary for adventurers who make it past "
    "Thalinor's guardians. The Warden of Thalinor has held that first seal for centuries; "
    "if it has fallen, the trouble runs deeper than the tombs. Catch your "
    "breath, inspect what you need, and spend carefully before you descend.\"",
    "\"You made it through the Rootbound Depths. That sap on your boots "
    "is still warm: the old grove draws its strength from the forge below. "
    "With the Thornbound Sentinel gone, you've opened another seal. "
    "Best prepare for iron and ash.\"",
    "\"The Ashen Forge didn't break you. Those chains were built to "
    "hold something, not haul ore. Now the Ember Colossus is silent, "
    "the Starless Vault lies ahead. Three guardians behind you; "
    "don't let that make you careless.\"",
    "\"You survived the Starless Vault, and the Void Knight's watch "
    "has ended. So the king gave his heart to save the city, and "
    "something hollow answered in his voice. You've reached the "
    "last descent. Take what you need to face the throne.\"",
    "\"You returned from Thalinor's Heart. The Hollow King's false "
    "heartbeat has stopped; even here, the stones feel still. "
    "Five guardians, five broken thresholds, and you made it home. "
    "Rest awhile. When you're ready, I'll open the way out.\"",
)


def sanctuary_dialogue(floor: int) -> str:
    """Mira reacts to the floor just cleared, without revealing future lore."""
    _shop_tier(floor)
    return _SANCTUARY_DIALOGUE[floor - 1]

@dataclass(frozen=True)
class ShopItem:
    id: str
    name: str
    price: int
    kind: str
    value: int
    description: str
    equipment: EquipmentItem | None = None


def _shop_class(class_id: str) -> str:
    """Use the equipment catalog's validation and supported class aliases."""
    equipment_options(class_id)
    canonical = class_id.strip().lower()
    return {"warrior": "fighter", "rouge": "rogue"}.get(canonical, canonical)


def _shop_tier(floor: int) -> int:
    if type(floor) is not int or not 1 <= floor <= len(FLOORS):
        raise ValueError("Invalid shop floor.")
    return min(floor, MAX_ENCHANTMENT)


def preferred_item_id(floor: int, class_id: str, kind: str) -> str:
    """Resolve old weapon/armor shortcuts to the shop's default upgrade."""
    tier = _shop_tier(floor)
    canonical = _shop_class(class_id)
    if kind not in ("weapon", "armor"):
        raise ValueError("Equipment kind must be weapon or armor.")
    if kind == "weapon":
        base_id = "arcane_staff" if canonical == "wizard" else DEFAULT_WEAPONS[canonical]
    else:
        base_id = DEFAULT_ARMOR[canonical]
    return make_equipment(base_id, tier).id


def _equipment_description(item: EquipmentItem) -> str:
    """Share the same examined card for shop stock and recovered equipment."""
    return item.description

def stock(floor: int, class_id: str = "fighter") -> tuple[ShopItem, ...]:
    """Reliable supplies and proficient gear; magical tiers unlock with depth.

    Stock is deterministic and replenished: random dungeon finds supplement
    these purchases, rather than supplying a mandatory equipment upgrade.
    """
    tier = _shop_tier(floor)
    canonical = _shop_class(class_id)
    items = (
        ShopItem("potion", "Healing potion", 12, "potion", 1,
                 "A stoppered vial of ruby-red medicine that warms your hands. "
                 "Drink it as a bonus action to regain 2d4+2 HP, up to your "
                 "maximum. The potion is consumed."),
        ShopItem("charm", "Vitality charm", 35, "charm", 4,
                 "A small heart-shaped charm tied with a copper-thread cord. "
                 "One per adventurer: permanently grants +4 maximum and current "
                 "HP when purchased. It does not occupy an armor slot."),
        ShopItem("ward", "Warding ring", 65, "ward", 1,
                 "A narrow silver band engraved with a circle of protective runes. "
                 "One per adventurer: permanently grants +1 Armor Class when "
                 "purchased. It does not occupy an armor slot or count toward "
                 "the combined armor-enchantment cap."),
        ShopItem("ember", "Ember stone", 18, "ember", 1,
                 "An orange crystal holds a restless spark behind its cloudy "
                 "surface. Crush it as an action to deal 3d6 damage to the "
                 "current foe, with no attack roll. The stone is consumed."),
    )
    if canonical == "wizard":
        items += (ShopItem("mana", "Mana draught", 18, "mana", 1,
                           "A blue-violet tonic shimmers when brought near a "
                           "spell focus. Drink it as a bonus action to restore "
                           "one spent first-level spell slot. The draught is "
                           "consumed; it cannot restore higher-level slots."),)
    for kind in ("weapon", "armor"):
        for bonus in range(tier + 1):
            for spec in equipment_options(canonical, kind):
                item = make_equipment(spec.id, bonus)
                items += (ShopItem(item.id, item.name, equipment_price(item),
                                   item.kind, item.bonus,
                                   _equipment_description(item), item),)
    return items


def shop_items(floor: int, class_id: str = "fighter",
               category: str = "all") -> tuple[ShopItem, ...]:
    """Return a deterministic category view without dropping stock or details.

    Descriptions remain on the returned records for free item examination;
    clients can present compact ID/name/price rows and page those rows.
    """
    if not isinstance(category, str):
        raise ValueError("Choose a shop category or armor slot.")
    normalized = category.strip().lower()
    normalized = {"weapon": "weapons", "armors": "armor",
                  "supply": "supplies"}.get(normalized, normalized)
    valid = ("all", "weapons", "armor", "supplies", *ARMOR_SLOTS)
    if normalized not in valid:
        raise ValueError("Choose all, weapons, armor, supplies, or an armor slot.")
    items = stock(floor, class_id)
    if normalized == "all":
        return items
    if normalized == "supplies":
        return tuple(item for item in items if item.equipment is None)
    if normalized == "weapons":
        return tuple(item for item in items if item.kind == "weapon")
    if normalized == "armor":
        return tuple(item for item in items if item.kind == "armor")
    return tuple(item for item in items
                 if item.equipment is not None
                 and item.equipment.spec.slot == normalized)
