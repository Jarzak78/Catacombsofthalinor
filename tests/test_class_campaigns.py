"""Real five-floor Rogue and Wizard campaigns and source-launcher replays."""

from collections import deque
from dataclasses import replace
from heapq import heappop, heappush
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from game import Game
from campaign import FLOORS, preferred_item_id, stock
from loot_library import roll_room_loot as original_roll_room_loot
from monster_catalog import MONSTERS_BY_NAME
from tests.test_game import complete_adventure


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
        for _ in range(150):
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
                foe = game.enemy
                maximum_regular_hit = (foe.damage_dice[0] * foe.damage_dice[1]
                                       + foe.damage_bonus)
                if (player.hp < player.max_hp
                        and player.hp <= maximum_regular_hit
                        and game.previous_position is not None
                        and game.actions_remaining
                        and (player.level < 2 or game.bonus_action_available)):
                    # A low potion roll may leave the Rogue within one
                    # ordinary hit of death. Disengage and recover along a
                    # cleared route rather than repeatedly trading strikes.
                    act("flee")
                    return
                if game.actions_remaining:
                    # Vex provides accuracy, not Sneak Attack eligibility.
                    # At level one ordinary Hide consumes the attack action;
                    # repeated DC-20 attempts expose a fragile Rogue to many
                    # free strikes. Use the free opening attempt, then strike.
                    # Cunning Action makes later in-combat Hide worthwhile.
                    if (not game.hidden and player.level >= 2
                            and game.bonus_action_available):
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

    def wizard_ready():
        if class_id != "wizard":
            return True
        # Mage Armor uses one level-one slot; higher-level attack spells
        # should be available before taking on the next unfamiliar foe.
        return all(game.player.spell_slots.get(level, 0) >= maximum - (level == 1)
                   for level, maximum in game.player.max_spell_slots.items())

    def recover_if_needed(for_guardian=False):
        if game.over or game.enemy is not None or not game.player.is_conscious:
            return
        player = game.player
        missing_health = player.hp < player.max_hp - 3
        missing_slots = not wizard_ready()
        if missing_health or (missing_slots and player.arcane_recovery_available):
            act("rest")
        # A detected arrival can allow an immediate advantaged strike. The
        # Rogue has no Second Wind, so enter unfamiliar rooms fully healed.
        safe_health = (player.max_hp if for_guardian or class_id == "rogue"
                       else max(player.max_hp - 5, 5 + game.floor * 2))
        if player.hp >= safe_health and wizard_ready():
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

    def careful_route(target):
        """Prefer cleared passages, then fewer and weaker unavoidable foes."""
        frontier = [(0, 0, game.position, [])]
        cheapest = {}
        while frontier:
            risk, distance, position, route = heappop(frontier)
            if position in cheapest:
                continue
            cheapest[position] = (risk, distance)
            if position == target:
                return risk, route
            for direction, destination in game.dungeon.get_room(position).exits.items():
                if destination == game.dungeon.boss_position and destination != target:
                    continue
                if destination in cheapest:
                    continue
                enemy = game.dungeon.get_room(destination).enemy
                danger = 0 if enemy is None or not enemy.is_alive else 1000 + enemy.hp * enemy.armor_class
                heappush(frontier, (risk + danger, distance + 1, destination,
                                    [*route, direction]))
        raise AssertionError(f"No route to {target}")

    def shop_wisely():
        act("sell all")
        offers = {item.id: item for item in stock(game.floor, class_id)}
        for kind in ("weapon", "armor"):
            item_id = preferred_item_id(game.floor, class_id, kind)
            act("buy " + item_id)
            # A purchased item may be a deliberate tradeoff. Prefer the
            # class's normal Vex blade or spell focus, without reducing its
            # enchantment below a stronger find already worn.
            current = (game.player.equipped_weapon if kind == "weapon"
                       else game.player.equipped_armor)
            desired = next((item for item in game.player.equipment_inventory
                            if item.id == item_id), None)
            if desired is not None and desired.bonus >= current.bonus:
                act("equip " + item_id)
            act("sell all")
        for item in ("charm", "ward"):
            act("buy " + item)
        while game.player.potions < 5 and game.player.gold >= offers["potion"].price:
            act("buy potion")
        if game.player.gold >= offers["ember"].price:
            act("buy ember")
        if class_id == "wizard" and game.player.gold >= offers["mana"].price:
            act("buy mana")

    act("skills")
    while not game.over:
        if class_id == "wizard":
            act("cast armor")
        targets = {position for position in game.dungeon.rooms
                   if position != game.dungeon.boss_position}
        while targets and not game.over:
            # Test automation knows the generated map and chooses safe
            # rooms first. All movement, looting and recovery remain actual
            # commands, and source-launcher replay uses the same command list.
            target = min(targets, key=lambda position: (
                careful_route(position)[0],
                0 if game.dungeon.get_room(position).loot else 1,
                len(careful_route(position)[1]), position))
            while game.position != target and not game.over:
                direction = careful_route(target)[1][0]
                act(direction)
                if game.enemy:
                    clear_room()
                    if not game.over:
                        recover_if_needed()
            if game.over:
                break
            clear_room()
            targets.remove(target)
            recover_if_needed()
        if not game.over:
            recover_if_needed(for_guardian=True)
            target = game.dungeon.boss_position
            while game.position != target and not game.over:
                act(careful_route(target)[1][0])
                if game.enemy:
                    clear_room()
                    if not game.over and game.position != target:
                        recover_if_needed(for_guardian=True)
            if not game.over:
                clear_room()
        if game.over:
            break
        if not game.floor_cleared:
            raise AssertionError("Exploring the floor did not defeat its guardian.")
        act("portal")
        shop_wisely()
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
                defeated = {line.removeprefix("You defeat ").split("!")[0]
                            for line in transcript if line.startswith("You defeat ")}
                self.assertEqual(defeated, set(MONSTERS_BY_NAME)
                                 | {floor.guardian for floor in FLOORS})
                self.assertEqual(game.player.second_wind_uses, 0)
                self.assertFalse(game.player.action_surge_available)
                self.assertIn(weapon, game.player.weapon_name)
                self.assertEqual(game.player.weapon_bonus, 3)
                self.assertEqual(game.player.armor_bonus, 3)
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

    def test_all_classes_can_complete_the_campaign_without_any_equipment_drops(self):
        """Earned gold and reliable shops suffice when gear rolls yield nothing."""
        for class_id, seed in (("fighter", 0), ("rogue", 0), ("wizard", 1)):
            with self.subTest(class_id=class_id):
                generated_loot = []

                def no_equipment(rng, floor, adventurer_class, source="cache"):
                    # Retain the real loot rolls and every non-equipment
                    # reward; suppress finds rather than adding resources.
                    loot = replace(original_roll_room_loot(rng, floor, adventurer_class, source),
                                   equipment=())
                    generated_loot.append(loot)
                    return loot

                with patch("dungeon.roll_room_loot", side_effect=no_equipment):
                    if class_id == "fighter":
                        game, commands, transcript = complete_adventure(seed, floors=5)
                    else:
                        game, commands, transcript = complete_class_adventure(class_id, seed)
                self.assertTrue(game.won, "\n".join(transcript[-20:]))
                self.assertTrue(game.player.is_alive)
                self.assertEqual(len(generated_loot), 55)
                self.assertTrue(all(not loot.equipment for loot in generated_loot))
                self.assertEqual(len(game.journal), 20)
                self.assertEqual(game.player.weapon_bonus, 3)
                self.assertEqual(game.player.armor_bonus, 3)
                self.assertGreaterEqual(game.player.gold, 0)
                self.assertTrue(any(line.startswith("Bought ") and " +3 for " in line
                                    for line in transcript))
                self.assertEqual(commands.count("portal"), 5)
                self.assertEqual(commands.count("descend"), 5)

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
