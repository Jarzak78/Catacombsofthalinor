"""Revised 2024 D&D fifth-edition attack and dice resolution.

These helpers handle attack rolls and damage without changing combatants.
The caller decides when a condition grants Advantage, Disadvantage, or an
automatic critical hit on a successful attack.
"""

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class AttackResult:
    """An attack's d20 rolls, chosen result, and final damage."""

    rolls: tuple[int, ...]
    roll: int
    total: int
    hit: bool
    critical: bool
    damage: int


def roll_dice(rng: random.Random, count: int, sides: int) -> int:
    """Sum ``count`` dice with ``sides`` faces, using the supplied RNG.

    A dice pool must contain at least one die, with at least two faces.
    Invalid pools raise ``ValueError`` before consuming random numbers.
    """
    if count < 1:
        raise ValueError("A dice pool must contain at least one die.")
    if sides < 2:
        raise ValueError("Dice must have at least two sides.")
    return sum(rng.randint(1, sides) for _ in range(count))


def roll_attack(
    rng: random.Random,
    attack_bonus: int,
    armor_class: int,
    damage_dice: tuple[int, int],
    damage_bonus: int,
    *,
    advantage: bool = False,
    disadvantage: bool = False,
    critical_on_hit: bool = False,
) -> AttackResult:
    """Resolve one attack against Armor Class and roll damage on a hit.

    Advantage and Disadvantage together cancel. A natural 1 always misses;
    a natural 20 always hits critically. Other attacks hit when their total
    meets or exceeds Armor Class. Critical hits roll twice the weapon dice,
    adding the flat damage bonus once. Damage cannot be negative.

    ``critical_on_hit`` models effects such as attacking an Unconscious
    target from within 5 feet. It only converts successful hits to critical
    hits; the caller must supply any associated Advantage separately.
    """
    rolls = (rng.randint(1, 20),)
    if advantage != disadvantage:
        rolls += (rng.randint(1, 20),)
        roll = max(rolls) if advantage else min(rolls)
    else:
        roll = rolls[0]

    total = roll + attack_bonus
    hit = roll != 1 and (roll == 20 or total >= armor_class)
    critical = hit and (roll == 20 or critical_on_hit)
    damage = 0
    if hit:
        count, sides = damage_dice
        damage = max(0, roll_dice(rng, count * (2 if critical else 1), sides) + damage_bonus)

    return AttackResult(rolls, roll, total, hit, critical, damage)


def roll_initiative(rng: random.Random, bonus: int) -> int:
    """Roll a Dexterity check for initiative; the caller resolves ties."""
    return rng.randint(1, 20) + bonus


def roll_healing_potion(rng: random.Random) -> int:
    """Roll the 2d4 + 2 Hit Points restored by a Potion of Healing."""
    return roll_dice(rng, 2, 4) + 2
