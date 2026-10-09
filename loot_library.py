"""Treasure carried by the forgotten chambers of Thalinor."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Loot:
    """A treasure bundle that can be claimed once from its room."""

    gold: int = 0
    potions: int = 0
    weapon_name: str | None = None
    weapon_bonus: int = 0

    def __post_init__(self) -> None:
        if self.gold < 0 or self.potions < 0 or self.weapon_bonus < 0:
            raise ValueError("Loot amounts cannot be negative.")


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
