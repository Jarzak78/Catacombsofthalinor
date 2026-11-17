"""Input adapters send actions; the engine has no keyboard/window dependency."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Action:
    kind: str
    argument: str = ""
