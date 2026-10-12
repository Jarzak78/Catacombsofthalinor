"""Real five-floor Rogue and Wizard campaigns and source-launcher replays."""

from collections import deque
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from game import Game
from tests.test_game import route_to


ROOT = Path(__file__).resolve().parents[1]


def complete_class_adventure(class_id, seed, floors=5):
    """Win with preset scores, actual rolls, earned gear, and legal rests.

    Every change to health, time, equipment, or resources goes through a
    player command. Safe routes back to the entrance permit a long rest
    when healing supplies or spell slots run low; short rests advance the
    required cooldown without spending Hit Dice unnecessarily.
    """
    if class_id not in ("rogue", "wizard"):
        raise ValueError("This playtest supports Rogue and Wizard campaigns.")
    game = Game(name="Tarin", seed=seed, class_id=class_id, floors=floors)
    commands, transcript = [], []

    def act(command):
        commands.append(command)
        transcript.extend(game.handle_command(command))

    def clear_room():
        for turn in range(150):
            if game.over or game.enemy is None:
                break
            player = game.player
            if game.free_examine_available:
                act("examine")
            if class_id == "rogue" and game.opening_hide_available:
                act("hide")
                # A failed opening Hide resolves initiative and may expose
                # the Rogue to an immediate attack before choosing tactics.
                if game.over or game.enemy is None:
                    break
            if (player.hp <= player.max_hp - 4 and game.bonus_action_available
                    and player.potions):
                act("potion")
            if class_id == "rogue":
                if game.actions_remaining:
                    if not game.hidden and not game.rogue_vex:
                        if player.level >= 2 and game.bonus_action_available:
                            act("hide")
                        elif player.level == 1 and turn == 0:
                            act("hide")
                    if game.actions_remaining:
                        if game.hidden and game.enemy_unaware:
                            act("attack")
                        elif (player.ember_stones and game.enemy.hp >= 10
                                and player.level < 3):
                            act("ember")
                        else:
                            act("attack")
            else:
                if game.actions_remaining:
                    if (player.spell_slots.get(3, 0)
                            and (game.enemy.boss or game.enemy.hp >= 24)):
                        act("cast fireball")
                    elif player.spell_slots.get(2, 0) and game.enemy.hp >= 12:
                        act("cast frost")
                    elif player.spell_slots.get(1, 0):
                        act("cast missile")
                    elif player.ember_stones:
                        act("ember")
                    else:
                        act("attack")
                if game.enemy and game.bonus_action_available:
                    if not player.spell_slots.get(1, 0) and player.mana_draughts:
                        act("mana")
                    elif player.spell_slots.get(1, 0):
                        act("cast shield")
            if game.enemy:
                act("end")
        if not game.over:
            if game.enemy is not None:
                raise AssertionError("Combat did not finish within 150 turns.")
            act("loot")

    def safe_route_to_entrance():
        frontier = deque([(game.position, [])])
        seen = {game.position}
        while frontier:
            position, route = frontier.popleft()
            if position == game.dungeon.start:
                return route
            for direction, target in game.dungeon.get_room(position).exits.items():
                room = game.dungeon.get_room(target)
                if target not in seen and (room.enemy is None or not room.enemy.is_alive):
                    seen.add(target)
                    frontier.append((target, [*route, direction]))
        return None

    def recover_if_needed():
        if game.over or not game.player.is_conscious:
            return
        player = game.player
        missing_health = player.hp < player.max_hp - 3
        missing_slots = class_id == "wizard" and not player.spell_slots.get(1, 0)
        if missing_health or (missing_slots and player.arcane_recovery_available):
            act("rest")
        if (player.hp >= max(player.max_hp - 5, 5 + game.floor * 2)
                and (class_id != "wizard" or player.spell_slots.get(1, 0))):
            return
        route = safe_route_to_entrance()
        if route is None:
            return
        for direction in route:
            act(direction)
        while game.elapsed_minutes - game.last_long_rest_end < 960:
            act("rest 0")
        act("long rest")
        if class_id == "wizard":
            act("cast armor")

    act("skills")
    while not game.over:
        if class_id == "wizard":
            act("cast armor")
        targets = [position for position in game.dungeon.rooms
                   if position != game.dungeon.boss_position]
        # A rare boss drop must never displace the safe, early weapon cache.
        weapon_room = next((position for position, room in game.dungeon.rooms.items()
                            if position != game.dungeon.boss_position
                            and room.loot and room.loot.weapon_name), None)
        if weapon_room is not None:
            targets.remove(weapon_room)
            targets.insert(0, weapon_room)
        targets.append(game.dungeon.boss_position)
        for target in targets:
            for direction in route_to(game, target):
                act(direction)
                if game.enemy:
                    clear_room()
                if game.over:
                    break
            if game.over:
                break
            clear_room()
            if target != game.dungeon.boss_position:
                recover_if_needed()
        if game.over:
            break
        if not game.floor_cleared:
            raise AssertionError("Exploring the floor did not defeat its guardian.")
        act("portal")
        act("sell all")
        for item in ("sword", "armor", "charm", "ward"):
            act("buy " + item)
        for _ in range(4):
            act("buy potion")
        act("buy ember")
        if class_id == "wizard":
            act("buy mana")
        act("journal")
        act("read")
        act("descend")
    return game, commands, transcript


class ClassCampaignTests(unittest.TestCase):
    def test_both_classes_complete_five_floors_using_their_own_abilities(self):
        for class_id, seed, weapon, evidence in (
                ("rogue", 0, "Rapier", "Sneak Attack:"),
                ("wizard", 1, "Staff", "Fire Bolt:")):
            with self.subTest(class_id=class_id):
                game, commands, transcript = complete_class_adventure(class_id, seed)
                self.assertTrue(game.won)
                self.assertTrue(game.player.is_conscious)
                self.assertEqual(game.player.class_id, class_id)
                self.assertEqual((game.floor, game.player.level), (5, 5))
                self.assertEqual(len(game.journal), 20)
                self.assertEqual(len({note.id for note in game.journal}), 20)
                self.assertEqual(game.player.second_wind_uses, 0)
                self.assertFalse(game.player.action_surge_available)
                self.assertIn(weapon, game.player.weapon_name)
                self.assertGreaterEqual(game.player.weapon_bonus, 4)
                self.assertGreaterEqual(game.player.armor_bonus, 4)
                self.assertGreaterEqual(game.player.gold, 0)
                self.assertIn(evidence, "\n".join(transcript))
                self.assertIn("Perception check:", "\n".join(transcript))
                self.assertTrue(any("Mira buys your treasure" in line for line in transcript))
                self.assertTrue(any(command in ("rest", "potion") for command in commands))
                self.assertNotIn("wind", commands)
                self.assertNotIn("surge", commands)
                if class_id == "wizard":
                    self.assertIn("rest", commands)
                    self.assertIn("long rest", commands)
                    for spell in ("cast armor", "cast missile", "cast frost", "cast fireball"):
                        self.assertIn(spell, commands)
                else:
                    self.assertIn("Opening Hide:", "\n".join(transcript))
                    self.assertIn("Your opening Hide attempt spends no action or bonus action.",
                                  "\n".join(transcript))

    def test_source_launcher_replays_both_complete_campaigns_outside_checkout(self):
        for class_id, seed in (("rogue", 0), ("wizard", 1)):
            with self.subTest(class_id=class_id):
                game, commands, _ = complete_class_adventure(class_id, seed)
                self.assertTrue(game.won)
                with tempfile.TemporaryDirectory() as directory:
                    result = subprocess.run(
                        [sys.executable, str(ROOT / "Main.py"), "--quick-start",
                         "--class", class_id, "--seed", str(seed), "--name", "Tarin"],
                        input="\n".join(commands) + "\n", capture_output=True,
                        text=True, encoding="utf-8", timeout=20, cwd=directory,
                        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                    )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertIn("Your first dungeon is conquered!", result.stdout)
                self.assertIn("20 collected note(s)", result.stdout)
                self.assertIn(game.player.class_name, result.stdout)
                self.assertIn("Mira buys your treasure", result.stdout)
                self.assertIn("Perception check:", result.stdout)
                if class_id == "rogue":
                    self.assertIn("Opening Hide:", result.stdout)
                    self.assertIn("Sneak Attack:", result.stdout)


if __name__ == "__main__":
    unittest.main()
