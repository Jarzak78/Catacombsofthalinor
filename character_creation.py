"""Rolled ability scores and an injectable terminal character creator."""

from dataclasses import dataclass
import random
from typing import Callable

from player import Player


ABILITY_NAMES: tuple[str, ...] = (
    "strength", "dexterity", "intelligence", "constitution", "wisdom", "charisma",
)

CLASS_NAMES: dict[str, str] = {
    "fighter": "Warrior",
    "rogue": "Rogue",
    "wizard": "Wizard",
}

_CLASS_ALIASES = {
    "1": "fighter", "warrior": "fighter", "fighter": "fighter",
    "2": "rogue", "rogue": "rogue", "rouge": "rogue",
    "3": "wizard", "wizard": "wizard",
}

CLASS_SUMMARIES: dict[str, str] = {
    "fighter": "Armored sword fighter; Second Wind restores health, with Action Surge and Extra Attack as you level.",
    "rogue": "A nimble rapier fighter; Sneak Attack, Vex, and skilled hiding, with Cunning Action as you level.",
    "wizard": "Fire Bolt cantrip and protective magic; spell slots fuel stronger spells and recover with rest.",
}


@dataclass(frozen=True)
class AbilityRoll:
    """The four dice, one discarded die, and the resulting ability score."""

    stat: str
    dice: tuple[int, int, int, int]
    dropped: int
    total: int


def canonical_class(value: str) -> str:
    """Normalize the class names and numbered choices offered at startup."""
    try:
        return _CLASS_ALIASES[value.strip().lower()]
    except KeyError:
        raise ValueError("Choose Warrior, Rogue, or Wizard.") from None


def roll_ability_scores(rng: random.Random) -> tuple[AbilityRoll, ...]:
    """Roll four six-sided dice per ability, discarding one lowest die."""
    rolls = []
    for stat in ABILITY_NAMES:
        dice = tuple(rng.randint(1, 6) for _ in range(4))
        dropped = min(dice)
        rolls.append(AbilityRoll(stat, dice, dropped, sum(dice) - dropped))
    return tuple(rolls)


def select_character(
    rng: random.Random,
    name: str = "Adventurer",
    class_id: str | None = None,
    *,
    input_fn: Callable[[str], str] | None = None,
    output_fn: Callable[[str], None] | None = None,
) -> Player | None:
    """Choose a class, roll abilities, and allow one whole-set reroll.

    Input and output are injected so other interfaces can use the same
    selection flow. Quitting returns None; EOF and interruption propagate
    to the launcher, which already handles a player closing the session.
    """
    read = input if input_fn is None else input_fn
    write = print if output_fn is None else output_fn
    if class_id is None:
        write("\nChoose your adventurer:")
        for index, candidate in enumerate(CLASS_NAMES, start=1):
            write(f"  {index}. {CLASS_NAMES[candidate]} — {CLASS_SUMMARIES[candidate]}")
        while True:
            choice = read("\nClass (1/2/3 or name; quit to leave): ").strip().lower()
            if choice in {"quit", "q", "exit"}:
                return None
            try:
                class_id = canonical_class(choice)
                break
            except ValueError:
                write("Choose 1 (Warrior), 2 (Rogue), or 3 (Wizard).")
    else:
        class_id = canonical_class(class_id)

    write(f"\n{name}, the {CLASS_NAMES[class_id]}: {CLASS_SUMMARIES[class_id]}")
    write("Roll 4d6 for each ability and drop one lowest die. You may reroll once, replacing all six scores.")
    reroll_available = True
    while True:
        rolls = roll_ability_scores(rng)
        write("\nYour starting ability scores:")
        for roll in rolls:
            dice = ", ".join(str(die) for die in roll.dice)
            write(f"  {roll.stat.title():12} [{dice}]  drop {roll.dropped}  = {roll.total}")
        while True:
            prompt = ("\nAccept these scores, reroll once, or quit? [accept/reroll/quit]: "
                      if reroll_available else "\nAccept these scores or quit? [accept/quit]: ")
            choice = read(prompt).strip().lower()
            if choice in {"", "accept", "a", "yes", "y", "keep"}:
                return Player.create(
                    name=name,
                    class_id=class_id,
                    stats={roll.stat: roll.total for roll in rolls},
                )
            if choice in {"reroll", "re-roll", "roll", "r"}:
                if reroll_available:
                    reroll_available = False
                    break
                write("You have already used your one reroll. Accept these scores or quit; your scores are unchanged.")
                continue
            if choice in {"quit", "q", "exit"}:
                return None
            options = "'accept', 'reroll', or 'quit'" if reroll_available else "'accept' or 'quit'"
            write(f"Enter {options}. Your current scores are unchanged.")
