"""Small display helpers for the terminal interface."""


def health_bar(hp: int, max_hp: int, width: int = 16) -> str:
    """Show remaining health using plain characters supported by any terminal."""
    filled = max(0, min(width, round(width * hp / max_hp)))
    return "[" + "#" * filled + "-" * (width - filled) + "]"
