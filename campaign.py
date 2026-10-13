"""Campaign content, independent of presentation and input devices."""
from dataclasses import dataclass
from equipment import (
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
    spec = item.spec
    if item.kind == "weapon":
        count, sides = spec.damage_dice
        grip = "two-handed" if spec.two_handed else "one-handed"
        details = f"{count}d{sides} damage; {grip}."
    else:
        if spec.dex_cap == 0:
            dexterity = ""
        elif spec.dex_cap is None:
            dexterity = " + full Dexterity modifier"
        else:
            dexterity = f" + Dexterity modifier (maximum +{spec.dex_cap})"
        enchantment = f" + {item.bonus} enchantment" if item.bonus else ""
        details = f"Base AC {spec.base_ac}{dexterity}{enchantment}."
    return f"{item.rarity.capitalize()}. {details} {item.description}"

def stock(floor: int, class_id: str = "fighter") -> tuple[ShopItem, ...]:
    """Reliable supplies and proficient gear; magical tiers unlock with depth.

    Stock is deterministic and replenished: random dungeon finds supplement
    these purchases, rather than supplying a mandatory equipment upgrade.
    """
    tier = _shop_tier(floor)
    canonical = _shop_class(class_id)
    items = (
        ShopItem("potion", "Healing potion", 12, "potion", 1, "Heals 2d4+2 HP; bonus action."),
        ShopItem("charm", "Vitality charm", 35, "charm", 4, "One per adventurer: +4 maximum and current HP."),
        ShopItem("ward", "Warding ring", 65, "ward", 1, "One per adventurer: +1 Armor Class."),
        ShopItem("ember", "Ember stone", 18, "ember", 1, "Consumed as an action: 3d6 damage, no attack roll."),
    )
    if canonical == "wizard":
        items += (ShopItem("mana", "Mana draught", 18, "mana", 1,
                           "Restores one spent first-level spell slot; bonus action."),)
    for kind in ("weapon", "armor"):
        for bonus in range(tier + 1):
            for spec in equipment_options(canonical, kind):
                item = make_equipment(spec.id, bonus)
                items += (ShopItem(item.id, item.name, equipment_price(item),
                                   item.kind, item.bonus,
                                   _equipment_description(item), item),)
    return items
