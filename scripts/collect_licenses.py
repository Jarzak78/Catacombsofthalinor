"""Collect redistributable notices from the exact Windows build environment.

No game content is relicensed by this script. The installed CPython Windows
LICENSE.txt is deliberately retained whole: upstream combines the PSF, CRT,
bzip2, libffi, OpenSSL and Tcl/Tk notices there. Upstream documentation supplies
the additional notices for incorporated standard-library code.
"""

import ast
import hashlib
from importlib.metadata import distribution
import json
import os
from pathlib import Path, PureWindowsPath
import platform
import re
import shutil
import sys
from urllib.request import urlopen


class NoticeError(RuntimeError):
    """Required redistributable notices or their provenance are missing."""


PYTHON_LICENSE_MARKERS = (
    "PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2",
    "Microsoft Distributable Code",
    "libbzip2",
    "Anthony Green",
    "Apache License",
    "Regents of the University of California",
    "Sun Microsystems",
)


def require_text(data: bytes, markers: tuple[str, ...], source: str) -> None:
    """Reject missing/truncated notices, including HTML error pages."""
    text = data.decode("utf-8-sig")
    missing = [marker for marker in markers if marker.casefold() not in text.casefold()]
    if missing:
        raise NoticeError(f"Incomplete license notice {source}: missing {', '.join(missing)}")


def source_bytes(url: str, cache: Path, markers: tuple[str, ...]) -> bytes:
    """Fetch upstream notices, or use the same URL's previously verified cache.

    Set THALINOR_LICENSE_CACHE to a populated cache for an offline build. No
    certificate checks are disabled and a missing source fails the build.
    """
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / (hashlib.sha256(url.encode()).hexdigest() + ".txt")
    if path.is_file():
        data = path.read_bytes()
    else:
        try:
            with urlopen(url, timeout=30) as response:
                data = response.read()
        except OSError as error:
            raise NoticeError(f"Could not obtain required notice {url}: {error}") from error
        require_text(data, markers, url)
        path.write_bytes(data)
    require_text(data, markers, url)
    return data


def collect_notices(root: Path, destination: Path) -> Path:
    """Stage project and exact-build runtime notices before PyInstaller runs."""
    credits = root / "CREDITS.txt"
    legal = root / "legal"
    if not credits.is_file() or not credits.read_bytes().strip():
        raise NoticeError("CREDITS.txt is required before building a distributable.")
    if not (legal / "README.md").is_file():
        raise NoticeError("legal/README.md and the project's license texts are required.")
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    shutil.copy2(credits, destination / "CREDITS.txt")
    shutil.copytree(legal, destination / "legal")
    runtime = destination / "legal" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    records = []

    def retain(name: str, data: bytes, source: str, component: str) -> None:
        target = runtime / name
        target.write_bytes(data)
        records.append({"path": target.relative_to(destination).as_posix(),
                        "source": source, "component": component,
                        "sha256": hashlib.sha256(data).hexdigest()})

    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.is_file():
        raise NoticeError(f"Official Windows Python license is missing: {python_license}")
    data = python_license.read_bytes()
    require_text(data, PYTHON_LICENSE_MARKERS, str(python_license))
    retain("Python-Windows-LICENSE.txt", data, str(python_license),
           "CPython and its Windows build dependencies (including Tcl/Tk)")

    python_version = platform.python_version()
    python_source = f"https://raw.githubusercontent.com/python/cpython/v{python_version}/"
    cache = Path(os.environ.get("THALINOR_LICENSE_CACHE", root / "build" / "license-cache"))
    doc_url = python_source + "Doc/license.rst"
    retain("Python-incorporated-notices.rst", source_bytes(doc_url, cache, (
        "Licenses and Acknowledgements for Incorporated Software", "Mersenne Twister",
        "expat", "zlib", "libffi")), doc_url, "CPython incorporated software notices")

    # liblzma is built statically into _lzma.pyd. Its notices are not in
    # CPython's generated Windows LICENSE.txt or Doc/license.rst.
    props_url = python_source + "PCbuild/python.props"
    props = source_bytes(props_url, cache, ("lzmaDir", "xz-"))
    match = re.search(rb"<lzmaDir\b[^>]*>[^<]*?xz-([0-9.]+)", props)
    if not match:
        raise NoticeError("Cannot identify this CPython release's XZ/liblzma dependency.")
    xz_version = match.group(1).decode("ascii").rstrip(".")
    xz_url = f"https://raw.githubusercontent.com/python/cpython-source-deps/xz-{xz_version}/COPYING"
    retain("XZ-liblzma-COPYING.txt", source_bytes(xz_url, cache, (
        "XZ Utils Licensing", "liblzma is in the public domain")),
        xz_url, f"XZ Utils liblzma {xz_version}; no XZ command-line programs bundled")

    # Keep any individually installed Tcl/Tk notices too. The whole installed
    # Python license above is mandatory and covers installers lacking these.
    for path in sorted((Path(sys.base_prefix) / "tcl").rglob("*")):
        if path.is_file() and path.name.lower() in {"license.terms", "tcllicense.terms", "tklicense.terms"}:
            name = "TclTk-" + "-".join(path.relative_to(Path(sys.base_prefix) / "tcl").parts)
            retain(name, path.read_bytes(), str(path), "Installed Tcl/Tk notice")

    pyinstaller = distribution("PyInstaller")
    license_files = [path for path in pyinstaller.files or () if path.name == "COPYING.txt"]
    if len(license_files) != 1:
        raise NoticeError("Installed PyInstaller must supply exactly one COPYING.txt.")
    pyi_license = Path(pyinstaller.locate_file(license_files[0]))
    data = pyi_license.read_bytes()
    require_text(data, ("Bootloader Exception", "Apache License"), str(pyi_license))
    retain("PyInstaller-COPYING.txt", data, str(pyi_license),
           f"PyInstaller {pyinstaller.version}; bootloader exception and runtime hooks")
    pyi_source = f"https://raw.githubusercontent.com/pyinstaller/pyinstaller/v{pyinstaller.version}/"
    zlib_url = pyi_source + "bootloader/zlib/LICENSE"
    retain("PyInstaller-bootloader-zlib-LICENSE.txt", source_bytes(zlib_url, cache, (
        "zlib", "Jean-loup Gailly", "Mark Adler")), zlib_url, "PyInstaller bootloader zlib")
    for name, url, markers in (
        ("Apache-2.0.txt", "https://www.apache.org/licenses/LICENSE-2.0.txt",
         ("Apache License", "Version 2.0", "END OF TERMS AND CONDITIONS")),
        ("GPL-2.0.txt", "https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt",
         ("GNU GENERAL PUBLIC LICENSE", "Version 2, June 1991", "END OF TERMS AND CONDITIONS")),
    ):
        retain(name, source_bytes(url, cache, markers), url, "PyInstaller license text; see bootloader exception")

    # Preserve the authorship/license headers of the installed runtime hooks.
    import PyInstaller
    hook_directory = Path(PyInstaller.__file__).parent / "hooks" / "rthooks"
    headers = []
    for path in sorted(hook_directory.glob("*.py")):
        lines = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith("#"):
                break
            lines.append(line)
        headers.append(path.name + "\n" + "\n".join(lines))
    if not headers:
        raise NoticeError("Installed PyInstaller runtime-hook notices could not be read.")
    retain("PyInstaller-runtime-hook-notices.txt", "\n\n".join(headers).encode(),
           str(hook_directory), "Unmodified installed PyInstaller runtime-hook copyright headers")

    info = {"python": sys.version, "python_implementation": platform.python_implementation(),
            "architecture": platform.machine(), "platform": sys.platform,
            "pyinstaller": pyinstaller.version, "source_commit": os.environ.get("GITHUB_SHA", "local build"),
            "python_modifications": "None; unmodified CPython bundled by PyInstaller.",
            "dependency_modifications": "None; runtime dependencies copied from the installed Windows Python.",
            "notice_sources": records}
    (runtime / "notice-manifest.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    return destination


def binary_component(name: str, source: Path, python_root: Path) -> str:
    """Fail closed if a newly bundled native component has not been reviewed."""
    leaf = PureWindowsPath(name).name.lower()
    if re.fullmatch(r"python3(?:12)?\.dll", leaf):
        return "CPython"
    if (re.fullmatch(r"vcruntime140(?:_\d+)?\.dll", leaf) or leaf == "ucrtbase.dll"
            or re.fullmatch(r"api-ms-win-(?:core|crt)-[a-z0-9-]+\.dll", leaf)):
        return "Microsoft Windows runtime (Python-Windows-LICENSE.txt)"
    if leaf.startswith(("libcrypto-", "libssl-")) and leaf.endswith(".dll"):
        return "OpenSSL (Python-Windows-LICENSE.txt)"
    if leaf.startswith("libffi-") and leaf.endswith(".dll"):
        return "libffi (Python-Windows-LICENSE.txt)"
    if re.fullmatch(r"(?:tcl|tk)86t?\.dll", leaf):
        return "Tcl/Tk (Python-Windows-LICENSE.txt)"
    if leaf == "zlib1.dll":
        return "zlib (Python-incorporated-notices.rst)"
    # Only CPython-owned extension modules, never arbitrary site-packages.
    try:
        relative = source.resolve().relative_to(python_root.resolve())
    except ValueError:
        relative = None
    if leaf.endswith(".pyd") and relative is not None and "site-packages" not in str(relative).lower():
        return "CPython extension and incorporated dependencies (Python notices; XZ notice for _lzma)"
    raise NoticeError(f"Unreviewed bundled native component: {name} from {source}")


def audit_analysis(path: Path, python_root: Path) -> list[dict]:
    """Read PyInstaller's literal TOC without executing generated build code."""
    if not path.is_file():
        raise NoticeError(f"Missing PyInstaller dependency inventory: {path}")
    records = {}

    def walk(value):
        if not isinstance(value, (tuple, list)):
            return
        if len(value) == 3 and all(isinstance(part, str) for part in value) and value[2] in {"BINARY", "EXTENSION"}:
            name, source, kind = value
            file = Path(source)
            if not file.is_file():
                raise NoticeError(f"Bundled dependency disappeared: {source}")
            records[name] = {"name": name, "kind": kind,
                             "component": binary_component(name, file, python_root),
                             "sha256": hashlib.sha256(file.read_bytes()).hexdigest()}
        else:
            for child in value:
                walk(child)

    walk(ast.literal_eval(path.read_text(encoding="utf-8")))
    if not records:
        raise NoticeError("PyInstaller's dependency inventory did not contain native components.")
    return [records[key] for key in sorted(records)]


def verify_embedded_notices(executable: Path, staged: Path) -> None:
    """Verify every staged notice is inside the one-file executable byte-for-byte."""
    from PyInstaller.archive.readers import CArchiveReader
    archive = CArchiveReader(str(executable))
    paths = {name.replace("\\", "/"): name for name in archive.toc}
    for source in sorted(staged.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(staged).as_posix()
        if relative not in paths or archive.extract(paths[relative]) != source.read_bytes():
            raise NoticeError(f"Required notice is missing or altered in {executable.name}: {relative}")


def copy_notices(staged: Path, dist: Path) -> None:
    """Keep notices readable beside the executable as well as inside it."""
    dist.mkdir(parents=True, exist_ok=True)
    shutil.copy2(staged / "CREDITS.txt", dist / "CREDITS.txt")
    if (dist / "legal").exists():
        shutil.rmtree(dist / "legal")
    shutil.copytree(staged / "legal", dist / "legal")
