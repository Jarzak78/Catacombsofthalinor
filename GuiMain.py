"""Launch the desktop game with ``python GuiMain.py`` or the Windows EXE."""

import argparse
import json
from pathlib import Path
import sys
import traceback


def _show_launch_error(error: Exception) -> None:
    """Make startup failures visible when the windowed EXE has no console."""
    if sys.stderr is not None:
        traceback.print_exc()
    try:
        from tkinter import messagebox

        messagebox.showerror(
            "Catacombs of Thalinor",
            f"The game could not start.\n\n{error}",
        )
    except Exception:
        # A missing display or Tk runtime must not obscure the original failure.
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Explore the Catacombs of Thalinor.")
    parser.add_argument("--name", default="Adventurer", help="your adventurer's name")
    parser.add_argument("--seed", type=int, help="repeat a dungeon layout and its random events")
    parser.add_argument("--floors", type=int, choices=range(1, 6), default=5,
                        help="campaign length (1–5 floors)")
    parser.add_argument("--ui-smoke-report", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    name = args.name.strip() or "Adventurer"
    try:
        # Import lazily so command-line help and tests do not create a Tk window.
        from desktop_ui import run_gui, run_gui_smoke

        if args.ui_smoke_report is not None:
            run_gui_smoke(args.ui_smoke_report, name=name, seed=args.seed, floors=args.floors)
            report = json.loads(args.ui_smoke_report.read_text(encoding="utf-8"))
            return 0 if report.get("success") is True else 1
        run_gui(name=name, seed=args.seed, floors=args.floors)
        return 0
    except Exception as error:
        if args.ui_smoke_report is not None:
            # Automated desktop checks must fail without opening a modal dialog.
            failure = {"success": False, "checks": [], "error": str(error),
                       "traceback": traceback.format_exc()}
            try:
                args.ui_smoke_report.write_text(json.dumps(failure, indent=2), encoding="utf-8")
            except OSError:
                if sys.stderr is not None:
                    traceback.print_exc()
        else:
            _show_launch_error(error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
