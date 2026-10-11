# Catacombs of Thalinor

Your guild badge is new. You have never faced a monster. Today you
enter your first dungeon: the forgotten catacombs beneath Thalinor.
Explore five increasingly dangerous floors, defeat their guardians, and
use portals to shop for upgrades before facing the Hollow King.

A turn-based terminal dungeon crawler with **Warrior, Rogue, and Wizard**
adventurers, rolled starting abilities, and combat inspired by the revised
2024 D&D 5e rules. Classes use the simplified abilities described below;
the story, monsters, treasure, and dungeon rulings are original.

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

At the beginning, choose **Warrior** (the existing Fighter), **Rogue**, or
**Wizard**. Each ability—Strength, Dexterity, Intelligence, Constitution,
Wisdom, and Charisma—is rolled separately using **4d6, dropping one lowest
die**. The game shows all four dice, the discarded die, and the resulting
score. Accept the first set or use your **one reroll** to replace all six
scores. After rerolling, accept the replacement set or quit; a further
reroll attempt leaves those scores unchanged and rolls no dice.
Scores are assigned to their displayed abilities; there are no added
species/background bonuses or score rearrangement.

`--class rogue` or `--class wizard` skips the class-selection question,
then still offers ability rolls and one optional reroll. `--quick-start` skips character
creation and uses a preset character; it can be combined with `--class`.
For example, `python3 Main.py --quick-start --class wizard --seed 7` begins
a repeatable Wizard adventure immediately. The default quick-start class
is Warrior.

Use `--seed 7` to repeat character rolls, a dungeon, and its random events.
The same seed, class, accepted rolls/rerolls, and commands give the same
results. The default campaign has five floors. Use `--floors 1` for a short first-floor
trial, or `--floors 3` for a three-floor campaign. Adventures are held in memory;
quitting ends the current run.

Start with `look`, `map`, `skills`, and `help`. The entrance is safe. Search
treasure rooms with `loot`; gems, jewelry, useful magical supplies, and
occasional equipment upgrades can join your gold and healing potions.
A nearby first-floor treasure room always holds a +1 weapon suited to
your class: longsword, rapier, or magical staff.

Entering a room with a living foe shows only combat information: the enemy,
initiative, any ambush result, your turn, and combat commands. Room descriptions,
exits, treasure, and documents wait until the fight is over. During combat,
`look` keeps the same focused view. After victory, type `look` to examine the
room and discover what you can collect.

In a safe room, `look` describes the hiding place and gives vague clues such
as a metallic glimmer, stoppered glass, or a gleaming longsword. Specific treasure
names, quantities, and equipment bonuses are revealed when you use `loot`. Looking
collects and equips nothing. Collected treasure disappears from later previews,
while uncollected documents remain visible.

Successful `loot` searches describe where you uncover the find: abandoned
packs, burial chests, offerings, and other hiding places suited to each room
and floor. Treasure and documents share one discovery description when found
together. The following lines list exactly what you collect. Discovery prose
lives in `loot_flavor.py` and consumes no random rolls.
Found equipment receives an exact name and bonus, and an explanation of
whether it replaces your current gear. Better compatible gear equips
automatically; a weaker find never downgrades what you use.

## Commands

| Command | Effect |
| --- | --- |
| `north`, `south`, `east`, `west` | Move through a passage; `n/s/e/w` also work. |
| `look`, `map`, `stats`, `inventory`, `skills` | Inspect surroundings, character, possessions, or class abilities. |
| `loot` | Collect treasure and lore documents once the room is safe. |
| `journal` | List your collected notes with journal numbers. |
| `read`, `read 1`, `read <note id>` | Read the latest note, a numbered note, or a collected note by its id. |
| `examine`, `inspect`, `examine foe` | Study your current foe's description, HP, AC, attacks, and tactical clues. |
| `attack` / `a` | Use an action for a weapon attack; Wizards use Fire Bolt instead. |
| `strike` | Make one physical weapon strike, including a Wizard's staff; Warriors use `attack` for Extra Attack. |
| `hide` | Rogue: try to hide, gaining Advantage for a successful hidden attack. |
| `cast <spell>` | Wizard: cast `firebolt`, `missile`, `armor`, `shield`, `frost`, or `fireball`. |
| `dodge` / `d` | Use an action to impose Disadvantage on enemy attacks until your next turn. |
| `disengage` / `flee` / `f` | Use an action and movement to retreat without an opportunity attack; level-2+ Rogues use a bonus action. |
| `potion` / `p` | Use a bonus action to drink a healing potion for `2d4+2` HP. |
| `second wind` / `wind` | Warrior: use a bonus action to heal `1d10 + level` HP. |
| `action surge` / `surge` | Warrior: from level 2, gain one additional action this turn. |
| `mana` | Wizard: drink a Mana draught as a bonus action to restore one spent level-1 spell slot. |
| `end` | End your turn and allow the enemy to act. |
| `rest` | Spend one hour resting; spend available Hit Dice until healed. |
| `rest 0`, `rest 1`, `rest 2` | Limit the Hit Dice spent in that one-hour rest. |
| `long rest` | Rest for eight hours at the entrance. |
| `portal` | After defeating a guardian, enter its portal to the vendor. |
| `shop`, `buy <item id>` | View vendor prices and purchase an upgrade or supply. |
| `sell <item id>`, `sell all` | At Mira's shop, sell collected valuables for their displayed gold value. |
| `descend` | Leave the vendor for the next floor; after the final floor, return home. |
| `ember` | Consume an Ember stone and an action to deal 3d6 magic damage. |
| `help`, `quit` | Show instructions or end the adventure. |

Actions do **not** automatically end your turn. For example, you can
`attack`, drink a `potion` as your bonus action, then `end`. A level-2 Warrior
can `attack`, `surge`, `attack`, and `end`. You get only one bonus action
per turn, so Second Wind and a potion cannot both be used on that turn.
Other informational and invalid commands spend no actions. Examining a
foe follows the opening-encounter rules below.

## Shared combat rules

- Initiative is `d20 + Dexterity modifier`, rolled when an encounter begins.
  The adventurer wins ties as this game's chosen DM ruling.
- Winning initiative gives you a free `examine` before your first action
  or the end of your opening turn. A bonus action or Action Surge does
  not use up this chance. Otherwise, your first examination costs one
  action. Once studied, you can examine that foe again for free during
  the encounter. Examining rolls no dice and advances no time; you must
  be conscious and fighting a foe.
- If the monster wins initiative, it ambushes you. You automatically
  make this game's **Perception save** against DC 12. Warriors and Wizards
  use `d20 + Wisdom modifier`; Rogues add twice their proficiency bonus
  through Perception expertise. Success lets its opening
  strike proceed normally; failure gives that strike Advantage. Later
  attacks get no ambush Advantage, and you do not lose a turn. Natural
  1 and 20 have no special effect on this save. This is a house rule.
- Weapon attacks roll `d20 + attack ability modifier + proficiency + magic
  weapon bonus` against Armor Class. Warriors and Wizard staff attacks use
  Strength; Rogue rapier attacks use Dexterity. Wizard spell attacks use
  Intelligence, proficiency, and their magical staff's focus bonus.
  Natural 1 always misses; natural 20 always hits.
  As a game house rule, a natural 1 also causes 1 HP of self-damage to
  the attacker and a comic mishap description.
- Advantage and Disadvantage roll two d20s and use the higher or lower;
  having both cancels them.
- Critical hits double damage dice, including eligible Sneak Attack dice,
  and add flat modifiers once. A critical hit can still roll low damage.
- Successful player and monster attacks get descriptions based on the damage
  rolled: **glancing** (1–5), **solid** (6–10), **heavy** (11–15), or
  **devastating** (16+). Swords, claws, roots, iron fists, and the Hollow
  King's darkness have distinct wording; critical hits add precision detail.
  These descriptions add no damage, conditions, or extra random rolls.
- Short-rest healing adds Constitution to each spent Hit Die; multiple
  dice can be spent within the same rest. A long rest
  restores all Hit Dice and HP, and must begin with positive HP. At least
  sixteen hours must pass after one long rest before starting the next.
- XP is cumulative: level 2 at 300 XP, level 3 at 900, level 4 at 2,700,
  and level 5 at 6,500. Fixed HP increases use `6 + Constitution modifier`
  for Warriors, `5 + Constitution modifier` for Rogues, and
  `4 + Constitution modifier` for Wizards. Leveling preserves missing HP
  rather than fully healing or recharging existing resources. Each level
  adds at least 1 HP, even with a very low Constitution score.
- At zero HP, you are unconscious. Death saves happen at the start of
  your turn: 10+ succeeds, natural 1 causes two failures, natural 20
  restores 1 HP, three successes stabilize, and three failures kill.
  Unconscious targets give attackers Advantage; successful attacks from
  within five feet are critical hits and cause two failed saves. Massive
  damage can cause instant death. A natural-20 recovery lets you rise
  using half your movement and act on that turn.

## Adventurer classes

All three classes support levels 1–5. Starting HP and attack bonuses depend
on your rolled abilities. `skills` lists your class's abilities, costs, and
later unlocks without spending a turn. `stats` shows remaining class resources.

### Warrior

The original Fighter is shown as **Warrior** during character creation.
It starts with chain mail and shield (AC 18), a longsword, the Dueling
style, and a d10 Hit Die. A sword strike deals `1d8 + Strength modifier + 2`,
plus its magic bonus. Longsword **Sap** gives the enemy Disadvantage on its
next attack before the Warrior's next turn; repeated Sap does not stack.

**Second Wind** uses a bonus action to restore `1d10 + level` HP. It starts
with two uses, gains a third at level 4, restores one use on a short rest,
and restores all uses on a long rest. **Action Surge** unlocks at level 2,
adding one action this turn once per short or long rest. At level 5,
**Extra Attack** grants two weapon strikes per Attack action.

### Rogue

The Rogue starts with a rapier, leather armor (AC `12 + Dexterity modifier`),
and a d8 Hit Die. Rapier strikes use Dexterity for both attack and damage.
**Stealth and Perception expertise** add twice proficiency to their checks.
The rapier's **Vex** grants Advantage on your next strike against that foe
after a successful hit.

Use **hide** to roll a Stealth check against `DC 12 + dungeon floor`. Success
gives Advantage on your next attack and Disadvantage to enemy attacks until
you reveal yourself by attacking. Hiding costs an action at level 1;
**Cunning Action** makes it a bonus action from level 2, and also lets you
flee using a bonus action instead of an action. Hidden status ends when you
attack. **Sneak Attack** adds `ceil(level / 2)d6` once per turn when an
eligible rapier strike has Advantage; these dice double on a critical hit.
At level 5, **Uncanny Dodge** automatically halves damage from one enemy hit
per turn while you are conscious. The game applies it without a separate
reaction command.

### Wizard

The Wizard starts with a staff, known spells, AC `10 + Dexterity modifier`,
and a d6 Hit Die. `attack` and `cast firebolt` use **Fire Bolt**, a slot-free
Intelligence spell attack dealing `1d10` damage (`2d10` at level 5). Use
`strike` for a physical staff attack based on Strength.

| Spell | Cost and effect |
| --- | --- |
| `cast missile` | Action and a level-1 slot: Magic Missile automatically deals `3d4+3` damage. |
| `cast armor` | Action in combat and a level-1 slot: Mage Armor changes base AC to `13 + Dexterity modifier` until a long rest. |
| `cast shield` | Bonus action and a level-1 slot: +5 AC against the next enemy strike. |
| `cast frost` | Action and a level-2 slot: an Intelligence spell attack deals `3d8`; a hit also gives the enemy Disadvantage on its next attack. |
| `cast fireball` | Action and a level-3 slot: deals `8d6`, halved by a successful enemy Dexterity save. |

Spell save DC is `8 + Intelligence modifier + proficiency + staff focus bonus`.
This is a single-enemy dungeon; Fireball targets the current foe. Shield's bonus-action
cost and Frost are simplified game abilities, rather than full tabletop
spell implementations.

| Wizard level | Level-1 slots | Level-2 slots | Level-3 slots |
| --- | --- | --- | --- |
| 1 | 2 | 0 | 0 |
| 2 | 3 | 0 | 0 |
| 3 | 4 | 2 | 0 |
| 4 | 4 | 3 | 0 |
| 5 | 4 | 3 | 2 |

Long rests and the portal's sanctuary rest restore all spell slots and end
Mage Armor. **Arcane Recovery** works automatically on one short rest per
long rest: it recovers spent slots with a combined slot-level budget of
`ceil(level / 2)`, restoring lower-level slots first, up to level 2. A
**Mana draught** restores one spent level-1 slot when drunk with `mana`;
it uses your bonus action in combat.

## Scope and dungeon rulings

This campaign implements selected level 1–5 Warrior, Rogue, and Wizard
abilities, rolled character creation, Stealth/Perception checks, and the
spells listed above. Ember stones and Mana draughts use the game's own rules.
It does not implement the full tabletop classes, species/background traits,
origin feats, Tactical Mind, grappling, tactical ranged combat, multiple
simultaneous opponents, subclasses, feats, or features beyond those listed.
Higher-level progression statistics exist in the model; higher-level class
features are outside the campaign's scope.

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

The suite checks character creation, class abilities, attack and damage rolls,
action budgets, healing, resources, death saves, generation, treasure, complete seeded
adventures, and a full adventure through the actual command-line entry point.

`Main.py` owns terminal input; `game.py` handles commands and turns;
`combat.py` resolves dice; `player.py` tracks character resources;
`character_creation.py` rolls and accepts starting abilities;
`dungeon.py` generates the map; the room and loot libraries define content.
Pass an explicit seed to reproduce gameplay failures.

## Build the Windows executable

For free signing on your own Windows account, see
[personal test signing](PERSONAL_TEST_SIGNING.md). The tool creates a local,
short-lived certificate and signs a separate EXE copy. It does not clear Chrome
download detections or change antivirus, browser, or PowerShell policies.

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
rest restores HP, Hit Dice, class resources, and Wizard spell slots once per
visit, and ends Mage Armor. Potions, Ember stones, and Mana draughts are
not replenished for free.

Use `shop` to see stable purchase ids and `buy sword`, `buy armor`, `buy charm`,
`buy ward`, `buy potion`, or `buy ember` to purchase. Equipment is applied
immediately. The sword and armor tier improves at deeper vendors. The
Vitality charm grants +4 maximum and current HP; the Warding ring grants
+1 AC. Both are permanent and can only be bought once. Healing potions
use a bonus action, and Ember stones use an action for automatic 3d6 damage.
Wizards can also use `buy mana` for a Mana draught (18 gold).
Insufficient gold, duplicate permanent items, and downgrades never cost gold.

When done shopping, type `descend`. Your character, XP, gold, supplies, and
equipment carry forward. Old floors close behind you. After the last floor,
the vendor's departure portal returns you home and completes the campaign.
Victory is not declared until you choose to leave the final vendor.

## Treasure and valuables

The dungeon contains gems, jewelry, and magical trinkets alongside coins and
healing potions. Safe caches and defeated foes can hold treasure. Some magical
finds are usable supplies: **Ember stones** deal `3d6` damage with `ember`,
and **Mana draughts** restore a Wizard's spent level-1 slot with `mana`.
Other classes can carry Mana draughts to sell to Mira instead.
Rare finds include class-compatible magical weapons and armor; better gear
equips automatically and weaker gear never replaces your current equipment.

`look` gives vague hints about the container and its contents. Use `loot`
after a room is safe to reveal exact item names, quantities, bonuses, and
sell values. `inventory` lists collected valuables and their stable item ids.
At Mira's sanctuary, use `sell <item id>` to sell all copies of that valuable
or `sell all` to exchange your collected valuables for gold, then buy upgrades. Supplies
and equipped gear are separate from the valuables you sell.

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

Snapshots expose floor/scene, class, abilities, player equipment/resources,
spell slots, carried valuables, turn budgets,
encounter initiative and examination availability,
visited room descriptions/exits/enemies/loot, portal status, and vendor
stock with stable item ids. Unvisited room contents are hidden. Reading a
snapshot does not advance randomness or time; changing it cannot mutate
the game. Coordinates identify rooms within the current floor. Text
commands use the same `perform` path as future button or controller input.
Floor themes and item definitions live separately in `campaign.py`.
Future foe panels can use `Action("examine")` through the same engine.
Class controls use `Action("hide")`, `Action("cast", "firebolt")`, or
`Action("sell", "all")`. The terminal character creator uses pure rolled-score
data from `character_creation.py`; another interface can display those rolls
and pass an accepted `Player` to `Game(player=player, seed=7)`. Constructing
`Game` directly without a player or rolled stats uses class presets.

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

## Collectible lore and the journal

Twenty authored documents tell the dungeon's history as you descend: four
on each floor, placed at its entrance, two exploration rooms, and the
guardian's chamber. Letters, watch orders, ledgers, and personal testimony
reveal the people behind the seals and the deeper threat. Each document
also includes a practical adventurer's clue.

`look` calls attention to documents in the current room. Once the room is
safe, `loot` collects both notes and any treasure in one search. You can
collect a note in a room with no treasure or whose treasure was already
claimed. Each note is collected once; guardians must be defeated before
searching their chambers. The map uses `N` for visited rooms with an
uncollected note, unless an enemy or treasure marker takes precedence.

Collection prints an exact reading command, such as `read 1`. Use
`journal` to browse numbered titles, floors, and stable note ids. `read 1`
opens the first note, `read <note id>` opens a collected note by id, and
plain `read` opens the most recently collected document. Reading does
not spend combat actions, advance game time, or roll dice. You can
reread collected notes during combat or in Mira's shop.

The journal carries forward between floors for this adventure. Search
the guardian's chamber and any remaining rooms before taking its portal:
old floors cannot be revisited. Notes are optional; they never block a
portal or victory. Like the rest of the adventure, the journal currently
lives in memory and is not saved when you close the game.

Authored text and clues live in `lore_notes.py`. The engine snapshot
exposes full text only for collected notes in `journal`; visited room
notes expose their title/id and collection flag, and unexplored rooms
reveal no documents. Future graphical journal panels can use the same
`Action("read", "1")` input as the terminal command.

## Terminal title screen

Launch the game to see an ASCII catacomb entrance with the game's title
and descending stairs, followed by class selection and ability rolls.
`--quick-start` goes directly from the title to the adventure. Narrow
terminals use a compact version. The art uses plain ASCII so it displays
without special fonts or terminal colors. Redirected-input playthroughs
can use `--quick-start` to skip creation prompts.
The artwork lives in `title_screen.py`, separate from the game rules.
