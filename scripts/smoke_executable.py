"""Exercise a built game from outside the checkout, including a full victory."""

from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.test_game import complete_adventure
from tests.test_class_campaigns import complete_class_adventure
from campaign import FLOORS
from monster_catalog import floor_roster


def check_monster_rosters(text: str) -> None:
    """Every complete campaign must encounter each floor's native foes."""
    ordinary_foes = tuple(spec.name for floor in range(1, len(FLOORS) + 1)
                         for spec in floor_roster(floor))
    guardians = tuple(floor.guardian for floor in FLOORS)
    if len(ordinary_foes) != 30 or len(set(ordinary_foes)) != 30 or len(guardians) != 5:
        raise RuntimeError("The campaign must contain thirty unique floor monsters and five guardians.")
    missing = [name for name in (*ordinary_foes, *guardians) if name not in text]
    if missing:
        raise RuntimeError("The complete adventure omitted monsters: " + ", ".join(missing))


def check_character_rolls(text: str, expected_blocks: int) -> None:
    """Check the packaged creator's visible rolls and accepted final stats."""
    rolls = re.findall(
        r"^\s+(Strength|Dexterity|Intelligence|Constitution|Wisdom|Charisma)\s+"
        r"\[(\d+), (\d+), (\d+), (\d+)\]\s+drop (\d+)\s+= (\d+)\s*$",
        text, re.MULTILINE,
    )
    if len(rolls) != expected_blocks * 6:
        raise RuntimeError("Character creation did not show every ability roll and reroll.")
    order = ("Strength", "Dexterity", "Intelligence", "Constitution", "Wisdom", "Charisma")
    for block in range(expected_blocks):
        if tuple(roll[0] for roll in rolls[block * 6:(block + 1) * 6]) != order:
            raise RuntimeError("Character creation changed the announced ability order.")
    for ability, *numbers in rolls:
        dice = [int(number) for number in numbers[:4]]
        dropped, total = (int(number) for number in numbers[4:])
        if any(not 1 <= die <= 6 for die in dice) or dropped != min(dice) or total != sum(dice) - dropped:
            raise RuntimeError(f"Character creation displayed an invalid 4d6 roll: {ability}")
    for abbreviation, roll in zip(("STR", "DEX", "INT", "CON", "WIS", "CHA"), rolls[-6:]):
        if f"{abbreviation} {roll[-1]}" not in text:
            raise RuntimeError("The accepted character did not retain the last displayed ability scores.")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/smoke_executable.py path/to/game.exe", file=sys.stderr)
        return 2
    executable = Path(sys.argv[1]).resolve()
    if not executable.is_file():
        print(f"Executable not found: {executable}", file=sys.stderr)
        return 2

    game, commands, transcript = complete_adventure(7, floors=5)
    if len(game.journal) != 20:
        raise RuntimeError("The reference adventure did not collect all twenty lore notes.")
    if not game.won:
        raise RuntimeError("The reference adventure did not reach victory.")
    encounter_text = "\n".join(transcript)
    check_monster_rosters(encounter_text)
    if "Examining " not in encounter_text or "Perception check:" not in encounter_text:
        raise RuntimeError("The reference adventure did not exercise examination and room scouting.")
    scenarios = [
        ("full adventure", 7, ["--quick-start"], "\n".join(commands) + "\n",
         ("Your first dungeon is conquered",), 0),
        ("collect and read lore", 7, ["--quick-start"], "loot\njournal\nread 1\nquit\n",
         ("Adventurer's clue:",), 0),
        ("commands and quit", 7, ["--quick-start"], "help\nstats\nquit\n",
         ("You leave the trial for another day",), 0),
        ("credits before character creation", 7, ["--credits"], "",
         ("System Reference Document", "https://creativecommons.org/licenses/by/4.0/legalcode"), 0),
        ("credits during an adventure", 7, ["--quick-start"], "credits\nlicenses\nquit\n",
         ("System Reference Document", "https://creativecommons.org/licenses/by/4.0/legalcode",
          "You leave the trial for another day"), 0),
        ("closed input", 7, ["--quick-start"], "",
         ("You leave the trial for another day",), 0),
        ("Rogue character creation", 7, [], "rogue\naccept\nskills\nstats\nquit\n",
         ("the Rogue", "Rogue abilities", "Rogue 1", "Sneak Attack", "Vex", "Stealth"), 1),
        ("Wizard character creation", 7, [], "wizard\naccept\nskills\nstats\nquit\n",
         ("the Wizard", "Wizard abilities", "Wizard 1", "cast firebolt", "cast armor", "level 1: 2/2"), 1),
        ("one reroll and accept character", 7, [], "rouge\nreroll\nreroll\naccept\nskills\nstats\nquit\n",
         ("the Rogue", "Rogue abilities", "Rogue 1", "already used your one reroll"), 2),
        ("quit character creation", 7, [], "quit\n",
         ("Choose your adventurer", "You leave the trial for another day"), 0),
        ("closed input during creation", 7, [], "",
         ("Choose your adventurer", "You leave the trial for another day"), 0),
    ]
    for class_id, seed, attack_text in (("rogue", 0, "Sneak Attack:"), ("wizard", 1, "Fire Bolt")):
        class_game, class_commands, class_transcript = complete_class_adventure(class_id, seed, floors=5)
        if not class_game.won or class_game.floor != 5 or len(class_game.journal) != 20:
            raise RuntimeError(f"The reference {class_id} did not win all five floors and collect twenty notes.")
        if attack_text not in "\n".join(class_transcript):
            raise RuntimeError(f"The reference {class_id} did not exercise its class attacks.")
        check_monster_rosters("\n".join(class_transcript))
        class_evidence = ("Your first dungeon is conquered", "Floor 5/5",
                          f"You are a first-level {class_id.title()}", attack_text,
                          "Perception check:")
        if class_id == "rogue":
            if "Opening Hide:" not in "\n".join(class_transcript):
                raise RuntimeError("The reference Rogue did not exercise its free opening Hide.")
            class_evidence += ("Opening Hide:",
                               "Your opening Hide attempt spends no action or bonus action.")
        scenarios.append((
            f"{class_id.title()} full adventure", seed, ["--quick-start", "--class", class_id],
            "\n".join(class_commands) + "\n",
            class_evidence, 0,
        ))
    with TemporaryDirectory(prefix="thalinor-smoke-") as working_directory:
        for name, seed, options, command_text, expected, roll_blocks in scenarios:
            result = subprocess.run(
                [str(executable), "--accept-runtime-terms", "--name", "Tarin", "--seed", str(seed), "--floors", "5", *options],
                cwd=working_directory, input=command_text, text=True,
                capture_output=True, timeout=90,
            )
            if result.returncode != 0 or result.stderr or any(token not in result.stdout for token in expected):
                print(result.stdout)
                print(result.stderr, file=sys.stderr)
                raise RuntimeError(f"Executable smoke test failed: {name} (exit {result.returncode})")
            if roll_blocks:
                check_character_rolls(result.stdout, roll_blocks)
            if name == "full adventure" and "Floor 5/5" not in result.stdout:
                raise RuntimeError("Executable adventure did not reach the fifth floor.")
            if name == "full adventure" and ("Examining " not in result.stdout
                                             or "Perception check:" not in result.stdout):
                raise RuntimeError("Executable adventure did not exercise examination and room scouting.")
            if name == "full adventure" or name.endswith(" full adventure"):
                check_monster_rosters(result.stdout)
                print(f"PASS: {name} (30 floor monsters and 5 guardians)")
            else:
                print(f"PASS: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
