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
    armor_class: int = 0
    extra_damage: int = 0
    damage_dice: tuple[int, int] | None = None
    damage_bonus: int = 0
    extra_damage_dice: tuple[int, int] | None = None
    damage_rolls: tuple[int, ...] = ()
    extra_damage_rolls: tuple[int, ...] = ()
    raw_damage: int | None = None

    @property
    def critical_fail(self) -> bool:
        """Only the selected natural 1 causes a mishap, not a discarded die."""
        return self.roll == 1

    @property
    def fumble_damage(self) -> int:
        """The game's natural-1 house rule causes one point of self-damage."""
        return 1 if self.critical_fail else 0

    @property
    def near_miss(self) -> bool:
        """A normal miss within two points of the target's Armor Class."""
        return not self.hit and not self.critical_fail and 1 <= self.armor_class - self.total <= 2


def roll_dice(rng: random.Random, count: int, sides: int) -> int:
    """Sum ``count`` dice with ``sides`` faces, using the supplied RNG.

    A dice pool must contain at least one die, with at least two faces.
    Invalid pools raise ``ValueError`` before consuming random numbers.
    """
    return sum(_roll_damage_dice(rng, count, sides))


def _roll_damage_dice(rng: random.Random, count: int, sides: int) -> tuple[int, ...]:
    """Keep each face while using the same dice order as ``roll_dice``."""
    if count < 1:
        raise ValueError("A dice pool must contain at least one die.")
    if sides < 2:
        raise ValueError("Dice must have at least two sides.")
    return tuple(rng.randint(1, sides) for _ in range(count))


def format_damage_pool(
    dice: tuple[int, int],
    bonus: int,
    total: int,
    *,
    critical: bool = False,
    extra_dice: tuple[int, int] | None = None,
    original_total: int | None = None,
) -> str:
    """Describe the rolled dice pool followed by the actual damage total.

    ``1d6 × 2`` denotes two independent d6 rolls on a critical hit, not
    doubling a single roll. A flat modifier appears once, after all dice.
    ``original_total`` allows a caller to show a saving throw or Uncanny
    Dodge reduction without presenting the reduced number as a full roll.
    The zero-damage floor remains visible through the resulting total.
    This helper never rolls dice or changes an attack result.
    """
    def pool_text(pool: tuple[int, int]) -> str:
        count, sides = pool
        if count < 1 or sides < 2:
            raise ValueError("Damage notation requires a valid dice pool.")
        return f"{count}d{sides}" + (" × 2" if critical else "")

    terms = [pool_text(dice)]
    if extra_dice is not None:
        terms.append(pool_text(extra_dice))
    formula = " + ".join(terms)
    if bonus > 0:
        formula += f" + {bonus}"
    elif bonus < 0:
        formula += f" - {abs(bonus)}"

    if original_total is not None and original_total != total:
        reduction = "halved" if total == original_total // 2 else "reduced"
        return f"{formula} ({original_total}; {reduction} to {total})"
    return f"{formula} ({total})"


def damage_notation(result: AttackResult) -> str:
    """Format a resolved hit, retaining the original roll when reduced.

    Misses never roll damage and display zero. Older caller-created
    results without pool metadata retain their plain numeric output.
    """
    if not result.hit or result.damage_dice is None:
        return str(result.damage)
    return format_damage_pool(
        result.damage_dice,
        result.damage_bonus,
        result.damage,
        critical=result.critical,
        extra_dice=result.extra_damage_dice,
        original_total=result.raw_damage,
    )


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
    extra_damage_dice: tuple[int, int] | None = None,
) -> AttackResult:
    """Resolve one attack against Armor Class and roll damage on a hit.

    Advantage and Disadvantage together cancel. A natural 1 always misses;
    a natural 20 always hits critically. Other attacks hit when their total
    meets or exceeds Armor Class. Critical hits roll twice the weapon dice,
    adding the flat damage bonus once. Optional extra damage dice (such as
    Sneak Attack) belong to the same hit and double on a critical hit;
    the zero-damage floor is applied after combining all dice and modifiers.

    ``critical_on_hit`` supports effects that make a successful attack
    critical. It never overrides a miss; the caller supplies any
    associated Advantage separately.
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
    extra_damage = 0
    damage_rolls: tuple[int, ...] = ()
    extra_damage_rolls: tuple[int, ...] = ()
    if hit:
        count, sides = damage_dice
        multiplier = 2 if critical else 1
        damage_rolls = _roll_damage_dice(rng, count * multiplier, sides)
        if extra_damage_dice is not None:
            extra_count, extra_sides = extra_damage_dice
            extra_damage_rolls = _roll_damage_dice(
                rng, extra_count * multiplier, extra_sides
            )
            extra_damage = sum(extra_damage_rolls)
        damage = max(0, sum(damage_rolls) + extra_damage + damage_bonus)

    return AttackResult(
        rolls, roll, total, hit, critical, damage, armor_class, extra_damage,
        damage_dice, damage_bonus, extra_damage_dice, damage_rolls,
        extra_damage_rolls, damage,
    )


def roll_initiative(rng: random.Random, bonus: int) -> int:
    """Roll a Dexterity check for initiative; the caller resolves ties."""
    return rng.randint(1, 20) + bonus


def roll_healing_potion(rng: random.Random) -> int:
    """Roll the 2d4 + 2 Hit Points restored by a Potion of Healing."""
    return roll_dice(rng, 2, 4) + 2
