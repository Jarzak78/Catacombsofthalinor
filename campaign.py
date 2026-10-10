"""Campaign content, independent of presentation and input devices."""
from dataclasses import dataclass

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

def stock(floor: int) -> tuple[ShopItem, ...]:
    tier = min(floor + 1, 5)
    return (
        ShopItem("potion", "Healing potion", 12, "potion", 1, "Heals 2d4+2 HP; bonus action."),
        ShopItem("sword", f"Longsword +{tier}", 45 * floor, "weapon", tier, "Upgrade attack and damage; equipped immediately."),
        ShopItem("armor", f"Runic armor +{floor}", 40 * floor, "armor", floor, "Upgrade Armor Class; equipped immediately."),
        ShopItem("charm", "Vitality charm", 35, "charm", 4, "One per adventurer: +4 maximum and current HP."),
        ShopItem("ward", "Warding ring", 65, "ward", 1, "One per adventurer: +1 Armor Class."),
        ShopItem("ember", "Ember stone", 18, "ember", 1, "Consumed as an action: 3d6 damage, no attack roll."),
    )
