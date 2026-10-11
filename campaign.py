"""Campaign content, independent of presentation and input devices."""
from dataclasses import dataclass
from loot_library import suitable_armor_name, suitable_weapon_name

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

def stock(floor: int, class_id: str = "fighter") -> tuple[ShopItem, ...]:
    if not 1 <= floor <= len(FLOORS):
        raise ValueError("Invalid shop floor.")
    if class_id not in ("fighter", "rogue", "wizard"):
        raise ValueError("Invalid adventurer class.")
    tier = min(floor + 1, 5)
    weapon_name = (f"Longsword +{tier}" if class_id == "fighter" else
                   suitable_weapon_name(class_id, tier))
    items = (
        ShopItem("potion", "Healing potion", 12, "potion", 1, "Heals 2d4+2 HP; bonus action."),
        ShopItem("sword", weapon_name, 45 * floor, "weapon", tier, "Upgrade attack and damage; equipped immediately."),
        ShopItem("armor", suitable_armor_name(class_id, floor), 40 * floor, "armor", floor, "Upgrade Armor Class; equipped immediately."),
        ShopItem("charm", "Vitality charm", 35, "charm", 4, "One per adventurer: +4 maximum and current HP."),
        ShopItem("ward", "Warding ring", 65, "ward", 1, "One per adventurer: +1 Armor Class."),
        ShopItem("ember", "Ember stone", 18, "ember", 1, "Consumed as an action: 3d6 damage, no attack roll."),
    )
    if class_id == "wizard":
        items += (ShopItem("mana", "Mana draught", 18, "mana", 1,
                           "Restores one spent first-level spell slot; bonus action."),)
    return items
