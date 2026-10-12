"""First-entry scouting and the rogue's one preparatory hide through real actions."""

import json
import random
import unittest
from unittest.mock import PropertyMock, patch

from actions import Action
from game import Game
from player import Player
from room import Enemy
from tests.test_examine_ambush import EncounterRandom


CLASSES = ("fighter", "rogue", "wizard")


def entry_game(class_id="rogue", values=(), *, visited=False, level=1):
    """Place a controlled foe across an actual passage without starting combat."""
    game = Game(seed=7, class_id=class_id)
    game.player.level = level
    direction, destination = next(iter(game.room.exits.items()))
    room = game.dungeon.get_room(destination)
    room.visited = visited
    room.enemy = Enemy("Waiting sentry", 100, 100, 12, 3, (1, 6), 1, 50, 7)
    game.rng = EncounterRandom(values)
    return game, direction, destination


class ScoutingTests(unittest.TestCase):
    def assert_reset(self, game):
        self.assertIsNone(game.scouting_result)
        self.assertFalse(game.enemy_unaware)
        self.assertFalse(game.opening_hide_available)
        state = game.get_state()["encounter"]
        self.assertIsNone(state["scouting"])
        self.assertFalse(state["enemy_unaware"])
        self.assertFalse(state["opening_hide_available"])

    def test_every_class_can_spot_a_new_foe_and_act_without_initiative_dice(self):
        for class_id, die in (("fighter", 11), ("rogue", 6), ("wizard", 11)):
            with self.subTest(class_id=class_id):
                game, direction, destination = entry_game(class_id, [die])
                hp = game.player.hp
                output = game.handle_command(direction)
                self.assertEqual(game.position, destination)
                self.assertTrue(game.room.visited)
                self.assertEqual(game.elapsed_minutes, 1)
                self.assertEqual(game.player.hp, hp)
                self.assertEqual(game.scouting_result,
                                 {"roll": die, "bonus": game.player.perception_bonus,
                                  "total": 12, "dc": 12, "success": True})
                self.assertEqual(game.initiative_result,
                                 {"player": None, "enemy": None,
                                  "hero_first": True, "source": "scouting"})
                self.assertIsNone(game.perception_result)
                self.assertTrue(game.enemy_unaware)
                self.assertEqual(game.opening_hide_available, class_id == "rogue")
                self.assertTrue(game.free_examine_available)
                self.assertEqual(game.round_number, 1)
                self.assertEqual(game.actions_remaining, 1)
                self.assertTrue(game.bonus_action_available)
                self.assertFalse(game.ambush_advantage)
                self.assertEqual(game.rng.calls, [(1, 20, die)])
                self.assertIn("Perception", "\n".join(output))

    def test_scouting_uses_current_wisdom_and_rogue_expertise(self):
        for class_id, wisdom, expected_bonus, die in (
                ("fighter", 16, 3, 9), ("wizard", 8, -1, 13),
                ("rogue", 8, 5, 7)):
            with self.subTest(class_id=class_id):
                game, direction, _ = entry_game(class_id, [die], level=5)
                game.player.wisdom = wisdom
                self.assertEqual(game.player.perception_bonus, expected_bonus)
                game.handle_command(direction)
                self.assertTrue(game.scouting_result["success"])
                self.assertEqual(game.scouting_result["total"], 12)
                self.assertEqual(game.rng.calls, [(1, 20, die)])

    def test_failed_scouting_can_still_win_normal_initiative_without_free_hide(self):
        for class_id, die in (("fighter", 10), ("rogue", 5), ("wizard", 10)):
            with self.subTest(class_id=class_id):
                game, direction, _ = entry_game(class_id, [die, 20, 1])
                hp = game.player.hp
                game.handle_command(direction)
                self.assertFalse(game.scouting_result["success"])
                self.assertEqual(game.scouting_result["total"], 11)
                self.assertTrue(game.initiative_result["hero_first"])
                self.assertTrue(game.free_examine_available)
                self.assertFalse(game.enemy_unaware)
                self.assertFalse(game.opening_hide_available)
                self.assertEqual(game.player.hp, hp)
                self.assertEqual(game.round_number, 1)
                self.assertEqual(game.rng.calls, [(1, 20, die), (1, 20, 20), (1, 20, 1)])

    def test_failed_scouting_and_enemy_initiative_use_only_one_perception_check(self):
        for class_id in CLASSES:
            with self.subTest(class_id=class_id):
                game, direction, _ = entry_game(class_id, [1, 2, 20, 2, 19, 2, 2])
                hp = game.player.hp
                output = game.handle_command(direction)
                self.assertFalse(game.scouting_result["success"])
                self.assertFalse(game.initiative_result["hero_first"])
                self.assertFalse(game.enemy_unaware)
                self.assertFalse(game.opening_hide_available)
                self.assertFalse(game.free_examine_available)
                self.assertFalse(game.ambush_advantage)
                self.assertEqual(game.player.hp, hp - 3)
                self.assertIn("d20 [2/19]", "\n".join(output))
                self.assertEqual(game.rng.calls,
                                 [(1, 20, 1), (1, 20, 2), (1, 20, 20),
                                  (1, 20, 2), (1, 20, 19), (1, 6, 2)])
                second = game.handle_command("end")
                self.assertIn("d20 [2]", "\n".join(second))
                self.assertFalse(game.rng.values)

    def test_perception_natural_rolls_use_totals_instead_of_automatic_outcomes(self):
        for bonus, die, success, extra in ((11, 1, True, []), (-10, 20, False, [20, 1])):
            with self.subTest(die=die):
                with patch.object(Player, "perception_bonus", new_callable=PropertyMock) as modifier:
                    modifier.return_value = bonus
                    game, direction, _ = entry_game("fighter", [die, *extra])
                    hp = game.player.hp
                    game.handle_command(direction)
                    self.assertEqual(game.scouting_result["success"], success)
                    self.assertEqual(game.enemy_unaware, success)
                    self.assertEqual(game.player.hp, hp)
                    self.assertFalse(game.rng.values)

    def test_safe_rooms_and_defeated_foes_do_not_roll_scouting(self):
        for corpse in (False, True):
            with self.subTest(corpse=corpse):
                game, direction, destination = entry_game(values=[])
                room = game.dungeon.get_room(destination)
                if corpse:
                    room.enemy.hp = 0
                else:
                    room.enemy = None
                game.handle_command(direction)
                self.assertTrue(game.room.visited)
                self.assert_reset(game)
                self.assertEqual(game.rng.calls, [])

    def test_visited_foes_use_normal_initiative_and_the_existing_reactive_save(self):
        for class_id in CLASSES:
            with self.subTest(class_id=class_id):
                game, direction, _ = entry_game(class_id, [2, 20, 12, 2], visited=True)
                output = game.handle_command(direction)
                self.assertIsNone(game.scouting_result)
                self.assertFalse(game.enemy_unaware)
                self.assertFalse(game.opening_hide_available)
                self.assertTrue(game.perception_result["success"])
                self.assertIn("d20 [2]", "\n".join(output))
                self.assertEqual(game.rng.calls,
                                 [(1, 20, 2), (1, 20, 20), (1, 20, 12), (1, 20, 2)])

    def test_retreat_and_reentry_cannot_farm_a_second_scouting_opportunity(self):
        game, direction, destination = entry_game(values=[12, 20, 1])
        entrance = game.position
        game.handle_command(direction)
        game.handle_command("flee")
        self.assertEqual(game.position, entrance)
        self.assert_reset(game)
        game.handle_command(direction)
        self.assertEqual(game.position, destination)
        self.assertIsNone(game.scouting_result)
        self.assertFalse(game.enemy_unaware)
        self.assertFalse(game.opening_hide_available)
        self.assertTrue(game.free_examine_available)
        self.assertEqual(game.rng.calls, [(1, 20, 12), (1, 20, 20), (1, 20, 1)])

    def test_snapshot_detaches_scouting_results_without_mutating_or_rerolling(self):
        game, direction, _ = entry_game(values=[12])
        game.handle_command(direction)
        before = game.get_state()
        changed = game.get_state()
        json.dumps(changed)
        changed["encounter"]["scouting"].clear()
        changed["encounter"]["initiative"].clear()
        changed["encounter"]["enemy_unaware"] = False
        changed["encounter"]["opening_hide_available"] = False
        self.assertEqual(game.get_state(), before)
        self.assertEqual(game.rng.calls, [(1, 20, 12)])

    def test_invalid_and_informational_commands_preserve_the_unnoticed_opening(self):
        game, direction, _ = entry_game(values=[12])
        game.handle_command(direction)
        before = game.get_state()
        for command in ("look", "map", "stats", "skills", "inventory", "help", "journal",
                        "north", "loot", "rest", "ember", "surge", "cast missile", "nonsense"):
            with self.subTest(command=command):
                game.handle_command(command)
                self.assertEqual(game.get_state(), before)
                self.assertEqual(game.elapsed_minutes, 1)
                self.assertEqual(game.rng.calls, [(1, 20, 12)])

    def test_free_examination_preserves_the_rogues_preparatory_hide(self):
        game, direction, _ = entry_game(values=[12, 10])
        game.handle_command(direction)
        game.handle_command("examine")
        self.assertTrue(game.foe_examined)
        self.assertFalse(game.free_examine_available)
        self.assertTrue(game.enemy_unaware)
        self.assertTrue(game.opening_hide_available)
        self.assertEqual(game.actions_remaining, 1)
        self.assertTrue(game.bonus_action_available)
        game.handle_command("hide")
        self.assertTrue(game.hidden)
        self.assertTrue(game.enemy_unaware)
        self.assertEqual(game.actions_remaining, 1)

    def test_valid_bonus_actions_preserve_the_preparatory_hide(self):
        game, direction, _ = entry_game(values=[12, 1, 1, 10])
        game.player.hp = 1
        game.handle_command(direction)
        game.handle_command("potion")
        self.assertFalse(game.bonus_action_available)
        self.assertTrue(game.enemy_unaware)
        self.assertTrue(game.opening_hide_available)
        game.handle_command("hide")
        self.assertTrue(game.hidden)
        self.assertEqual(game.actions_remaining, 1)
        self.assertFalse(game.bonus_action_available)
        self.assertEqual(game.rng.calls,
                         [(1, 20, 12), (1, 4, 1), (1, 4, 1), (1, 20, 10)])

    def test_wizard_shield_preserves_the_unnoticed_opening_until_a_main_spell(self):
        game, direction, _ = entry_game("wizard", [12, 15, 4])
        game.handle_command(direction)
        game.handle_command("cast shield")
        self.assertTrue(game.enemy_unaware)
        self.assertTrue(game.free_examine_available)
        self.assertTrue(game.shield_active)
        self.assertEqual(game.actions_remaining, 1)
        self.assertFalse(game.bonus_action_available)
        self.assertEqual(game.rng.calls, [(1, 20, 12)])
        game.handle_command("cast firebolt")
        self.assertFalse(game.enemy_unaware)
        self.assertTrue(game.shield_active)
        self.assertEqual(game.actions_remaining, 0)
        self.assertEqual(game.enemy.hp, 96)
        self.assertEqual(game.rng.calls, [(1, 20, 12), (1, 20, 15), (1, 10, 4)])

    def test_ending_the_opening_turn_alerts_the_foe_and_allows_its_attack(self):
        game, direction, _ = entry_game(values=[12, 10])
        game.handle_command(direction)
        before = game.get_state()
        self.assertNotIn("damage", "\n".join(game.enemy_turn()).lower())
        self.assertEqual(game.get_state(), before)
        self.assertEqual(game.rng.calls, [(1, 20, 12)])
        output = game.handle_command("end")
        self.assertIn("d20 [10]", "\n".join(output))
        self.assertFalse(game.enemy_unaware)
        self.assertFalse(game.opening_hide_available)
        self.assertFalse(game.free_examine_available)
        self.assertEqual(game.round_number, 2)
        self.assertEqual(game.actions_remaining, 1)
        self.assertAlmostEqual(game.elapsed_minutes, 1.1)

    def test_main_actions_end_the_unnoticed_opportunity_without_an_extra_attack(self):
        for class_id, command, dice in (
                ("rogue", "dodge", []), ("rogue", "ember", [1, 1, 1]),
                ("rogue", "strike", [15, 4]), ("wizard", "attack", [15, 4]),
                ("wizard", "cast missile", [1, 1, 1]), ("wizard", "cast armor", [])):
            with self.subTest(class_id=class_id, command=command):
                game, direction, _ = entry_game(class_id, [12, *dice])
                game.player.ember_stones = 1
                game.handle_command(direction)
                hp = game.player.hp
                game.handle_command(command)
                self.assertFalse(game.enemy_unaware)
                self.assertFalse(game.opening_hide_available)
                self.assertFalse(game.free_examine_available)
                self.assertEqual(game.actions_remaining, 0)
                self.assertEqual(game.player.hp, hp)
                self.assertEqual(game.round_number, 1)
                self.assertFalse(game.rng.values)

    def test_paid_examination_ends_the_unnoticed_opportunity(self):
        game, direction, _ = entry_game(values=[12])
        game.handle_command(direction)
        game.free_examine_available = False
        game.handle_command("examine")
        self.assertTrue(game.foe_examined)
        self.assertEqual(game.actions_remaining, 0)
        self.assertFalse(game.enemy_unaware)
        self.assertFalse(game.opening_hide_available)
        self.assertEqual(game.rng.calls, [(1, 20, 12)])

    def test_floor_transition_clears_scouting_and_opportunities(self):
        game, direction, _ = entry_game(values=[12])
        game.handle_command(direction)
        game.position = game.dungeon.boss_position
        game.room.enemy.hp = 0
        game.floor_cleared = True
        game.handle_command("portal")
        game.rng = random.Random(8)
        game.handle_command("descend")
        self.assertEqual(game.floor, 2)
        self.assert_reset(game)


class PreparatoryHideTests(unittest.TestCase):
    def test_first_hide_is_free_at_every_rogue_level_and_preserves_the_opening(self):
        for level in (1, 2, 5):
            with self.subTest(level=level):
                game, direction, _ = entry_game(values=[12, 10], level=level)
                game.handle_command(direction)
                hp = game.player.hp
                output = game.handle_command("hide")
                self.assertTrue(game.hidden)
                self.assertTrue(game.enemy_unaware)
                self.assertFalse(game.opening_hide_available)
                self.assertTrue(game.free_examine_available)
                self.assertEqual(game.actions_remaining, 1)
                self.assertTrue(game.bonus_action_available)
                self.assertEqual(game.player.hp, hp)
                self.assertEqual(game.round_number, 1)
                self.assertEqual(game.elapsed_minutes, 1)
                self.assertIn("d20 [10]", "\n".join(output))
                self.assertEqual(game.rng.calls, [(1, 20, 12), (1, 20, 10)])
                before = game.get_state()
                game.handle_command("hide")
                self.assertEqual(game.get_state(), before)
                self.assertEqual(len(game.rng.calls), 2)

    def test_preparatory_hide_dc_increases_with_floor_depth(self):
        for floor, die, success, extra in ((1, 6, True, []), (3, 7, False, [20, 1]),
                                          (3, 8, True, []), (5, 10, True, [])):
            with self.subTest(floor=floor, die=die):
                game, direction, _ = entry_game(values=[12, die, *extra])
                game.floor = floor
                game.handle_command(direction)
                output = game.handle_command("hide")
                self.assertEqual(game.hidden, success)
                self.assertEqual(game.enemy_unaware, success)
                self.assertIn(f"DC {12 + floor}", "\n".join(output))
                self.assertFalse(game.rng.values)

    def test_hidden_attack_has_advantage_sneak_damage_and_only_one_action(self):
        game, direction, _ = entry_game(values=[12, 10, 3, 15, 4, 5, 10])
        game.handle_command(direction)
        game.handle_command("hide")
        hp = game.player.hp
        output = game.handle_command("attack")
        self.assertIn("d20 [3/15]", "\n".join(output))
        self.assertIn("Sneak Attack", "\n".join(output))
        self.assertEqual(game.enemy.hp, 88)  # Rapier 4 + Dexterity 3 + Sneak Attack 5.
        self.assertEqual(game.player.hp, hp)
        self.assertTrue(game.sneak_attack_used)
        self.assertFalse(game.hidden)
        self.assertFalse(game.enemy_unaware)
        self.assertFalse(game.opening_hide_available)
        self.assertEqual(game.actions_remaining, 0)
        self.assertTrue(game.bonus_action_available)
        self.assertEqual(game.round_number, 1)
        self.assertEqual(game.rng.calls,
                         [(1, 20, 12), (1, 20, 10), (1, 20, 3), (1, 20, 15),
                          (1, 8, 4), (1, 6, 5)])
        game.handle_command("attack")
        self.assertEqual(game.enemy.hp, 88)
        game.handle_command("end")
        self.assertEqual(game.round_number, 2)
        self.assertFalse(game.sneak_attack_used)
        self.assertFalse(game.rng.values)

    def test_hidden_critical_doubles_weapon_and_sneak_dice_only(self):
        game, direction, _ = entry_game(values=[12, 10, 3, 20, 1, 2, 3, 4])
        game.handle_command(direction)
        game.handle_command("hide")
        output = game.handle_command("attack")
        self.assertEqual(game.enemy.hp, 87)  # 2d8 = 3, Dexterity = 3, 2d6 = 7.
        self.assertIn("Critical hit!", "\n".join(output))
        self.assertIn("Sneak Attack", "\n".join(output))
        self.assertEqual(game.rng.calls,
                         [(1, 20, 12), (1, 20, 10), (1, 20, 3), (1, 20, 20),
                          (1, 8, 1), (1, 8, 2), (1, 6, 3), (1, 6, 4)])

    def test_low_dexterity_opening_critical_clamps_combined_damage_once(self):
        game, direction, _ = entry_game(values=[12, 20, 2, 20, 1, 1, 1, 1])
        game.player.dexterity = 3  # Dexterity -4, expertise +4, so Stealth +0.
        game.handle_command(direction)
        game.handle_command("hide")
        self.assertTrue(game.hidden)
        output = game.handle_command("attack")
        self.assertIn("Critical hit!", "\n".join(output))
        self.assertEqual(game.enemy.hp, 100)  # 2d8 (2) + 2d6 (2) - 4 = zero.
        self.assertTrue(game.sneak_attack_used)
        self.assertFalse(game.enemy_unaware)
        self.assertEqual(game.actions_remaining, 0)
        self.assertEqual(game.rng.calls,
                         [(1, 20, 12), (1, 20, 20), (1, 20, 2), (1, 20, 20),
                          (1, 8, 1), (1, 8, 1), (1, 6, 1), (1, 6, 1)])

    def test_attack_without_hiding_has_no_advantage_or_sneak_damage(self):
        game, direction, _ = entry_game(values=[12, 15, 4])
        game.handle_command(direction)
        output = game.handle_command("attack")
        self.assertEqual(game.enemy.hp, 93)
        self.assertNotIn("Sneak Attack", "\n".join(output))
        self.assertFalse(game.sneak_attack_used)
        self.assertFalse(game.enemy_unaware)
        self.assertFalse(game.opening_hide_available)
        self.assertEqual(game.actions_remaining, 0)
        self.assertEqual(game.rng.calls, [(1, 20, 12), (1, 20, 15), (1, 8, 4)])

    def test_hidden_miss_still_reveals_the_rogue_without_sneak_damage_rolls(self):
        game, direction, _ = entry_game(values=[12, 10, 2, 3])
        game.handle_command(direction)
        game.handle_command("hide")
        game.handle_command("attack")
        self.assertEqual(game.enemy.hp, 100)
        self.assertFalse(game.hidden)
        self.assertFalse(game.enemy_unaware)
        self.assertFalse(game.sneak_attack_used)
        self.assertEqual(game.actions_remaining, 0)
        self.assertEqual(game.rng.calls, [(1, 20, 12), (1, 20, 10), (1, 20, 2), (1, 20, 3)])

    def test_failed_preparatory_hide_rolls_initiative_without_a_second_ambush_save(self):
        for hero_first, extra in ((True, [18, 2]), (False, [2, 20, 19, 2])):
            with self.subTest(hero_first=hero_first):
                game, direction, _ = entry_game(values=[12, 1, *extra])
                game.handle_command(direction)
                hp = game.player.hp
                output = game.handle_command("hide")
                self.assertFalse(game.hidden)
                self.assertFalse(game.enemy_unaware)
                self.assertFalse(game.opening_hide_available)
                self.assertTrue(game.scouting_result["success"])
                self.assertEqual(game.initiative_result["hero_first"], hero_first)
                self.assertEqual(game.free_examine_available, hero_first)
                self.assertFalse(game.ambush_advantage)
                self.assertIsNone(game.perception_result)
                self.assertEqual(game.actions_remaining, 1)
                self.assertTrue(game.bonus_action_available)
                self.assertEqual(game.round_number, 1)
                self.assertEqual(game.player.hp, hp if hero_first else hp - 3)
                self.assertIn("Initiative", "\n".join(output))
                self.assertEqual(game.rng.calls[:2], [(1, 20, 12), (1, 20, 1)])
                self.assertEqual(len(game.rng.calls), 4 if hero_first else 6)
                self.assertFalse(game.rng.values)

    def test_another_hide_after_failure_pays_normal_level_dependent_cost(self):
        for level in (1, 2):
            with self.subTest(level=level):
                game, direction, _ = entry_game(values=[12, 1, 18, 2, 10], level=level)
                game.handle_command(direction)
                game.handle_command("hide")
                self.assertFalse(game.opening_hide_available)
                game.handle_command("hide")
                self.assertTrue(game.hidden)
                self.assertFalse(game.enemy_unaware)
                self.assertEqual(game.actions_remaining, 0 if level == 1 else 1)
                self.assertEqual(game.bonus_action_available, level == 1)
                self.assertFalse(game.rng.values)

    def test_failed_hide_with_hero_initiative_does_not_refund_a_used_bonus_action(self):
        game, direction, _ = entry_game(values=[12, 1, 1, 1, 20, 1, 1, 1])
        game.player.hp = 1
        game.handle_command(direction)
        game.handle_command("potion")
        self.assertEqual(game.player.hp, 5)
        self.assertEqual(game.player.potions, 2)
        self.assertFalse(game.bonus_action_available)
        game.handle_command("hide")
        self.assertTrue(game.initiative_result["hero_first"])
        self.assertFalse(game.enemy_unaware)
        self.assertEqual(game.actions_remaining, 1)
        self.assertFalse(game.bonus_action_available)
        self.assertEqual(game.player.hp, 5)
        before = game.get_state()
        calls = list(game.rng.calls)
        game.handle_command("potion")
        self.assertEqual(game.get_state(), before)
        self.assertEqual(game.rng.calls, calls)
        self.assertEqual(game.rng.calls,
                         [(1, 20, 12), (1, 4, 1), (1, 4, 1), (1, 20, 1),
                          (1, 20, 20), (1, 20, 1)])
        self.assertEqual(list(game.rng.values), [1, 1])

    def test_failed_hide_with_enemy_initiative_refreshes_bonus_after_foe_acts(self):
        game, direction, _ = entry_game(values=[12, 1, 1, 1, 2, 20, 19, 2, 1, 1])
        game.player.hp = 1
        game.handle_command(direction)
        game.handle_command("potion")
        self.assertEqual(game.player.hp, 5)
        game.handle_command("hide")
        self.assertFalse(game.initiative_result["hero_first"])
        self.assertEqual(game.player.hp, 2)  # The foe deals 3 before a new hero turn.
        self.assertTrue(game.bonus_action_available)
        self.assertEqual(game.actions_remaining, 1)
        game.handle_command("potion")
        self.assertEqual(game.player.hp, 6)
        self.assertEqual(game.player.potions, 1)
        self.assertFalse(game.bonus_action_available)
        self.assertEqual(game.rng.calls,
                         [(1, 20, 12), (1, 4, 1), (1, 4, 1), (1, 20, 1),
                          (1, 20, 2), (1, 20, 20), (1, 20, 19), (1, 6, 2),
                          (1, 4, 1), (1, 4, 1)])
        self.assertFalse(game.rng.values)

    def test_preparatory_hide_structured_action_matches_command(self):
        reference, direction, _ = entry_game(values=[12, 10])
        reference.handle_command(direction)
        expected = reference.handle_command("hide")
        game, direction, _ = entry_game(values=[12, 10])
        game.handle_command(direction)
        self.assertEqual(game.perform(Action("hide")), expected)
        self.assertEqual(game.get_state(), reference.get_state())

    def test_opening_kill_clears_scouting_and_awards_rewards_only_once(self):
        game, direction, _ = entry_game(values=[12, 10, 3, 15, 4, 5])
        game.handle_command(direction)
        enemy = game.enemy
        enemy.hp = 1
        game.handle_command("hide")
        game.handle_command("attack")
        self.assertIsNone(game.enemy)
        self.assertEqual((game.player.xp, game.player.gold), (50, 7))
        self.assertIsNone(game.scouting_result)
        self.assertFalse(game.enemy_unaware)
        self.assertFalse(game.opening_hide_available)
        before = game.get_state()
        game.handle_command("attack")
        game.handle_command("end")
        self.assertEqual(game.get_state(), before)
        self.assertFalse(game.rng.values)

    def test_failed_hide_can_be_lethal_before_any_hero_action(self):
        game, direction, _ = entry_game(values=[12, 1, 2, 20, 19, 2])
        game.player.hp = 3
        game.handle_command(direction)
        output = game.handle_command("hide")
        self.assertTrue(game.player.dead)
        self.assertTrue(game.over)
        self.assertEqual(game.player.hp, 0)
        self.assertFalse(game.enemy_unaware)
        self.assertFalse(game.opening_hide_available)
        self.assertEqual(game.round_number, 0)
        self.assertIn("You die", "\n".join(output))
        self.assertNotIn("Actions left", "\n".join(output))
        self.assertEqual(game.rng.calls,
                         [(1, 20, 12), (1, 20, 1), (1, 20, 2), (1, 20, 20),
                          (1, 20, 19), (1, 6, 2)])


if __name__ == "__main__":
    unittest.main()
