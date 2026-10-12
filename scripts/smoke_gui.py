"""Exercise the actual packaged desktop from outside the source checkout."""

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


REQUIRED_CHECKS = frozenset({
    "title_screen", "character_creation", "class_choice", "4d6_drop_lowest",
    "one_reroll", "enter_dungeon", "command_submission", "minimap",
    "room_scouting", "rogue_opening_hide", "rogue_opening_sneak", "responsive_layout",
    "instant_death", "post_death_actions", "new_adventure",
})


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/smoke_gui.py path/to/game.exe", file=sys.stderr)
        return 2
    executable = Path(sys.argv[1]).resolve()
    if not executable.is_file():
        print(f"Executable not found: {executable}", file=sys.stderr)
        return 2

    with TemporaryDirectory(prefix="thalinor-gui-smoke-") as working_directory:
        report_path = Path(working_directory) / "desktop-smoke.json"
        # A --windowed executable has no reliable stdout/stderr. Inspect the
        # report produced by real widget interaction instead of capturing them.
        result = subprocess.run(
            [str(executable), "--ui-smoke-report", str(report_path),
             "--name", "Tarin", "--seed", "7", "--floors", "5"],
            cwd=working_directory, timeout=90,
        )
        if not report_path.is_file():
            raise RuntimeError(f"The desktop did not write its smoke report (exit {result.returncode}).")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        checks = report.get("checks")
        if not isinstance(checks, list) or not all(isinstance(check, str) for check in checks):
            raise RuntimeError("The desktop smoke report contains invalid checks.")
        if result.returncode != 0 or report.get("success") is not True:
            print(json.dumps(report, indent=2))
            raise RuntimeError(f"The desktop smoke test failed (exit {result.returncode}).")
        missing = REQUIRED_CHECKS.difference(checks)
        if missing:
            raise RuntimeError(f"The desktop smoke test skipped required checks: {', '.join(sorted(missing))}")
        for check in checks:
            print(f"PASS: desktop {check}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
