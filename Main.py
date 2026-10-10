"""Launch Catacombs of Thalinor with ``python3 Main.py``."""

import argparse
import shutil
import sys
import traceback

from game import Game
from title_screen import title_screen


def main() -> None:
    parser = argparse.ArgumentParser(description="Conquer your first dungeon in Thalinor.")
    parser.add_argument("--name", default="Adventurer", help="your adventurer's name")
    parser.add_argument("--seed", type=int, help="repeat a dungeon layout and its random events")
    parser.add_argument("--floors", type=int, choices=range(1, 6), default=5, help="campaign length (1–5 floors)")
    args = parser.parse_args()
    name = args.name.strip() or "Adventurer"
    game = Game(name=name, seed=args.seed, floors=args.floors)
    print("\n".join(title_screen(shutil.get_terminal_size(fallback=(80, 25)).columns)))
    try:
        if sys.stdin is not None and sys.stdin.isatty():
            input("\nPress Enter to enter the catacombs...")
        # The title art supplies the heading; the engine supplies the story.
        print("\n".join(game.introduction()[1:]))
        while not game.over:
            command = input("\n> ")
            print("\n".join(game.handle_command(command)))
    except (EOFError, KeyboardInterrupt):
        print("\nYou leave the trial for another day.")


def launch() -> int:
    """Keep a double-clicked executable open after victory, quitting, or errors."""
    try:
        main()
        return 0
    except Exception:
        traceback.print_exc()
        return 1
    finally:
        # Redirected input must exit unattended; source runs keep normal CLI behavior.
        if getattr(sys, "frozen", False) and sys.stdin is not None and sys.stdin.isatty():
            try:
                input("\nPress Enter to close the game window...")
            except (EOFError, KeyboardInterrupt):
                pass


if __name__ == "__main__":
    raise SystemExit(launch())
