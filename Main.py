"""Launch Catacombs of Thalinor with ``python3 Main.py``."""

import argparse
import random
import shutil
import sys
import traceback

from character_creation import canonical_class, select_character
from game import Game
from presentation import print_messages
from title_screen import title_screen


def main() -> None:
    parser = argparse.ArgumentParser(description="Conquer your first dungeon in Thalinor.")
    parser.add_argument("--name", default="Adventurer", help="your adventurer's name")
    parser.add_argument("--seed", type=int, help="repeat a dungeon layout and its random events")
    parser.add_argument("--floors", type=int, choices=range(1, 6), default=5, help="campaign length (1–5 floors)")
    parser.add_argument("--class", dest="class_id", choices=("fighter", "warrior", "rogue", "rouge", "wizard"),
                        help="choose a class before rolling your starting ability scores")
    parser.add_argument("--quick-start", action="store_true",
                        help="skip character creation and use the selected class's preset ability scores")
    args = parser.parse_args()
    name = args.name.strip() or "Adventurer"
    print("\n".join(title_screen(shutil.get_terminal_size(fallback=(80, 25)).columns)))
    try:
        if args.quick_start:
            class_id = canonical_class(args.class_id or "fighter")
            game = Game(name=name, seed=args.seed, floors=args.floors, class_id=class_id)
        else:
            # Character rolls and rerolls never consume the dungeon/combat RNG.
            player = select_character(random.Random(args.seed), name=name, class_id=args.class_id)
            if player is None:
                print("\nYou leave the trial for another day.")
                return
            game = Game(name=name, seed=args.seed, floors=args.floors, player=player)
        # The title art supplies the heading; the engine supplies the story.
        print_messages(game.introduction()[1:])
        while not game.over:
            command = input("\n> ")
            print_messages(game.handle_command(command))
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
