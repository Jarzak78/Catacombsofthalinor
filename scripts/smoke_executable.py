"""Exercise a built game from outside the checkout, including a full victory."""

from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.test_game import complete_adventure


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/smoke_executable.py path/to/game.exe", file=sys.stderr)
        return 2
    executable = Path(sys.argv[1]).resolve()
    if not executable.is_file():
        print(f"Executable not found: {executable}", file=sys.stderr)
        return 2

    game, commands, _ = complete_adventure(7, floors=5)
    if len(game.journal) != 20:
        raise RuntimeError("The reference adventure did not collect all twenty lore notes.")
    if not game.won:
        raise RuntimeError("The reference adventure did not reach victory.")
    scenarios = [
        ("full adventure", "\n".join(commands) + "\n", "Your first dungeon is conquered"),
        ("collect and read lore", "loot\njournal\nread 1\nquit\n", "Adventurer's clue:"),
        ("commands and quit", "help\nstats\nquit\n", "You leave the trial for another day"),
        ("closed input", "", "You leave the trial for another day"),
    ]
    with TemporaryDirectory(prefix="thalinor-smoke-") as working_directory:
        for name, command_text, expected in scenarios:
            result = subprocess.run(
                [str(executable), "--name", "Tarin", "--seed", "7", "--floors", "5"],
                cwd=working_directory, input=command_text, text=True,
                capture_output=True, timeout=90,
            )
            if result.returncode != 0 or result.stderr or expected not in result.stdout:
                print(result.stdout)
                print(result.stderr, file=sys.stderr)
                raise RuntimeError(f"Executable smoke test failed: {name} (exit {result.returncode})")
            if name == "full adventure" and "Floor 5/5" not in result.stdout:
                raise RuntimeError("Executable adventure did not reach the fifth floor.")
            print(f"PASS: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
