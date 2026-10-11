"""Package the desktop game and its terminal alternative for Windows.

Run this script using 64-bit Python 3.12 on Windows after installing
requirements-build.txt. PyInstaller does not cross-compile from Linux or
macOS to Windows.
"""

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import struct
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
PYINSTALLER_VERSION = "6.16.0"


def main() -> int:
    """Validate the build environment and create both Windows executables."""
    if sys.platform != "win32":
        print(
            "Build this Windows executable on Windows. PyInstaller cannot "
            "cross-compile a Windows .exe from Linux or macOS.",
            file=sys.stderr,
        )
        return 2

    if sys.version_info[:2] != (3, 12):
        print(
            "Use Python 3.12 for this build: py -3.12 scripts/build_windows.py",
            file=sys.stderr,
        )
        return 2

    if struct.calcsize("P") * 8 != 64:
        print("Use a 64-bit installation of Python 3.12.", file=sys.stderr)
        return 2

    try:
        installed_version = version("PyInstaller")
    except PackageNotFoundError:
        installed_version = None

    if installed_version != PYINSTALLER_VERSION:
        print(
            f"This build requires PyInstaller=={PYINSTALLER_VERSION}. "
            "Install the pinned build dependency with:\n"
            f'  py -3.12 -m pip install -r "{ROOT / "requirements-build.txt"}"',
            file=sys.stderr,
        )
        return 2

    build_directory = ROOT / "build"
    build_directory.mkdir(parents=True, exist_ok=True)
    targets = (
        ("CatacombsOfThalinor", "GuiMain.py", "--windowed"),
        ("CatacombsOfThalinor-Terminal", "Main.py", "--console"),
    )
    for name, entry_point, window_mode in targets:
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "PyInstaller",
                    "--noconfirm",
                    "--clean",
                    "--onefile",
                    window_mode,
                    "--name",
                    name,
                    "--distpath",
                    str(ROOT / "dist"),
                    "--workpath",
                    str(build_directory),
                    "--specpath",
                    str(build_directory),
                    str(ROOT / entry_point),
                ],
                cwd=ROOT,
                check=True,
            )
        except subprocess.CalledProcessError as error:
            print(
                f"PyInstaller failed while building {name} with exit code {error.returncode}.",
                file=sys.stderr,
            )
            return error.returncode or 1

        executable = ROOT / "dist" / f"{name}.exe"
        if not executable.is_file():
            print(f"Build did not produce the expected executable: {executable}", file=sys.stderr)
            return 1
        print(f"Windows executable ready: {executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
