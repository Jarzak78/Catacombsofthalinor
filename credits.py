"""Read the same attribution text in source and packaged game interfaces."""

from pathlib import Path
import sys


def credits_text() -> str:
    """Resolve beside this module, independent of the player's working folder."""
    return Path(__file__).with_name("CREDITS.txt").read_text(encoding="utf-8").strip()


def credits_lines() -> list[str]:
    return credits_text().splitlines()


def notice_documents() -> dict[str, Path]:
    """Offer source and exact-build notices, including those embedded in an EXE."""
    root = Path(__file__).resolve().parent
    documents = {"CREDITS.txt": root / "CREDITS.txt"}
    for path in sorted((root / "legal").rglob("*")):
        if path.is_file() and path.suffix.lower() in (".txt", ".terms", ".md", ".rst", ".json"):
            documents[path.relative_to(root).as_posix()] = path
    return documents


def runtime_terms_required() -> bool:
    return sys.platform == "win32" and bool(getattr(sys, "frozen", False))


def runtime_terms_text() -> str:
    return (Path(__file__).resolve().parent / "legal" / "END_USER_TERMS.txt").read_text(
        encoding="utf-8").strip()
