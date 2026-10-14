"""Package the desktop game and its terminal alternative for Windows.

Run this script using 64-bit Python 3.12 on Windows after installing
requirements-build.txt. PyInstaller does not cross-compile from Linux or
macOS to Windows.
"""

from importlib.metadata import PackageNotFoundError, version
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

if __package__:
    from .collect_licenses import (
        NoticeError, audit_analysis, collect_notices, copy_notices, verify_embedded_notices,
    )
else:
    from collect_licenses import (
        NoticeError, audit_analysis, collect_notices, copy_notices, verify_embedded_notices,
    )


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
    try:
        notices = collect_notices(ROOT, build_directory / "license-bundle")
    except (NoticeError, OSError, UnicodeError) as error:
        print(f"License collection failed: {error}", file=sys.stderr)
        return 1
    targets = (
        ("CatacombsOfThalinor", "GuiMain.py", "--windowed"),
        ("CatacombsOfThalinor-Terminal", "Main.py", "--console"),
    )
    binaries = []
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
                    "--add-data",
                    f"{notices / 'CREDITS.txt'}:.",
                    "--add-data",
                    f"{notices / 'legal'}:legal",
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
        try:
            verify_embedded_notices(executable, notices)
            dependencies = audit_analysis(build_directory / name / "Analysis-00.toc", Path(sys.base_prefix))
        except (NoticeError, OSError, UnicodeError, ValueError) as error:
            print(f"License verification failed: {error}", file=sys.stderr)
            return 1
        binaries.append({"executable": executable.name,
                         "sha256": hashlib.sha256(executable.read_bytes()).hexdigest(),
                         "native_dependencies": dependencies})
        print(f"Windows executable ready: {executable}")

    try:
        copy_notices(notices, ROOT / "dist")
        manifest = {"notice_manifest": "legal/runtime/notice-manifest.json", "executables": binaries,
                    "embedded_notice_files": [
                        {"path": path.relative_to(notices).as_posix(),
                         "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                        for path in sorted(notices.rglob("*")) if path.is_file()]}
        (ROOT / "dist" / "build-manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        # A copied EXE must still be able to display the embedded attribution.
        # Running outside the checkout catches accidental source-file reliance.
        with tempfile.TemporaryDirectory(prefix="thalinor-credits-") as unrelated:
            result = subprocess.run(
                [str(ROOT / "dist" / "CatacombsOfThalinor-Terminal.exe"), "--credits"],
                cwd=unrelated, capture_output=True, check=True, timeout=45,
            )
            if b"System Reference Document" not in result.stdout:
                raise NoticeError("Packaged --credits did not display the embedded SRD attribution.")
    except (NoticeError, OSError, subprocess.SubprocessError) as error:
        print(f"Distribution notice verification failed: {error}", file=sys.stderr)
        return 1
    print("Project credits, runtime license texts, native dependency inventory and hashes verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
