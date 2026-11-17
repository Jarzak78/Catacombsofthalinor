"""Resolved combat facts for presentation; this module never rolls or applies damage."""

from collections import deque
from copy import deepcopy


class CombatEventLog:
    """A bounded history whose reads cannot consume or mutate an event."""

    def __init__(self, limit: int = 64):
        if type(limit) is not int or limit < 1:
            raise ValueError("The visual event limit must be a positive integer.")
        self._events = deque(maxlen=limit)
        self.sequence = 0

    def append(self, event: dict) -> None:
        self.sequence += 1
        self._events.append({**deepcopy(event), "id": self.sequence})

    def events_since(self, after_id: int = 0) -> list[dict]:
        cursor = after_id if type(after_id) is int else 0
        return deepcopy([event for event in self._events if event["id"] > cursor])


def resolved_visual_event(*, source: str, kind: str, floor: int, position,
                          enemy: dict | None, target_hp: int, target_max_hp: int,
                          player_hp: int, enemy_hp: int = 0, enemy_max_hp: int = 0,
                          result=None, damage: int = 0, saved: bool | None = None) -> dict:
    """Describe an already resolved attack without affecting its participants.

    ``damage`` preserves the resolved number displayed to the player, including
    overkill. Predicted post-attack HP is clamped exactly as the combatants'
    damage methods are. Critical hits and natural-one mishaps are independent
    facts; a low-damage critical is never rewritten as a heavy blow.
    """
    hit = bool(result.hit) if result is not None else True
    amount = max(0, int(result.damage if result is not None else damage)) if hit else 0
    fumble = bool(result.critical_fail) if result is not None else False
    self_damage = result.fumble_damage if fumble else 0
    target_before = max(0, int(target_hp))
    target_after = max(0, target_before - amount)
    enemy_before = max(0, int(enemy_hp))
    player_before = max(0, int(player_hp))
    is_buff = kind in ("armor", "shield")
    enemy_after = max(0, enemy_before - (
        amount if source == "player" and not is_buff else self_damage if source == "enemy" else 0))
    player_after = max(0, player_before - (
        amount if source == "enemy" else self_damage))
    visible_enemy = None if enemy is None else {
        "name": str(enemy.get("name", "Unknown foe")), "boss": bool(enemy.get("boss", False))}
    event = {
        "source": source, "kind": kind, "floor": int(floor),
        "position": list(position), "enemy": visible_enemy,
        "roll": result.roll if result is not None else None,
        "total": result.total if result is not None else None,
        "ac": result.armor_class if result is not None else None,
        "hit": hit, "critical": bool(result.critical) if result is not None else False,
        "fumble": fumble, "near_miss": bool(result.near_miss) if result is not None else False,
        "damage": amount, "self_damage": self_damage,
        "target_hp_before": target_before, "target_hp_after": target_after,
        "target_max_hp": max(0, int(target_max_hp)),
        "killed": target_before > 0 and target_after == 0,
        "enemy_hp_before": enemy_before, "enemy_hp_after": enemy_after,
        "enemy_max_hp": max(0, int(enemy_max_hp)),
        "enemy_killed": enemy_before > 0 and enemy_after == 0,
        "player_killed": player_before > 0 and player_after == 0,
    }
    if saved is not None:
        event["saved"] = bool(saved)
    return event
