# Catacombs of Thalinor

Your guild badge is new. You have never faced a monster. Today you
enter your first dungeon: the forgotten catacombs beneath Thalinor.
Explore five increasingly dangerous floors, defeat their guardians, and
use portals to shop for upgrades before facing the Hollow King.

A turn-based dungeon crawler with desktop and terminal interfaces,
**Warrior, Rogue, and Wizard** adventurers, rolled starting abilities,
and combat adapted from selected fifth-edition SRD rules. Classes use the
simplified abilities described below; the campaign's story, monster roster,
treasure probabilities, and dungeon rulings were developed for this project. This
game's death rule is immediate: reaching zero HP ends the adventurer's run.

See [CREDITS.txt](CREDITS.txt) for the required SRD attribution and adaptation
notice, and [legal/README.md](legal/README.md) for content provenance and
third-party license information. Those notices cover the identified
third-party material; the owner has not selected a general license for the
separate project-specific code, story, or artwork. This is an independent
game and claims no official status.

## Play

### Windows: double-click the executable

1. Open [Build Windows EXE on GitHub](https://github.com/Jarzak78/Catacombsofthalinor/actions/workflows/windows-exe.yml).
2. Open the latest successful run for `codex/dungeon-campaign` (green check).
3. Under **Artifacts**, download **CatacombsOfThalinor-Windows-x64**.
   GitHub requires you to sign in to download workflow artifacts.
4. Extract the ZIP and double-click **CatacombsOfThalinor.exe**.

The main executable opens a desktop window. Its title screen depicts the
catacomb entrance with softly flickering torches and has a **Character Creation** button. Choose a class,
roll your abilities, and accept your character before clicking **Enter the
Dungeon**. The adventure screen keeps a scrolling text terminal on the
left, with a minimap in the upper-right corner and your character's status
across the top. Type commands and press Enter or click **Send**, or use the
direction and common-action buttons. Your class button offers **Second
Wind**, **Hide**, or a **Spells** menu. Mira's sanctuary has category buttons
for weapons, armor, supplies, inventory, selling, and continuing the adventure.
Use the command box for resting, portals, item examination, and other commands
listed below; the Up and Down keys
recall earlier commands. At zero HP, your adventurer dies immediately and
gameplay stops. When the adventure ends, its text remains visible and
**New Adventure** lets you start another character.

Python and Tk are bundled, so you do not need to install Python or VS Code.
Keep the included **CREDITS.txt** and **legal** folder with either executable
when copying or sharing the game. Credits are also available from the game's
**Credits** option or either launcher's `--credits` command-line option.
The packaged Windows launchers ask you to accept the included
[Microsoft runtime terms](legal/END_USER_TERMS.txt) before play. Those
terms concern only the bundled Microsoft components and do not relicense
the game's separate content, Python, or the SRD material. The terminal
option `--accept-runtime-terms` supplies explicit acceptance for automated
play; credits can be viewed without accepting.
The same ZIP also includes **CatacombsOfThalinor-Terminal.exe** for the
original console interface. That version waits for Enter before closing
after quitting, winning, or dying; the finished adventure cannot continue
while waiting. Artifact downloads remain available for 30 days; a new
successful build refreshes the download.

You can also launch it from a Windows terminal with options:

```powershell
.\CatacombsOfThalinor.exe --name Tarin --seed 7
```

For the console interface, run `CatacombsOfThalinor-Terminal.exe` instead.

### Run the Python source

The source requires **Python 3.10 or newer**. All runtime dependencies are
in the standard library; no account, network connection, or server is needed.

```sh
cd /workspace/Catacombsofthalinor
python3 GuiMain.py --name Tarin
```

The desktop interface requires Tk support in your Python installation.
Windows Python includes it; some Linux distributions provide it separately
as `python3-tk`. To play in a terminal instead, run
`python3 Main.py --name Tarin`.

During character creation, choose **Warrior** (the existing Fighter), **Rogue**, or
**Wizard**. Each ability—Strength, Dexterity, Intelligence, Constitution,
Wisdom, and Charisma—is rolled separately using **4d6, dropping one lowest
die**. The game shows all four dice, the discarded die, and the resulting
score. Accept the first set or use your **one reroll** to replace all six
scores. After rerolling, accept the replacement set or quit; you cannot
reroll again. In the desktop interface, **Create Character** accepts the
displayed scores and shows the resulting character before **Enter the
Dungeon** starts the adventure.
Changing class or using **Back to Title** preserves your rolls and whether
you have used the reroll. Accepting the character locks those choices.
Scores are assigned to their displayed abilities; there are no added
species/background bonuses or score rearrangement.

The terminal interface accepts `--class rogue` or `--class wizard` to skip
the class-selection question, then still offers ability rolls and one
optional reroll. The terminal's `--quick-start` skips character creation and
uses a preset character; it can be combined with `--class`.
For example, `python3 Main.py --quick-start --class wizard --seed 7` begins
a repeatable Wizard adventure immediately. The default quick-start class
is Warrior.

Use `--seed 7` to repeat character rolls, a dungeon, and its random events.
The same seed, class, accepted rolls/rerolls, and commands give the same
results. The default campaign has five floors. Use `--floors 1` for a short first-floor
trial, or `--floors 3` for a three-floor campaign. Adventures are held in memory;
quitting ends the current run.

Start with `look`, `map`, `skills`, and `help`. The entrance is safe. Search
cleared rooms with `loot`; gems, jewelry, useful magical supplies, and
mundane or enchanted equipment can join your gold and healing potions.
Each room's contents are rolled when its floor is generated. No room
guarantees a magic weapon, magic armor, or even searchable treasure;
Mira's shop supplies reliable equipment and consumables between floors.

Entering a room with a living foe shows only combat information: the enemy,
any scouting or initiative result, your turn, and combat commands. Room descriptions,
exits, treasure, and documents wait until the fight is over. During combat,
`look` keeps the same focused view. After victory, type `look` to examine the
room and discover what you can collect.

In a safe room, `look` describes the hiding place and gives vague clues such
as a metallic glimmer, stoppered glass, or the outline of a blade. Specific treasure
names, quantities, and equipment bonuses are revealed when you use `loot`. Looking
collects and equips nothing. Collected treasure disappears from later previews,
while uncollected documents remain visible.

Successful `loot` searches describe where you uncover the find: abandoned
packs, burial chests, offerings, and other hiding places suited to each room
and floor. Treasure and documents share one discovery description when found
together. The following lines list exactly what you collect. Discovery prose
lives in `loot_flavor.py` and consumes no random rolls.
Found equipment receives an exact name and bonus, and an explanation of
whether it replaces your current gear. Clear improvements equip
automatically; choices involving damage, shields, masteries, armor, or
stealth stay in your pack for you to decide. Your previous equipment is
retained. Use `inventory` to see compact, paged lists with stable item IDs,
`examine <id or name>` for an item's full description and properties, and
`equip <id or name>` to change gear in a safe room or at the vendor.

## Commands

| Command | Effect |
| --- | --- |
| `north`, `south`, `east`, `west` | Move through a passage; `n/s/e/w` also work. |
| `look`, `map`, `stats`, `skills` | Inspect surroundings, character, or class abilities. |
| `inventory`, `inventory <page>` | List carried items without descriptions, eight entries per page. |
| `loot` | Collect treasure and lore documents once the room is safe. |
| `equip <item id or name>` | Equip an owned weapon or armor in a safe room or at Mira's shop. |
| `journal` | List your collected notes with journal numbers. |
| `read`, `read 1`, `read <note id>` | Read the latest note, a numbered note, or a collected note by its id. |
| `examine`, `inspect`, `examine foe` | Study your current foe's description, HP, AC, attacks, and tactical clues. |
| `examine <item id or name>` | Read an owned item's description, properties, slot, rarity, and value; at Mira's shop, also examine stock. This is free. |
| `attack` / `a` | Use an action for a weapon attack; Wizards use Fire Bolt instead. |
| `strike` | Make one physical weapon strike, including a Wizard's staff; Warriors use `attack` for Extra Attack. |
| `hide` | Rogue: attempt a DC 20 Stealth check; a hidden finesse-weapon hit can deliver Sneak Attack. Your first attempt is free after spotting a new room's foe unnoticed. |
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
| `menu`, `shop`, `1`–`6` | At Mira's sanctuary, open the six-choice menu or select an option. |
| `shop weapons`, `shop armor`, `shop supplies` | Browse weapons or supplies, or choose an armor slot. |
| `shop <category or armor slot> [page]` | List up to eight sale items with IDs, names, and prices; slots are `boots`, `gloves`, `pants`, `torso`, and `helmet`. |
| `buy <item id or name>` | Purchase equipment or supplies at Mira's sanctuary. |
| `sell <item id or name>`, `sell all` | At Mira's shop, sell valuables and unequipped equipment; equipped gear is protected. |
| `descend` | Leave the vendor for the next floor; after the final floor, return home. |
| `ember` | Consume an Ember stone and an action to deal 3d6 magic damage. |
| `help`, `quit` | Show instructions or end the adventure. |

Actions do **not** automatically end your turn. For example, you can
`attack`, drink a `potion` as your bonus action, then `end`. A level-2 Warrior
can `attack`, `surge`, `attack`, and `end`. You get only one bonus action
per turn, so Second Wind and a potion cannot both be used on that turn.
Other informational and invalid commands spend no actions. Item examination
spends no action, bonus action, time, or dice rolls, including during combat.
Examining a foe follows the opening-encounter rules below.

## Shared combat rules

- On your first entry into a room containing a living foe, you make a
  **Perception check** against DC 12 before it can attack. Warriors and
  Wizards use `d20 + Wisdom modifier`; Rogues add twice their proficiency
  bonus through Perception expertise. Success lets you spot the monster
  unnoticed and take the first turn, regardless of initiative. You can
  examine it freely, attack normally, or, as a Rogue, try one free opening
  Hide check before attacking. Failed scouting uses normal initiative;
  if the monster goes first, that failed check gives its opening attack
  Advantage without a second Perception roll. Safe rooms and rooms with
  defeated foes require no check.
- When normal initiative is needed, the adventurer rolls
  `d20 + Dexterity modifier`; a monster rolls `d20 + its initiative bonus`.
  The adventurer wins ties as this game's chosen DM ruling.
- Spotting a new foe unnoticed or winning initiative gives you a free
  `examine` before your first action
  or the end of your opening turn. A bonus action or Action Surge does
  not use up this chance. Otherwise, your first examination costs one
  action. Once studied, you can examine that foe again for free during
  the encounter. Examining rolls no dice and advances no time; you must
  be alive and fighting a foe.
- Reentering a room with a living foe does not repeat its first-entry
  scouting check or offer another unnoticed opening. Normal initiative
  applies; if the monster goes first, make this game's **Perception save**
  against DC 12, using the same bonus as the scouting check. Success lets
  its opening strike proceed normally; failure gives that strike
  Advantage. Ambush Advantage applies only to the opening strike, and
  you do not lose a turn. Natural 1 and 20 have no special effect on
  Perception checks or saves. These are game house rules.
- Weapon attacks roll `d20 + attack ability modifier + proficiency + magic
  weapon bonus` against Armor Class. Weapons normally use Strength;
  finesse weapons use whichever is better of Strength and Dexterity.
  Wizard spell attacks use Intelligence, proficiency, and an enchanted
  Arcane Staff's focus bonus. Enchanted daggers and ordinary quarterstaffs
  improve physical attacks without improving spells.
  Natural 1 always misses; natural 20 always hits.
  As a game house rule, a natural 1 also causes 1 HP of self-damage to
  the attacker and a comic mishap description.
- Advantage and Disadvantage roll two d20s and use the higher or lower;
  having both cancels them.
- Critical hits double damage dice, including eligible Sneak Attack dice,
  and add flat modifiers once. A critical hit can still roll low damage.
  Combat text displays the dice formula before the damage total, for example
  `1d6 × 2 + 2 (12)` for a critical hit dealing 12 damage. The multiplication
  sign means rolling twice as many dice, not doubling one die's result.
  Sneak Attack appears as its own dice pool in the same formula. Uncanny
  Dodge and successful Fireball saves show the original roll and its halved
  damage explicitly.
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
- At zero HP, your adventurer dies immediately and the adventure ends.
  There are no death saving throws, stabilization, or recovery turns.
  Healing, potions, class abilities, and rests cannot revive a dead
  character. This is the game's chosen death rule.

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
Sap also works with a mace, but does not apply to a weapon without that
mastery. Two-handed weapons use their own damage dice and lose both the
shield's +2 AC and Dueling's +2 damage while equipped.

**Second Wind** uses a bonus action to restore `1d10 + level` HP. It starts
with two uses, gains a third at level 4, restores one use on a short rest,
and restores all uses on a long rest. **Action Surge** unlocks at level 2,
adding one action this turn once per short or long rest. At level 5,
**Extra Attack** grants two weapon strikes per Attack action.

### Rogue

The Rogue starts with a rapier, studded leather (AC `12 + Dexterity modifier`),
and a d8 Hit Die. Finesse strikes use the better of Strength and Dexterity
for both attack and damage.
**Stealth and Perception expertise** add twice proficiency to their checks.
The rapier's **Vex** grants Advantage on your next strike against that foe
after a successful hit.
Vex also works with a shortsword; daggers and scimitars do not grant it.
Armor marked as hindering stealth gives Disadvantage on Hide checks.

Use **hide** to roll a Stealth check against **DC 20** on every floor, including
the free opening attempt. Success
gives Advantage on your next attack and Disadvantage to enemy attacks until
you reveal yourself by attacking. If your first-entry Perception check
spots a foe unnoticed, you may attempt Hide **once for free** before your
first action or ending your opening turn. This preserves both your action
and bonus action. Success lets you attack from hiding; a failed opening
Hide alerts the monster and immediately rolls normal initiative. If the
monster wins, it makes one opening attack with Advantage, without another
Perception check. If you win or tie, you act first; failing Hide does not
refund an action or bonus action you already spent before detection. A hidden attack spends
your normal attack action and reveals you even if it misses. Spotting a
foe alone does not grant attack Advantage or Sneak Attack.

Outside that opening opportunity, hiding costs an action at level 1;
**Cunning Action** makes it a bonus action from level 2, and also lets you
flee using a bonus action instead of an action. A failed ordinary combat Hide
spends its normal resource and leaves you visible; it does not reroll initiative.
Hidden status ends when you attack, even on a miss.
**Sneak Attack** adds `ceil(level / 2)d6` once per turn only when the Rogue
was hidden immediately before a successful finesse-weapon strike. Vex or
another source of Advantage alone does not qualify. These extra dice double
on a critical hit.
At level 5, **Uncanny Dodge** automatically halves damage from one enemy hit
per turn while you are alive. The game applies it without a separate
reaction command.

### Wizard

The Wizard starts with a quarterstaff, robes, known spells, AC `10 + Dexterity modifier`,
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

Spell save DC is `8 + Intelligence modifier + proficiency + Arcane Staff focus bonus`.
Only an enchanted Arcane Staff adds a focus bonus. Protective wizard vestments
are homebrew unarmored clothing: Robes have base AC 10, Warded Robes 11, and
Battlemage Robes 12. Mage Armor raises that base to at least 13, then adds
Dexterity and the combined armor enchantment bonus described below.
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
movement. Leaving combat uses Disengage; creatures guard their rooms and
do not pursue. Both monsters and the adventurer die at zero HP.
Exploration proceeds room by room rather than on a tactical grid.
Cleared rooms allow uninterrupted short
rests; the entrance allows long rests. Time is simulated, and monsters
do not respawn. These are explicit dungeon rules and scope choices.

The original rules reference was the official System Reference Document
5.2; shared material was also reviewed against SRD 5.2.1. Both are available
from the [official SRD page](https://www.dndbeyond.com/srd) under CC BY 4.0.
This game adapts selected material and does not implement either complete
ruleset. [CREDITS.txt](CREDITS.txt) contains the exact attribution statements
and an explanation of the changes. The README describes the implemented
mechanics in wording written for this project.

## Develop and test

Use the existing checkout; each cloud task already has its own isolated
workspace. Start the desktop game with `python3 GuiMain.py`, or the terminal
game with `python3 Main.py`; no background services need restarting.

```sh
python3 -m unittest discover -v
```

The suite checks character creation, class abilities, attack and damage rolls,
action budgets, healing, resources, immediate death, generation, treasure,
complete seeded adventures, desktop-session flow and minimap visibility,
and a full adventure through the actual command-line entry point.

`GuiMain.py` launches the desktop interface; `desktop_ui.py` builds its
Tk screens, and `ui_controller.py` manages character creation and commands.
`Main.py` owns terminal input;
`game.py` handles commands and turns; `combat.py` resolves dice;
`player.py` tracks character resources;
`equipment.py` defines weapon and five-slot armor profiles, enchantments,
stat-buff affixes, and campaign prices;
`presentation.py` supplies shared desktop tags and interactive terminal colors;
`character_creation.py` rolls and accepts starting abilities;
`dungeon.py` generates the map; `monster_catalog.py` defines each floor's
ordinary foes, combat statistics, descriptions, and attack narration.
The room and loot libraries define the remaining content.
Pass an explicit seed to reproduce gameplay failures.

## Build the Windows executable

For free signing on your own Windows account, see
[personal test signing](PERSONAL_TEST_SIGNING.md). The tool creates a local,
short-lived certificate and signs a separate EXE copy. It does not clear Chrome
download detections or change antivirus, browser, or PowerShell policies.

GitHub builds **64-bit Windows desktop and console executables** whenever Python source
or build configuration is pushed to `main`, `codex/first-playable-dungeon`, or `codex/dungeon-campaign`.
Once this workflow is on the repository's default branch, GitHub also
allows **Run workflow** on the Actions page, selecting the game branch.
Each build runs the test suite, checks the packaged desktop's screens,
character creation, commands, and minimap, and plays a complete adventure
through the terminal executable from outside the checkout before uploading them.
Warrior, Rogue, and Wizard replays each encounter all thirty ordinary monster
types and all five guardians, checking that the packaged game includes every
floor's roster.

To build on your own Windows computer, install **64-bit Python 3.12**, open
a terminal in the source folder, and run:

```powershell
python -m pip install -r requirements-build.txt
python scripts/build_windows.py
python scripts/smoke_gui.py dist/CatacombsOfThalinor.exe
python scripts/smoke_executable.py dist/CatacombsOfThalinor-Terminal.exe
```

The outputs are `dist/CatacombsOfThalinor.exe` for the desktop interface
and `dist/CatacombsOfThalinor-Terminal.exe` for the console interface. Each
bundles Python and the game in one file. The desktop build also bundles Tk
and opens without a console. Game data and the title artwork are embedded,
so both executables work from any folder. PyInstaller
must build on Windows to produce a Windows EXE; a Linux build cannot be
renamed to make a Windows application.


## Five floors and the portal vendor

The campaign descends through the Forgotten Catacombs, Rootbound Depths,
Ashen Forge, Starless Vault, and Thalinor's Heart. Each floor has a fresh
12-room connected map. Enemy HP, Armor Class, attack bonuses, damage, gold,
and XP increase with depth; the guardians culminate in the Hollow King.

Each floor has six distinct ordinary monsters suited to its chapter of
the dungeon's story. Every generated floor places one of each species;
their rooms and encounter order change with the seed. Ordinary species do
not repeat on deeper floors. Each floor also has its own guardian, giving
the campaign thirty ordinary monster types and five guardians.

| Floor | Ordinary monsters |
| --- | --- |
| Forgotten Catacombs | Crypt Rat, Bone Sentry, Grave Marauder, Hollow Acolyte, Restless Knight, Catacomb Stalker |
| Rootbound Depths | Sapglass Beetle, Thorn Creeper, Spore Husk, Amber Mantis, Rootcoil Viper, Moldbound Keeper |
| Ashen Forge | Bellows Automaton, Slag Crawler, Cinder Imp, Hollow Smith, Chainwork Harrier, Crucible Scuttler |
| Starless Vault | Oathbound Echo, Silverchain Watcher, Shadow Jailer, Mirror Shardling, Nameless Witness, Starless Leech |
| Thalinor's Heart | Blackwater Courtier, Crown Wisp, Heartless Usher, Choir Fragment, Sacrifice Revenant, Throne Hunger |

Monster types vary in health, armor, damage dice, and initiative bonus.
`examine` describes their origins, defenses, and tactical weaknesses;
hits, near misses, and critical failures use creature-specific narration.
Each foe makes one attack on its turn using the shared combat rules above.
Monster attacks deal their listed damage without additional elemental or
status effects; descriptions of spores, fire, and shadows supply atmosphere.

Defeating a guardian clears its floor rather than ending the game. Stand in
its chamber and type `portal` to teleport to Mira's sanctuary. A safe night's
rest restores HP, Hit Dice, class resources, and Wizard spell slots once per
visit, and ends Mage Armor. Potions, Ember stones, and Mana draughts are
not replenished for free.

Mira introduces herself after the first guardian and offers different dialogue
after each floor, commenting on your progress through its story. Arrival
shows her dialogue and a compact six-choice sanctuary menu:

1. Weapons.
2. Armor, then boots, gloves, pants, torso, or helmet.
3. Supplies.
4. Inventory.
5. Sell spare items (`sell all`).
6. Descend, or leave the dungeon after the last floor.

Use `menu` or `shop` to return to these choices. Shop categories show up to
eight rows per page, each with just a stable purchase ID, exact item name,
and price. For example, `shop weapons 2` opens the next weapons page and
`shop boots` lists footwear. Use `examine <item id or name>` to read its
full physical description, damage or armor profile, class proficiency,
enchantment, and other properties before buying.
Every vendor stocks all weapon and armor
types your class can use, in mundane versions and each unlocked enchantment
tier: +1 after floor one, +2 after floor two, and +3 after floor three.
There are no +4 or +5 equipment bonuses. Equipment stock is reliable and
supplies can be purchased repeatedly when you have enough gold. Special
stat-buff affixes are optional dungeon finds; Mira's reliable equipment
stock does not guarantee them.

Use an ID such as `buy longsword_1` or a full name such as `buy Longsword +1`.
`buy sword`/`buy weapon` and `buy armor` remain shortcuts for your class's
preferred gear at the highest unlocked tier; the Wizard's weapon shortcut
selects an Arcane Staff. Purchases enter your pack, with clear improvements
equipping automatically. Use `equip` to choose gear with tradeoffs. The
Vitality charm grants +4 maximum and current HP; the Warding ring grants
+1 AC. Both are permanent and can only be bought once. Healing potions
use a bonus action, and Ember stones use an action for automatic 3d6 damage.
Wizards can also use `buy mana` for a Mana draught (18 gold).
Insufficient gold and duplicate permanent items never cost gold. You may
purchase a different equipment type even when it is not an automatic upgrade.

When done shopping, type `descend`. Your character, XP, gold, supplies, and
equipment carry forward. Old floors close behind you. After the last floor,
the vendor's departure portal returns you home and completes the campaign.
Victory is not declared until you choose to leave the final vendor.

## Equipment, treasure, and rarity

Weapons and armor use adapted fifth-edition SRD profiles, with mundane and +1/+2/+3
versions. The loot tables are self-authored for this game, rather than
reproductions of the SRD treasure tables. Campaign gold prices, wizard vestments,
and the Arcane Staff's spell bonuses are homebrew adaptations for solo play.

| Class | Weapon options | Torso armor or clothing options |
| --- | --- | --- |
| Warrior | Longsword, Battleaxe, Warhammer, Greatsword, Greataxe, Mace, Spear, Rapier, Shortsword, Dagger, Scimitar, Quarterstaff | Padded Armor, Leather Armor, Studded Leather, Scale Mail, Breastplate, Half Plate, Chain Mail, Splint Armor, Plate Armor |
| Rogue | Rapier, Shortsword, Dagger, Scimitar | Padded Armor, Leather Armor, Studded Leather |
| Wizard | Dagger, Quarterstaff, Arcane Staff | Robes, Warded Robes, Battlemage Robes |

Finesse weapons choose the better of Strength and Dexterity. Greatswords
deal 2d6 damage and greataxes 1d12; both require two hands. Other weapons
use their displayed damage dice. Light armor adds full Dexterity, medium
armor caps its Dexterity bonus at +2, and heavy armor ignores Dexterity.
Some armor imposes Disadvantage on stealth; use `examine` to compare these
properties with damage, protection, and class abilities.

Armor occupies **five separate slots: boots, gloves, pants, torso, and helmet**.
Warriors can use leather or mail accessories, Rogues leather accessories,
and Wizards cloth accessories. Each character starts with a complete mundane
outfit. The torso determines base AC, Dexterity limits, stealth penalties,
and whether Mage Armor applies. Mundane accessories do not each add another
base AC; they complete the outfit while offering their own magical upgrades.
The catalog contains 37 base weapon and armor types, each with fuller
physical descriptions and an examined explanation of its actual effects.

Each magical armor piece can contribute its +1, +2, or +3 enchantment to AC.
The **sum of enchantments across all five pieces is capped at +3**: for
example, +2 boots and +2 gloves contribute +3 AC together. This cap covers
armor enchantments; a shield, Warding ring, and spell protection use their
own existing rules.

Found magical armor has a further chance of one special buff: **20% for +1,
30% for +2, or 40% for +3 armor**. These percentages apply after a magical
armor item has been rolled; mundane armor and weapons never receive armor
buff affixes. Possible names include **Might**, **Agility**, **Intellect**,
**Insight**, **Presence**, **Shadow**, and **Vigilance**, with choices suited
to the adventurer's class. The effect matches the piece's enchantment tier:
+2 armor of Shadow adds +2 to Stealth checks, while +2 armor of Agility adds
+2 to the Dexterity **score**, rather than directly adding +2 to its modifier.

Buffs apply only while the actual item is equipped. Only the strongest bonus
to the same score or skill applies, and boosted ability scores stop at 20.
Rolled base scores remain unchanged. Strength, Dexterity, Intelligence,
Wisdom, Charisma, Stealth, and Perception can benefit; these affixes do not
change Constitution, maximum HP, or healing. Affixed equipment is priced
at its ordinary enchanted price plus **15 gold per enchantment tier**;
its resale value is half that total, rounded down.

Every floor has four ordinary rooms without monsters, six ordinary monster
rooms, a guardian chamber, and a safe entrance. The four ordinary safe
rooms are possible caches, not guaranteed treasure rooms. Each searchable
room rolls the following categories independently, so it may hold several
categories or none. Equipment finds are class-compatible; weapons and armor
are equally likely before selecting a type and enchantment.

| Searchable room | Gold | Healing potion | Gem or jewelry | Magical supply | Equipment |
| --- | --- | --- | --- | --- | --- |
| Ordinary safe room | 75% | 35% | 40% | 15% | 30% |
| Ordinary monster room | 30% | 15% | 20% | 10% | 15% |
| Guardian chamber | 70% | 35% | 50% | 25% | 30% |

Defeated monsters also award their listed gold automatically; that combat
reward is separate from treasure found by searching their rooms. Searchable
contents are rolled once when a floor is generated. `look`, `loot`, and
revisiting never reroll the contents or award the same treasure twice.

When equipment is found, its bonus is rolled using this depth-based table.
These percentages are conditional on the room's equipment roll succeeding.

| Floor | Mundane | +1 | +2 | +3 |
| --- | --- | --- | --- | --- |
| 1 | 70% | 27% | 2.9% | 0.1% |
| 2 | 55% | 35% | 9.5% | 0.5% |
| 3 | 40% | 40% | 18% | 2% |
| 4 | 25% | 42% | 28% | 5% |
| 5 | 15% | 40% | 35% | 10% |

Weapon rarities are uncommon (+1), rare (+2), and very rare (+3). Armor
rarities are rare (+1), very rare (+2), and legendary (+3). The percentage
table selects enchantment bonuses for either kind; the item then displays
its corresponding rarity.

For example, a first-floor safe room has a 30% chance of equipment, then
a 0.1% chance that equipment is +3: a **0.03% overall chance of any +3 item**
in that room. A particular weapon is rarer still. Magical equipment is never
guaranteed, while stronger finds become more common with depth.

The dungeon contains gems, jewelry, and magical trinkets alongside coins and
healing potions. Safe caches and defeated foes can hold treasure. Some magical
finds are usable supplies: **Ember stones** deal `3d6` damage with `ember`,
and **Mana draughts** restore a Wizard's spent level-1 slot with `mana`.
Other classes can carry Mana draughts to sell to Mira instead.
Mundane gear can be worth keeping too: a different weapon or armor profile
may suit your tactics. Clear upgrades equip automatically, tradeoffs wait
for your choice, and replaced gear remains in your pack.

`look` gives vague hints about the container and its contents. Use `loot`
after a room is safe to reveal exact item names, quantities, bonuses, and
sell values. `inventory` lists carried equipment and valuables with stable
IDs, rarity, quantity, equipped status, and resale values, eight entries per
page. It does not print descriptions beside every item. Use `inventory 2`
for another page and `examine <item id or name>` for an item's full card.
The same command examines Mira's sale stock while you are in the sanctuary.
Use `equip <item id or name>` in a safe room or at Mira's sanctuary.
At the shop, `sell <item id or name>` sells matching valuables or unequipped
gear; `sell all` sells both categories while protecting equipped items.
Equipment sells for half Mira's purchase price, rounded down, with a minimum
of one gold. Gems and jewelry use their displayed sale values. Healing
potions and usable class supplies remain separate from unequipped gear.

## Interfaces, graphics, and controls

The desktop interface launches through `GuiMain.py`; `Main.py` remains the
terminal adapter. Both interfaces use the same game engine. The engine
never opens a window, reads keys, or prints, so richer graphics or controller
input can use its existing actions and snapshots:

```python
from actions import Action
from game import Game

game = Game(seed=7)
state = game.get_state()       # Detached, JSON-compatible rendering data
messages = game.perform(Action("east"))
# At the vendor: game.perform(Action("buy", "sword"))
state = game.get_state()       # Redraw from the updated state
```

Snapshots expose floor/scene, class, base and effective abilities,
the five equipped armor slots and active buffs, player equipment/resources,
spell slots, carried valuables, turn budgets,
encounter scouting and initiative results, whether a foe is unaware,
opening Hide and examination availability,
visited room descriptions/exits/enemies/loot, portal status, and vendor
stock with stable item ids. Unvisited room contents are hidden. Reading a
snapshot does not advance randomness or time; changing it cannot mutate
the game. Coordinates identify rooms within the current floor. Text
commands and buttons use the same `perform` path as future controller input.
Floor themes and vendor stock live in `campaign.py`, equipment profiles in
`equipment.py`, and random treasure tables in `loot_library.py`.
Foe panels can use `Action("examine")` through the same engine.
Class controls use `Action("hide")`, `Action("cast", "firebolt")`, or
`Action("sell", "all")`. Item panels can use `Action("examine", "rapier_1")`.
Both character creators use pure rolled-score
data from `character_creation.py` to display rolls
and pass an accepted `Player` to `Game(player=player, seed=7)`. Constructing
`Game` directly without a player or rolled stats uses class presets.

The desktop interface supplies an illustrated entrance, character-creation
screens, text gameplay, action buttons, and a minimap. Visited rooms show
known foes, treasure, or notes; unexplored rooms use question marks, and
only explored passages are drawn. Hidden room descriptions, enemies, and
treasure remain hidden. In Mira's shop the map shows the
sanctuary instead of dungeon rooms. Sprite-based gameplay, animations, and
controller bindings can be added later without replacing combat rules.
Description colors make the log easier to scan: room descriptions are green,
item descriptions light blue, Mira's dialogue lavender, combat messages red,
and entered commands gold. The console interface also uses colors when
running interactively in a supported terminal. Redirected output stays plain,
and setting the `NO_COLOR` environment variable disables console colors.
The test suite includes real five-floor combat, shopping, and a full
campaign through the terminal launcher. The terminal executable smoke
check plays all five floors from outside the checkout.

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
not trigger the mishap.

Self-damage can kill an adventurer or defeat a monster. At 1 HP, an
adventurer's critical fail ends the run immediately, preventing a second
Extra Attack or any later action. A monster that defeats itself still
grants XP/gold once, and a guardian still opens its floor's portal.
Flavor text and fixed mishap damage consume no extra dice rolls, keeping
seeded play reproducible.

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

Launch the terminal version to see an ASCII catacomb entrance with the game's title
and descending stairs, followed by class selection and ability rolls.
`--quick-start` goes directly from the title to the adventure. Narrow
terminals use a compact version. The art uses plain ASCII so it displays
without special fonts or terminal colors. Redirected-input playthroughs
can use `--quick-start` to skip creation prompts.
The artwork lives in `title_screen.py`, separate from the game rules.
