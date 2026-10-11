"""Headless desktop flow and a fog-of-war map for graphical front ends.

This module owns no widgets. Character rolls use a separate random generator
from the adventure, and every game command goes through the existing engine.
"""

from dataclasses import asdict
import random

from character_creation import (
    AbilityRoll, CLASS_NAMES, canonical_class, roll_ability_scores,
)
from game import Game
from player import Player


class DesktopSession:
    """One character creation followed by one adventure.

    Going back to the title or changing class preserves the rolled scores and
    the one-reroll limit. Accepting the character locks creation choices.
    """

    def __init__(self, name: str = "Adventurer", seed: int | None = None,
                 floors: int = 5):
        if not 1 <= floors <= 5:
            raise ValueError("Choose between 1 and 5 floors.")
        self.name = name.strip() or "Adventurer"
        self.seed = seed
        self.floors = floors
        self.scene = "title"
        self.class_id = "fighter"
        self.rolls: tuple[AbilityRoll, ...] | None = None
        self.reroll_used = False
        self.accepted_player: Player | None = None
        self.game: Game | None = None
        self.stat_rng = random.Random(seed)

    def begin_creation(self) -> None:
        if self.game is not None:
            raise ValueError("Your adventure has already begun.")
        self.scene = "creation"

    def show_title(self) -> None:
        """Return to the title without granting a fresh set of rolls."""
        if self.game is not None:
            raise ValueError("Your adventure has already begun.")
        self.scene = "title"

    def _require_editable(self) -> None:
        if self.scene != "creation":
            raise ValueError("Open character creation first.")
        if self.accepted_player is not None:
            raise ValueError("Your character is accepted; enter the dungeon.")

    def choose_class(self, class_id: str) -> None:
        self._require_editable()
        self.class_id = canonical_class(class_id)

    def set_name(self, name: str) -> None:
        self._require_editable()
        self.name = name.strip() or "Adventurer"

    def roll_stats(self) -> tuple[AbilityRoll, ...]:
        self._require_editable()
        if self.rolls is not None:
            raise ValueError("Your scores are already rolled. Use your one reroll if available.")
        self.rolls = roll_ability_scores(self.stat_rng)
        return self.rolls

    def reroll_stats(self) -> tuple[AbilityRoll, ...]:
        self._require_editable()
        if self.rolls is None:
            raise ValueError("Roll your starting scores first.")
        if self.reroll_used:
            raise ValueError("You have already used your one reroll.")
        self.rolls = roll_ability_scores(self.stat_rng)
        self.reroll_used = True
        return self.rolls

    def _rolled_player(self) -> Player:
        if self.rolls is None:
            raise ValueError("Roll your starting scores before accepting your character.")
        return Player.create(
            name=self.name, class_id=self.class_id,
            stats={roll.stat: roll.total for roll in self.rolls},
        )

    def accept_character(self) -> Player:
        if self.accepted_player is not None:
            return self.accepted_player
        self._require_editable()
        self.accepted_player = self._rolled_player()
        return self.accepted_player

    def enter_dungeon(self) -> list[str]:
        if self.accepted_player is None:
            raise ValueError("Accept your character before entering the dungeon.")
        if self.game is not None:
            raise ValueError("Your adventure has already begun.")
        self.game = Game(player=self.accepted_player, seed=self.seed, floors=self.floors)
        self.scene = "dungeon"
        return self.game.introduction()

    def submit_command(self, raw: str) -> list[str]:
        if self.game is None or self.scene != "dungeon":
            raise ValueError("Enter the dungeon before issuing commands.")
        return self.game.handle_command(raw)

    def get_state(self) -> dict:
        """Return detached display data without advancing time or any dice."""
        if self.game is not None:
            return self.game.get_state()
        player = self.accepted_player
        if player is None and self.rolls is not None:
            player = self._rolled_player()
        preview = None
        if player is not None:
            preview = {
                "name": player.name, "class_id": player.class_id,
                "class_name": player.class_name, "hp": player.hp,
                "max_hp": player.max_hp, "armor_class": player.armor_class,
                "attack_bonus": player.attack_bonus, "weapon_name": player.weapon_name,
                "spell_attack_bonus": player.spell_attack_bonus if player.class_id == "wizard" else None,
                "spell_save_dc": player.spell_save_dc if player.class_id == "wizard" else None,
            }
        rolls = None if self.rolls is None else [
            {**asdict(roll), "dice": list(roll.dice)} for roll in self.rolls
        ]
        return {
            "scene": self.scene, "name": self.name, "class_id": self.class_id,
            "class_name": CLASS_NAMES[self.class_id], "rolls": rolls,
            "reroll_used": self.reroll_used,
            "reroll_available": self.rolls is not None and not self.reroll_used and self.accepted_player is None,
            "accepted": self.accepted_player is not None, "preview": preview,
        }

    def snapshot(self) -> dict:
        return self.get_state()


def minimap_data(state: dict) -> dict:
    """Reduce an engine snapshot to explored rooms and visible connections.

    Unknown rooms disclose coordinates only. Their hidden metadata is ignored
    even if a caller accidentally supplies it. Connections come exclusively
    from visited rooms, never from a hidden room's exits.
    """
    if state.get("scene") == "shop":
        return {"visible": False, "label": "The Lantern Between Worlds",
                "width": 0, "height": 0, "nodes": [], "edges": []}
    rooms = state.get("rooms", [])
    current = tuple(state.get("position", []))
    positions = {tuple(room["position"]) for room in rooms}
    nodes = []
    edges = set()
    for room in sorted(rooms, key=lambda candidate: (candidate["position"][1], candidate["position"][0])):
        position = tuple(room["position"])
        x, y = position
        visited = bool(room.get("visited", False))
        marker = "?"
        if visited:
            enemy = room.get("enemy")
            loot = room.get("loot")
            if enemy and enemy.get("hp", 0) > 0:
                marker = "B" if enemy.get("boss", False) else "E"
            elif loot and any(loot.get(key) for key in ("gold", "potions", "weapon_name", "items", "armor_name")):
                marker = "$"
            elif room.get("note") and not room.get("note_collected", False):
                marker = "N"
            else:
                marker = "."
            for destination in room.get("exits", {}).values():
                destination = tuple(destination)
                if destination in positions:
                    edges.add(tuple(sorted((position, destination))))
        if position == current:
            marker = "@"
        node = {"x": x, "y": y, "visited": visited, "marker": marker}
        if visited and "name" in room:
            node["name"] = room["name"]
        nodes.append(node)
    return {
        "visible": bool(nodes),
        "label": f"Floor {state.get('floor', 1)} · {state.get('theme', 'Dungeon')}",
        "width": max((node["x"] for node in nodes), default=-1) + 1,
        "height": max((node["y"] for node in nodes), default=-1) + 1,
        "nodes": nodes,
        "edges": [{"start": list(start), "end": list(end)} for start, end in sorted(edges)],
    }
