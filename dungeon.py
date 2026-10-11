"""Generate and reveal a connected, seedable dungeon."""

from campaign import FLOORS
from floor_lore import LORE
from lore_notes import NOTES
from collections import deque
import random

from loot_library import (
    Loot, TREASURE_BUNDLES, ember_stone, mana_draught, rare_equipment,
    suitable_weapon_name, valuable,
)
from room import Room
from room_library import make_enemy, make_warden


DIRECTION_OFFSETS = {
    "north": (0, -1),
    "east": (1, 0),
    "south": (0, 1),
    "west": (-1, 0),
}
OPPOSITE_DIRECTION = {
    "north": "south",
    "east": "west",
    "south": "north",
    "west": "east",
}


class Dungeon:
    width = 4
    height = 3
    start = (0, 0)
    boss_position = (3, 2)

    def __init__(self, rng: random.Random, floor: int = 1, class_id: str = "fighter") -> None:
        if not 1 <= floor <= len(FLOORS):
            raise ValueError("Invalid dungeon floor.")
        if class_id not in ("fighter", "rogue", "wizard"):
            raise ValueError("Invalid adventurer class.")
        self.floor = floor
        self.class_id = class_id
        self.theme = FLOORS[floor - 1]
        self.lore = LORE[floor - 1]
        self.rooms: dict[tuple[int, int], Room] = {}
        self._create_rooms(rng)
        self._connect_rooms(rng)
        self._place_contents(rng)
        # Place authored documents in their matching rooms without extra RNG.
        by_name = {room.name: room for room in self.rooms.values()}
        for note in NOTES[floor]:
            by_name[note.room_name].note = note
        depth = floor - 1
        for room in self.rooms.values():
            if room.enemy:
                enemy = room.enemy
                enemy.max_hp += depth * (10 if enemy.boss else 5)
                enemy.hp = enemy.max_hp
                enemy.armor_class += depth
                enemy.attack_bonus += depth
                enemy.damage_bonus += depth
                enemy.xp_reward *= floor
                enemy.gold_reward *= floor
                if enemy.boss:
                    enemy.name = self.theme.guardian

    def _create_rooms(self, rng: random.Random) -> None:
        flavors = list(self.lore.rooms)
        rng.shuffle(flavors)
        for y in range(self.height):
            for x in range(self.width):
                position = (x, y)
                if position == self.start:
                    name, description = self.lore.entrance
                elif position == self.boss_position:
                    name, description = self.lore.sanctum
                else:
                    name, description = flavors.pop()
                self.rooms[position] = Room(position, name, description, {})

    def _neighbors(self, position: tuple[int, int]):
        x, y = position
        for direction, (dx, dy) in DIRECTION_OFFSETS.items():
            destination = (x + dx, y + dy)
            if destination in self.rooms:
                yield direction, destination

    def _link(self, origin: tuple[int, int], direction: str, destination: tuple[int, int]) -> None:
        self.rooms[origin].exits[direction] = destination
        self.rooms[destination].exits[OPPOSITE_DIRECTION[direction]] = origin

    def _connect_rooms(self, rng: random.Random) -> None:
        # Build all ordinary routes first so the boss cannot block exploration.
        reached = {self.start}
        stack = [self.start]
        while stack:
            current = stack[-1]
            choices = [
                (direction, destination)
                for direction, destination in self._neighbors(current)
                if destination not in reached and destination != self.boss_position
            ]
            if not choices:
                stack.pop()
                continue
            direction, destination = rng.choice(choices)
            self._link(current, direction, destination)
            reached.add(destination)
            stack.append(destination)

        # A few additional passages let explorers circle around and backtrack.
        missing_links = [
            (position, direction, destination)
            for position in self.rooms
            for direction, destination in self._neighbors(position)
            if position != self.boss_position
            and destination != self.boss_position
            and direction in ("east", "south")
            and direction not in self.rooms[position].exits
        ]
        rng.shuffle(missing_links)
        for origin, direction, destination in missing_links[:2]:
            self._link(origin, direction, destination)

        # The final chamber is a terminal branch, never a route to other rooms.
        direction, destination = rng.choice(list(self._neighbors(self.boss_position)))
        self._link(self.boss_position, direction, destination)

    def _place_contents(self, rng: random.Random) -> None:
        positions = [
            position for position in self.rooms
            if position not in (self.start, self.boss_position)
        ]
        rng.shuffle(positions)

        # Place the runeblade in a nearest room, giving every run an early upgrade.
        distances = {self.start: 0}
        frontier = deque([self.start])
        while frontier:
            position = frontier.popleft()
            for destination in self.rooms[position].exits.values():
                if destination not in distances:
                    distances[destination] = distances[position] + 1
                    frontier.append(destination)
        weapon_position = min(positions, key=distances.__getitem__)
        positions.remove(weapon_position)
        self.rooms[weapon_position].loot = (TREASURE_BUNDLES[-1] if self.floor == 1
                                                  else Loot(gold=12 * self.floor, potions=2))

        treasures = list(TREASURE_BUNDLES[:-1])
        rng.shuffle(treasures)
        for position, treasure in zip(positions[:3], treasures):
            self.rooms[position].loot = Loot(gold=treasure.gold * self.floor, potions=treasure.potions)
        for position in positions[3:]:
            self.rooms[position].enemy = make_enemy(rng)
        self.rooms[self.boss_position].enemy = make_warden()
        # Generate extras only after the original placement and monster rolls.
        # Loot variety therefore cannot alter this floor's layout or enemies.
        self._enrich_treasure(rng, [weapon_position, *positions[:3]])

    def _enrich_treasure(self, rng: random.Random, cache_positions: list[tuple[int, int]]) -> None:
        extras = (
            (valuable(self.floor),),
            (valuable(self.floor, 1),),
            (valuable(self.floor, 2), ember_stone()),
            (valuable(self.floor, 3), mana_draught()),
        )
        for index, position in enumerate(cache_positions):
            room = self.rooms[position]
            original = room.loot
            weapon_name = original.weapon_name
            if weapon_name and self.class_id != "fighter":
                weapon_name = suitable_weapon_name(self.class_id, original.weapon_bonus)
            equipment = {}
            # Keep the first-floor opening weapon guaranteed, with additional
            # upgrades rare rather than giving every chamber another weapon.
            guaranteed_weapon = index == 0 and self.floor == 1
            if not guaranteed_weapon and rng.random() < 0.15:
                equipment = rare_equipment(rng, self.floor, self.class_id)
            room.loot = Loot(
                gold=original.gold,
                potions=original.potions,
                weapon_name=equipment.get("weapon_name", weapon_name),
                weapon_bonus=equipment.get("weapon_bonus", original.weapon_bonus),
                items=extras[index],
                armor_name=equipment.get("armor_name"),
                armor_bonus=equipment.get("armor_bonus", 0),
            )

        for room in self.rooms.values():
            if not room.enemy:
                continue
            items = ()
            if rng.random() < 0.35:
                kind = rng.randrange(6)
                item = (valuable(self.floor, kind) if kind < 4 else
                        ember_stone() if kind == 4 else mana_draught())
                items = (item,)
            equipment = rare_equipment(rng, self.floor, self.class_id) if rng.random() < 0.08 else {}
            if items or equipment:
                room.loot = Loot(items=items, **equipment)

    def get_room(self, position: tuple[int, int]) -> Room:
        return self.rooms[position]

    def map_lines(self, current_position: tuple[int, int]) -> list[str]:
        """Render visited rooms and passages; preserve mystery in unseen rooms."""
        self.get_room(current_position)  # Reject invalid map positions consistently.
        lines = []
        for y in range(self.height):
            room_line = []
            passage_line = []
            for x in range(self.width):
                position = (x, y)
                room = self.rooms[position]
                if position == current_position:
                    marker = "@"
                elif not room.visited:
                    marker = "?"
                elif room.enemy and room.enemy.is_alive:
                    marker = "B" if room.enemy.boss else "E"
                elif room.loot and room.loot.has_treasure and not room.looted:
                    marker = "$"
                elif room.note and not room.note_collected:
                    marker = "N"
                else:
                    marker = "."
                room_line.append(marker)
                if x < self.width - 1:
                    east = self.rooms[(x + 1, y)]
                    visible = room.visited or east.visited or position == current_position or east.position == current_position
                    room_line.append("---" if visible and "east" in room.exits else "   ")
                if y < self.height - 1:
                    south = self.rooms[(x, y + 1)]
                    visible = room.visited or south.visited or position == current_position or south.position == current_position
                    passage_line.append("|" if visible and "south" in room.exits else " ")
                    if x < self.width - 1:
                        passage_line.append("   ")
            lines.append("".join(room_line).rstrip())
            if y < self.height - 1:
                lines.append("".join(passage_line).rstrip())
        return lines
