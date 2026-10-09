# Catacombs of Thalinor

Your guild badge is new. Your sword has never faced a monster. Today you
enter your first dungeon: the forgotten catacombs beneath Thalinor.
Explore its chambers, gather supplies, and defeat the Warden to return
as a proven adventurer.

A turn-based terminal dungeon crawler with a prebuilt fighter and combat
based on **the revised 2024 D&D 5e rules**. The story and monster statistics
are original; encounters are balanced for one adventurer.

## Play

Requires **Python 3.10 or newer**. All dependencies are in the standard
library; no package installation, account, network connection, or server
is needed.

```sh
cd /workspace/Catacombsofthalinor
python3 Main.py --name Tarin
```

Use `--seed 7` to repeat a dungeon and its random events. Identical commands
with the same seed give identical results. Adventures are held in memory;
quitting ends the current run.

Start with `look`, `map`, and `help`. The entrance is safe, and a nearby
treasure room always holds a magic longsword. Search with `loot` to claim it.

## Commands

| Command | Effect |
| --- | --- |
| `north`, `south`, `east`, `west` | Move through a passage; `n/s/e/w` also work. |
| `look`, `map`, `stats`, `inventory` | Inspect your surroundings or character. |
| `loot` | Collect treasure once the room is safe. |
| `attack` / `a` | Use an action for a longsword attack. |
| `dodge` / `d` | Use an action to impose Disadvantage on enemy attacks until your next turn. |
| `disengage` / `flee` / `f` | Use an action and movement to retreat without an opportunity attack. |
| `potion` / `p` | Use a bonus action to drink a healing potion for `2d4+2` HP. |
| `second wind` / `wind` | Use a bonus action to heal `1d10 + fighter level` HP. |
| `action surge` / `surge` | At fighter level 2, gain one additional action this turn. |
| `end` | End your turn and allow the enemy to act. |
| `rest` | Spend one hour resting; spend available Hit Dice until healed. |
| `rest 0`, `rest 1`, `rest 2` | Limit the Hit Dice spent in that one-hour rest. |
| `long rest` | Rest for eight hours at the entrance. |
| `help`, `quit` | Show instructions or end the adventure. |

Actions do **not** automatically end your turn. For example, you can
`attack`, drink a `potion` as your bonus action, then `end`. At level 2 you
can `attack`, `surge`, `attack`, and `end`. You get only one bonus action
per turn, so Second Wind and a potion cannot both be used on that turn.
Informational and invalid commands spend no actions.

## Implemented 2024 combat rules

- Initiative is `d20 + Dexterity modifier`, rolled when an encounter begins.
  The adventurer wins ties as this game's chosen DM ruling.
- Attacks roll `d20 + Strength modifier + proficiency + magic weapon bonus`
  against Armor Class. Natural 1 always misses; natural 20 always hits.
- Advantage and Disadvantage roll two d20s and use the higher or lower;
  having both cancels them.
- A one-handed longsword deals `1d8 + Strength + 2` with the Dueling style,
  plus its magic bonus. Critical hits double dice and add modifiers once.
- Longsword **Sap** applies Disadvantage to the target's next attack before
  the fighter's next turn. It does not stack or persist indefinitely.
- Second Wind starts with two uses. A short rest restores one use; a long
  rest restores all. Action Surge unlocks at level 2 and recharges on
  either kind of rest.
- A fighter's Hit Die is a d10. Short-rest healing adds Constitution to
  each die; multiple dice can be spent within the same rest. A long rest
  restores all Hit Dice and HP, and must begin with positive HP. At least
  sixteen hours must pass after one long rest before starting the next.
- XP is cumulative: level 2 at 300 XP, level 3 at 900. Fixed fighter HP
  increases use `6 + Constitution modifier`; leveling preserves missing
  HP and does not fully heal or recharge abilities.
- At zero HP, you are unconscious. Death saves happen at the start of
  your turn: 10+ succeeds, natural 1 causes two failures, natural 20
  restores 1 HP, three successes stabilize, and three failures kill.
  Unconscious targets give attackers Advantage; successful attacks from
  within five feet are critical hits and cause two failed saves. Massive
  damage can cause instant death. A natural-20 recovery lets you rise
  using half your movement and act on that turn.

The prebuilt fighter has Strength 16, Dexterity 14, Constitution 14,
Intelligence 10, Wisdom 12, and Charisma 10. He begins with 12 HP, AC 18
(chain mail and shield), a +5 attack bonus, three potions, and Dueling.
The early +1 longsword increases both attack and damage by one.

## Scope and dungeon rulings

This first adventure implements melee combat for a **level 1–2 fighter**.
It does not yet implement character creation, species/background traits,
origin feats, other classes, spells, ability checks, Tactical Mind,
grappling, ranged weapons, multiple simultaneous opponents, or later
fighter features. The available XP keeps this adventure below level 3.

Combatants fight within five feet; exits are close enough for normal
movement, including after standing. Leaving combat uses Disengage;
creatures guard their rooms and do not pursue. Monsters die at zero HP,
while the adventurer makes death saves. Exploration proceeds room by room
rather than on a tactical grid. Cleared rooms allow uninterrupted short
rests; the entrance allows long rests. Time is simulated, and monsters
do not respawn. These are explicit dungeon rules and scope choices.

The 2024 rules reference is the official [System Reference Document 5.2](https://www.dndbeyond.com/srd).
The README describes the implemented mechanics in original wording.

## Develop and test

Use the existing checkout; each cloud task already has its own isolated
workspace. Start the game with `python3 Main.py`; no background services
need restarting.

```sh
python3 -m unittest discover -v
```

The suite checks attack and damage rolls, action budgets, healing,
fighter resources, death saves, generation, treasure, complete seeded
adventures, and a full adventure through the actual command-line entry point.

`Main.py` owns terminal input; `game.py` handles commands and turns;
`combat.py` resolves dice; `player.py` tracks character resources;
`dungeon.py` generates the map; the room and loot libraries define content.
Pass an explicit seed to reproduce gameplay failures.
