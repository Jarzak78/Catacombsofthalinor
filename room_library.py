"""Room flavor and independent homebrew foes for a novice D&D-style trial.

These creatures use custom statistics balanced for this small solo dungeon;
they are not official D&D monster stat blocks.
"""

import random

from monster_catalog import MonsterSpec, floor_roster
from room import Enemy


ENTRANCE = (
    "The Broken Stair",
    "Moonlight spills down a cracked stairway. Your first dungeon awaits: "
    "reach Thalinor's inner chamber and defeat its warden to prove yourself.",
)

SANCTUM = (
    "The Warden's Sanctum",
    "Blue fire burns around an ancient throne. A towering armored warden "
    "raises its blade. Defeat this last guardian, and your first dungeon "
    "will be complete.",
)

ROOM_FLAVORS = (
    (
        "Hall of Whispering Kings",
        "Broken statues watch from the shadows. Your footsteps stir whispers "
        "from mouths carved in stone.",
    ),
    (
        "The Rootbound Vault",
        "Pale roots push through the ceiling, winding around empty stone "
        "coffins like the fingers of a giant hand.",
    ),
    (
        "Chapel of the Last Light",
        "A silver altar catches the glow of your lantern. The candles around "
        "it have been cold for centuries.",
    ),
    (
        "The Sunken Gallery",
        "Dark water fills the grooves between flagstones. Torn banners "
        "cling to the walls above a forgotten battlefield mural.",
    ),
    (
        "The Ashen Armory",
        "Rusting weapon racks line the walls. Beneath the dust, a few "
        "old runes still flicker with stubborn light.",
    ),
    (
        "The Scribe's Tomb",
        "Fragments of parchment cover a stone desk. A faded inscription "
        "lists the names of adventurers who once completed this trial.",
    ),
    (
        "The Echoing Well",
        "A dry well opens in the center of the chamber. Every sound "
        "returns from its depths a heartbeat too late.",
    ),
    (
        "The Hall of Chains",
        "Heavy chains hang from the ceiling. They sway despite the still "
        "air, clicking softly against one another.",
    ),
    (
        "The Pilgrim's Refuge",
        "A stone bench and a shattered waterskin mark an old resting place. "
        "Someone scratched a tiny sun into the wall.",
    ),
    (
        "The Starless Observatory",
        "A collapsed dome reveals only solid rock. Tarnished bronze rings "
        "once tracked stars that Thalinor no longer sees.",
    ),
)

# Homebrew statistics: (name, HP, AC, attack bonus, damage dice, damage bonus, XP, gold).
ENEMY_TEMPLATES = tuple(
    (spec.name, spec.hp, spec.armor_class, spec.attack_bonus, spec.damage_dice,
     spec.damage_bonus, spec.xp_reward, spec.gold_reward)
    for spec in floor_roster(1)
)


def _instantiate_enemy(spec: MonsterSpec) -> Enemy:
    """Give a catalog entry independent, unscaled combat state."""
    return Enemy(
        name=spec.name,
        max_hp=spec.hp,
        hp=spec.hp,
        armor_class=spec.armor_class,
        attack_bonus=spec.attack_bonus,
        damage_dice=spec.damage_dice,
        damage_bonus=spec.damage_bonus,
        xp_reward=spec.xp_reward,
        gold_reward=spec.gold_reward,
        initiative_bonus=spec.initiative_bonus,
    )


def make_enemy(rng: random.Random, floor: int = 1) -> Enemy:
    """Choose a foe native to this floor and create fresh combat state."""
    return _instantiate_enemy(rng.choice(floor_roster(floor)))


def make_floor_enemies(rng: random.Random, floor: int) -> list[Enemy]:
    """Place each native species once, in a seedable shuffled order."""
    roster = list(floor_roster(floor))
    rng.shuffle(roster)
    return [_instantiate_enemy(spec) for spec in roster]


def make_warden() -> Enemy:
    return Enemy(
        name="Warden of Thalinor",
        max_hp=22,
        hp=22,
        armor_class=15,
        attack_bonus=4,
        damage_dice=(1, 6),
        damage_bonus=2,
        xp_reward=200,
        gold_reward=35,
        boss=True,
    )
