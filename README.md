# Catacombs of Thalinor

Your guild badge is new. Your sword has never faced a monster. Today you
enter your first dungeon: the forgotten catacombs beneath Thalinor.
Explore five increasingly dangerous floors, defeat their guardians, and
use portals to shop for upgrades before facing the Hollow King.

A turn-based terminal dungeon crawler with a prebuilt fighter and combat
based on **the revised 2024 D&D 5e rules**. The story and monster statistics
are original; encounters are balanced for one adventurer.

## Play

### Windows: double-click the executable

1. Open [Build Windows EXE on GitHub](https://github.com/Jarzak78/Catacombsofthalinor/actions/workflows/windows-exe.yml).
2. Open the latest successful run for `codex/dungeon-campaign` (green check).
3. Under **Artifacts**, download **CatacombsOfThalinor-Windows-x64**.
   GitHub requires you to sign in to download workflow artifacts.
4. Extract the ZIP and double-click **CatacombsOfThalinor.exe**.

The game opens in its own console window. Python is bundled, so you do not
need to install Python or VS Code: you only need the executable. After quitting, winning,
or dying, press Enter to close the window. Artifact downloads remain
available for 30 days; a new successful build refreshes the download.

You can also launch it from a Windows terminal with options:

```powershell
.\CatacombsOfThalinor.exe --name Tarin --seed 7
```

### Run the Python source

The source requires **Python 3.10 or newer**. All runtime dependencies are in the standard
library; no package installation, account, network connection, or server
is needed.

```sh
cd /workspace/Catacombsofthalinor
python3 Main.py --name Tarin
```

Use `--seed 7` to repeat a dungeon and its random events. Identical commands
with the same seed give identical results. The default campaign has five floors. Use `--floors 1` for a short first-floor
trial, or `--floors 3` for a three-floor campaign. Adventures are held in memory;
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
| `portal` | After defeating a guardian, enter its portal to the vendor. |
| `shop`, `buy <item id>` | View vendor prices and purchase an upgrade or supply. |
| `descend` | Leave the vendor for the next floor; after the final floor, return home. |
| `ember` | Consume an Ember stone and an action to deal 3d6 magic damage. |
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
  As a game house rule, a natural 1 also causes 1 HP of self-damage to
  the attacker and a comic mishap description.
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

This campaign implements a selected set of melee rules for a **level 1–5 fighter**,
including two strikes per Attack action at level 5. Ember stones are an original
magic item using the game's own rules.
It does not yet implement character creation, species/background traits,
origin feats, other classes, spells, ability checks, Tactical Mind,
grappling, ranged weapons, multiple simultaneous opponents, subclasses, feats, or later
fighter features other than Extra Attack. The complete campaign can reach fighter level 5. Higher-level progression
statistics exist in the model, but higher-level class features are outside scope.

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

## Build the Windows executable

GitHub builds a **64-bit Windows console executable** whenever Python source
or build configuration is pushed to `main`, `codex/first-playable-dungeon`, or `codex/dungeon-campaign`.
Once this workflow is on the repository's default branch, GitHub also
allows **Run workflow** on the Actions page, selecting the game branch.
Each build runs the test suite and then plays a complete adventure
through the actual executable from outside the checkout before uploading it.

To build on your own Windows computer, install **64-bit Python 3.12**, open
a terminal in the source folder, and run:

```powershell
python -m pip install -r requirements-build.txt
python scripts/build_windows.py
python scripts/smoke_executable.py dist/CatacombsOfThalinor.exe
```

The output is `dist/CatacombsOfThalinor.exe`. It bundles Python and the game
in one file and opens a console when launched from File Explorer. Game
data is embedded in the code, so it works from any folder. PyInstaller
must build on Windows to produce a Windows EXE; a Linux build cannot be
renamed to make a Windows application.


## Five floors and the portal vendor

The campaign descends through the Forgotten Catacombs, Rootbound Depths,
Ashen Forge, Starless Vault, and Thalinor's Heart. Each floor has a fresh
12-room connected map. Enemy HP, Armor Class, attack bonuses, damage, gold,
and XP increase with depth; the guardians culminate in the Hollow King.

Defeating a guardian clears its floor rather than ending the game. Stand in
its chamber and type `portal` to teleport to Mira's sanctuary. A safe night's
rest restores HP, Hit Dice, Second Wind, and Action Surge once per visit.
Potions and Ember stones are not replenished for free.

Use `shop` to see prices and `buy sword`, `buy armor`, `buy charm`,
`buy ward`, `buy potion`, or `buy ember` to purchase. Equipment is applied
immediately. The sword and armor tier improves at deeper vendors. The
Vitality charm grants +4 maximum and current HP; the Warding ring grants
+1 AC. Both are permanent and can only be bought once. Healing potions
use a bonus action, and Ember stones use an action for automatic 3d6 damage.
Insufficient gold, duplicate permanent items, and downgrades never cost gold.

When done shopping, type `descend`. Your character, XP, gold, supplies, and
equipment carry forward. Old floors close behind you. After the last floor,
the vendor's departure portal returns you home and completes the campaign.
Victory is not declared until you choose to leave the final vendor.

## Future graphics and controls

`Main.py` is the terminal adapter. It owns input and printing; the engine
never opens a window, reads keys, or prints. A graphical or controller
adapter can use the same engine directly:

```python
from actions import Action
from game import Game

game = Game(seed=7)
state = game.get_state()       # Detached, JSON-compatible rendering data
messages = game.perform(Action("east"))
# At the vendor: game.perform(Action("buy", "sword"))
state = game.get_state()       # Redraw from the updated state
```

Snapshots expose floor/scene, player equipment/resources, turn budgets,
visited room descriptions/exits/enemies/loot, portal status, and vendor
stock with stable item ids. Unvisited room contents are hidden. Reading a
snapshot does not advance randomness or time; changing it cannot mutate
the game. Coordinates identify rooms within the current floor. Text
commands use the same `perform` path as future button or controller input.
Floor themes and item definitions live separately in `campaign.py`.

This prepares the engine for graphics and controls; graphics assets, a
window renderer, animations, and controller bindings are future work.
The test suite includes real five-floor combat, shopping, and a full
campaign through the terminal launcher. The executable smoke check now
plays all five floors from outside the checkout.

Each floor has its own entrance, guardian chamber, and ten exploration
rooms. Arrival text and guardian discoveries tell a connected story:
the upper seals lead to a binding grove, its sustaining forge, a royal
prison, and finally the truth beneath Thalinor's throne. Room lore lives
in `floor_lore.py`; graphical interfaces can read the current chapter
from the snapshot's `story` field.

## Near misses and critical failures

A missed attack whose **total, including bonuses**, is one or two points
below the target's Armor Class receives a near-miss description. For
example, a total of 18 or 19 against AC 20 glances off armor without
dealing damage. Meeting AC 20 is still a hit. Both player and enemy
attacks receive narration suited to the combatant.

A **natural 1 on the d20 used for the attack** is a critical fail: the
attack misses, the attacker suffers a comic slip or stumble, and loses
**1 HP**. This is the game's house rule, added to the normal natural-1
miss. Advantage/disadvantage uses the selected die; a discarded 1 does
not trigger the mishap. Death-save natural 1s keep their existing rules
and do not cause this attack penalty.

Self-damage can knock an adventurer unconscious or defeat a monster. An
unconscious adventurer cannot make their second Extra Attack. A monster
that defeats itself still grants XP/gold once, and a guardian still
opens its floor's portal. If combat ends while you are unconscious,
`end` continues death saves; once stable in the safe room, another `end`
passes 1d4 recovery hours and restores 1 HP. Flavor text and fixed mishap
damage consume no extra dice rolls, keeping seeded play reproducible.
