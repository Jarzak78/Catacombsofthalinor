"""State for individual dungeon rooms and their inhabitants."""

from dataclasses import dataclass

from loot_library import Loot


@dataclass
class Enemy:
    name: str
    max_hp: int
    hp: int
    armor_class: int
    attack_bonus: int
    damage_dice: tuple[int, int]
    damage_bonus: int
    xp_reward: int
    gold_reward: int
    boss: bool = False
    initiative_bonus: int = 0

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    def take_damage(self, amount: int) -> int:
        """Apply already-calculated damage and return the HP actually lost."""
        if amount < 0:
            raise ValueError("Damage cannot be negative.")
        damage = min(self.hp, amount)
        self.hp -= damage
        return damage


@dataclass
class Room:
    position: tuple[int, int]
    name: str
    description: str
    exits: dict[str, tuple[int, int]]
    enemy: Enemy | None = None
    loot: Loot | None = None
    visited: bool = False
    looted: bool = False
