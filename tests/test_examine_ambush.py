"""Encounter inspection and initiative-based ambush behavior through the engine."""

from collections import deque
import json
import random
import unittest
from unittest.mock import PropertyMock, patch

from actions import Action
from game import Game
from player import Player
from room import Enemy


class EncounterRandom:
    """Fail on extra rolls, and record the dice needed by an encounter."""

    def __init__(self, values=()):
        self.values = deque(values)
        self.calls = []

    def randint(self, low, high):
        if not self.values:
            raise AssertionError(f"Unexpected random roll: {low}..{high}")
        value = self.values.popleft()
        if not low <= value <= high:
            raise AssertionError((low, high, value))
        self.calls.append((low, high, value))
        return value


def encounter_game(values=()):
    game = Game(seed=7)
    game.room.enemy = Enemy("Runebound sentry", 100, 100, 12, 3, (1, 6), 1, 50, 7)
    game.rng = EncounterRandom(values)
    return game


class ExamineTests(unittest.TestCase):
    def assert_cleared_encounter(self, game):
        self.assertFalse(game.free_examine_available)
        self.assertFalse(game.foe_examined)
        self.assertFalse(game.ambush_advantage)
        self.assertIsNone(game.initiative_result)
        self.assertIsNone(game.perception_result)
        self.assertIsNone(game.get_state()["encounter"]["foe_details"])

    def test_winning_initiative_offers_examination_without_extra_rolls_or_cost(self):
        game = encounter_game([18, 2])
        output = game.begin_encounter()
        self.assertTrue(game.free_examine_available)
        self.assertIsNone(game.perception_result)
        self.assertEqual(game.rng.calls, [(1, 20, 18), (1, 20, 2)])
        self.assertIn("examine", "\n".join(output).lower())
        original = (game.actions_remaining, game.bonus_action_available,
                    game.elapsed_minutes, game.round_number, list(game.rng.calls))
        output = game.handle_command("examine")
        self.assertEqual((game.actions_remaining, game.bonus_action_available,
                          game.elapsed_minutes, game.round_number, game.rng.calls), original)
        self.assertTrue(game.foe_examined)
        self.assertFalse(game.free_examine_available)
        text = "\n".join(output)
        self.assertIn("Runebound sentry", text)
        self.assertIn("100", text)
        self.assertIn("12", text)
        self.assertIsNotNone(game.get_state()["encounter"]["foe_details"])

    def test_tied_initiative_gives_the_adventurer_a_free_examination(self):
        game = encounter_game([10, 12])
        game.begin_encounter()
        self.assertTrue(game.free_examine_available)
        self.assertIsNone(game.perception_result)
        self.assertEqual(game.player.hp, 12)
        self.assertEqual(len(game.rng.calls), 2)

    def test_room_entry_rolls_initiative_and_then_offers_examination(self):
        game = Game(seed=7)
        direction, destination = next(iter(game.room.exits.items()))
        game.dungeon.get_room(destination).enemy = Enemy(
            "Door sentry", 100, 100, 12, 3, (1, 6), 1, 50, 7)
        game.rng = EncounterRandom([18, 2])
        output = game.handle_command(direction)
        self.assertEqual(game.position, destination)
        self.assertEqual(game.elapsed_minutes, 1)
        self.assertTrue(game.free_examine_available)
        self.assertIn("Initiative", "\n".join(output))
        self.assertIn("examine", "\n".join(output).lower())

    def test_examination_after_losing_initiative_spends_only_one_action(self):
        game = encounter_game([2, 20, 12, 10])
        game.begin_encounter()
        self.assertFalse(game.free_examine_available)
        original = (game.bonus_action_available, game.elapsed_minutes,
                    game.round_number, list(game.rng.calls), game.player.hp, game.enemy.hp)
        game.handle_command("examine")
        self.assertTrue(game.foe_examined)
        self.assertEqual(game.actions_remaining, 0)
        self.assertEqual((game.bonus_action_available, game.elapsed_minutes,
                          game.round_number, game.rng.calls, game.player.hp, game.enemy.hp), original)

    def test_examined_foe_can_be_reread_with_no_action_remaining(self):
        game = encounter_game([2, 20, 12, 10])
        game.begin_encounter()
        first = game.handle_command("examine")
        state, calls, clock = game.get_state(), list(game.rng.calls), game.elapsed_minutes
        repeated = game.handle_command("examine")
        # The cost message changes; the acquired observations stay available.
        self.assertEqual(repeated[1:], first[1:])
        self.assertEqual(game.get_state(), state)
        self.assertEqual(game.rng.calls, calls)
        self.assertEqual(game.elapsed_minutes, clock)

    def test_first_successful_action_expires_free_examination(self):
        for command, rolls in (("attack", [2]), ("dodge", []), ("ember", [1, 1, 1])):
            with self.subTest(command=command):
                game = encounter_game([18, 2, *rolls])
                game.player.ember_stones = 1
                game.begin_encounter()
                game.handle_command(command)
                self.assertFalse(game.free_examine_available)
                self.assertEqual(game.actions_remaining, 0)
                calls = list(game.rng.calls)
                game.handle_command("examine")
                self.assertFalse(game.foe_examined)
                self.assertEqual(game.actions_remaining, 0)
                self.assertEqual(game.rng.calls, calls)

    def test_ending_first_turn_expires_free_examination(self):
        game = encounter_game([18, 2, 10])
        game.begin_encounter()
        game.handle_command("end")
        self.assertFalse(game.free_examine_available)
        self.assertEqual(game.round_number, 2)
        game.handle_command("examine")
        self.assertTrue(game.foe_examined)
        self.assertEqual(game.actions_remaining, 0)

    def test_invalid_and_informational_commands_preserve_the_free_opportunity(self):
        game = encounter_game([18, 2])
        game.begin_encounter()
        for command in ("look", "stats", "help", "inventory", "north", "loot",
                        "rest", "ember", "surge", "nonsense"):
            with self.subTest(command=command):
                game.handle_command(command)
                self.assertTrue(game.free_examine_available)
                self.assertEqual(game.actions_remaining, 1)
                self.assertTrue(game.bonus_action_available)
                self.assertEqual(len(game.rng.calls), 2)

    def test_bonus_action_does_not_expire_free_examination(self):
        game = encounter_game([18, 2, 1])
        game.player.hp = 8
        game.begin_encounter()
        game.handle_command("wind")
        self.assertFalse(game.bonus_action_available)
        self.assertTrue(game.free_examine_available)
        game.handle_command("examine")
        self.assertTrue(game.foe_examined)
        self.assertEqual(game.actions_remaining, 1)
        self.assertFalse(game.bonus_action_available)
        self.assertEqual(game.player.hp, 10)

    def test_action_surge_preserves_free_opportunity_and_added_action(self):
        game = encounter_game([18, 2])
        game.player.gain_xp(300)
        game.begin_encounter()
        game.handle_command("surge")
        self.assertEqual(game.actions_remaining, 2)
        self.assertTrue(game.free_examine_available)
        game.handle_command("examine")
        self.assertEqual(game.actions_remaining, 2)
        self.assertTrue(game.foe_examined)

    def test_action_surge_after_an_attack_does_not_restore_the_free_opportunity(self):
        game = encounter_game([18, 2, 2])
        game.player.gain_xp(300)
        game.begin_encounter()
        game.handle_command("attack")
        game.handle_command("surge")
        self.assertEqual(game.actions_remaining, 1)
        self.assertFalse(game.free_examine_available)
        game.handle_command("examine")
        self.assertTrue(game.foe_examined)
        self.assertEqual(game.actions_remaining, 0)

    def test_aliases_and_structured_action_match_the_terminal_command(self):
        reference = encounter_game([18, 2])
        reference.begin_encounter()
        expected = reference.handle_command("examine")
        for command in ("examine foe", "inspect"):
            with self.subTest(command=command):
                game = encounter_game([18, 2])
                game.begin_encounter()
                self.assertEqual(game.handle_command(command), expected)
                self.assertEqual(game.get_state(), reference.get_state())
        game = encounter_game([18, 2])
        game.begin_encounter()
        self.assertEqual(game.perform(Action("examine")), expected)
        self.assertEqual(game.get_state(), reference.get_state())

    def test_no_enemy_shop_and_unconscious_examination_do_not_spend_resources(self):
        for scene in ("no enemy", "shop", "unconscious"):
            with self.subTest(scene=scene):
                game = Game(seed=7) if scene == "no enemy" else encounter_game([18, 2])
                if scene != "no enemy":
                    game.begin_encounter()
                if scene == "shop":
                    game.in_shop = True
                elif scene == "unconscious":
                    game.player.hp = 0
                if scene == "no enemy":
                    game.rng = EncounterRandom()
                state, clock, calls = game.get_state(), game.elapsed_minutes, list(game.rng.calls)
                game.handle_command("examine")
                self.assertEqual(game.get_state(), state)
                self.assertEqual(game.elapsed_minutes, clock)
                self.assertEqual(game.rng.calls, calls)

    def test_defeat_clears_examination_and_encounter_rolls(self):
        game = encounter_game([18, 2, 15, 1])
        game.begin_encounter()
        game.handle_command("examine")
        game.enemy.hp = 1
        game.handle_command("attack")
        self.assertIsNone(game.enemy)
        self.assertEqual(game.player.xp, 50)
        self.assertEqual(game.player.gold, 7)
        self.assert_cleared_encounter(game)

    def test_disengage_clears_encounter_and_reentry_requires_a_new_examination(self):
        game = encounter_game([18, 2, 18, 2])
        game.begin_encounter()
        game.handle_command("examine")
        old_position = game.position
        retreat = next(iter(game.room.exits.values()))
        game.dungeon.get_room(retreat).enemy = None
        game.previous_position = retreat
        game.handle_command("flee")
        self.assertEqual(game.position, retreat)
        self.assert_cleared_encounter(game)
        direction = next(direction for direction, target in game.room.exits.items()
                         if target == old_position)
        game.handle_command(direction)
        self.assertTrue(game.free_examine_available)
        self.assertFalse(game.foe_examined)
        self.assertIsNone(game.get_state()["encounter"]["foe_details"])

    def test_new_encounter_does_not_inherit_knowledge_of_a_different_foe(self):
        game = encounter_game([18, 2, 18, 2])
        game.begin_encounter()
        game.handle_command("examine")
        game.room.enemy = Enemy("Another sentry", 200, 200, 14, 4, (1, 8), 2, 100, 10)
        game.begin_encounter()
        self.assertFalse(game.foe_examined)
        self.assertTrue(game.free_examine_available)
        self.assertIsNone(game.get_state()["encounter"]["foe_details"])

    def test_floor_descent_clears_old_encounter_information(self):
        game = encounter_game([18, 2])
        game.begin_encounter()
        game.handle_command("examine")
        game.position = game.dungeon.boss_position
        game.room.enemy.hp = 0
        game.floor_cleared = True
        game.handle_command("portal")
        game.rng = random.Random(8)
        game.handle_command("descend")
        self.assertEqual(game.floor, 2)
        self.assert_cleared_encounter(game)

    def test_encounter_snapshot_is_detached_and_examination_details_start_hidden(self):
        game = encounter_game([18, 2])
        game.begin_encounter()
        before = game.get_state()["encounter"]
        self.assertIsNone(before["foe_details"])
        self.assertTrue(before["free_examine_available"])
        self.assertFalse(before["foe_examined"])
        before["initiative"].clear()
        self.assertTrue(game.initiative_result)
        game.handle_command("examine")
        state = game.get_state()
        json.dumps(state)
        state["encounter"]["foe_details"].clear()
        self.assertTrue(game.get_state()["encounter"]["foe_details"])
        self.assertEqual(len(game.rng.calls), 2)


class AmbushTests(unittest.TestCase):
    def test_losing_initiative_rolls_perception_before_an_advantaged_first_strike(self):
        game = Game(seed=7)
        direction, destination = next(iter(game.room.exits.items()))
        game.dungeon.get_room(destination).enemy = Enemy(
            "Door sentry", 100, 100, 12, 3, (1, 6), 1, 50, 7)
        game.rng = EncounterRandom([2, 20, 1, 2, 15, 3, 10])
        output = game.handle_command(direction)
        text = "\n".join(output)
        self.assertIn("Perception", text)
        self.assertIn("12", text)
        self.assertIn("d20 [2/15]", text)
        self.assertEqual(game.player.hp, 8)
        self.assertEqual(game.elapsed_minutes, 1)
        self.assertEqual(game.actions_remaining, 1)
        self.assertTrue(game.bonus_action_available)
        self.assertFalse(game.free_examine_available)
        self.assertFalse(game.ambush_advantage)
        game.handle_command("end")
        self.assertEqual(game.player.hp, 8)
        self.assertEqual(game.rng.calls[-1], (1, 20, 10))
        self.assertFalse(game.rng.values)

    def test_perception_dc_boundary_controls_only_first_attack_advantage(self):
        for perception, attack_rolls, expected_hp, expected_calls in (
                (10, [2, 15, 3], 8, 6),  # 10 + Wisdom 1 falls below DC 12.
                (11, [2], 12, 4)):       # Meeting DC 12 succeeds.
            with self.subTest(perception=perception):
                game = encounter_game([2, 20, perception, *attack_rolls])
                game.begin_encounter()
                self.assertEqual(game.player.hp, expected_hp)
                self.assertEqual(len(game.rng.calls), expected_calls)
                self.assertFalse(game.free_examine_available)
                self.assertFalse(game.ambush_advantage)
                self.assertIsNotNone(game.perception_result)

    def test_perception_bonus_uses_current_wisdom_without_proficiency(self):
        game = encounter_game([2, 20, 9, 2])
        game.player.wisdom = 16
        game.player.gain_xp(6500)
        self.assertEqual(game.player.perception_bonus, 3)
        game.begin_encounter()
        self.assertEqual(len(game.rng.calls), 4)  # 9 + 3 meets DC; single attack die.
        game.player.wisdom = 8
        self.assertEqual(game.player.perception_bonus, -1)

    def test_perception_natural_one_and_twenty_are_resolved_by_total(self):
        for bonus, die, attack_rolls, expected_hp in ((11, 1, [2], 12),
                                                    (-10, 20, [2, 15, 3], 8)):
            with self.subTest(die=die):
                with patch.object(Player, "perception_bonus", new_callable=PropertyMock) as modifier:
                    modifier.return_value = bonus
                    game = encounter_game([2, 20, die, *attack_rolls])
                    game.begin_encounter()
                    self.assertEqual(game.player.hp, expected_hp)
                    self.assertFalse(game.rng.values)

    def test_ambush_advantage_is_consumed_by_exactly_one_enemy_attack(self):
        game = encounter_game([18, 2, 2, 15, 3, 10])
        game.begin_encounter()
        game.ambush_advantage = True
        first = game.enemy_turn()
        self.assertIn("d20 [2/15]", "\n".join(first))
        self.assertFalse(game.ambush_advantage)
        second = game.enemy_turn()
        self.assertIn("d20 [10]", "\n".join(second))
        self.assertEqual(game.player.hp, 8)
        self.assertFalse(game.rng.values)

    def test_sap_and_dodge_cancel_ambush_advantage_without_extra_dice(self):
        for defense in ("enemy_sapped", "dodging"):
            with self.subTest(defense=defense):
                game = encounter_game([18, 2, 15, 3, 2])
                game.begin_encounter()
                game.ambush_advantage = True
                setattr(game, defense, True)
                first = game.enemy_turn()
                self.assertIn("d20 [15]", "\n".join(first))
                self.assertFalse(game.ambush_advantage)
                self.assertEqual(game.player.hp, 8)
                game.dodging = False
                second = game.enemy_turn()
                self.assertIn("d20 [2]", "\n".join(second))
                self.assertFalse(game.rng.values)

    def test_discarded_natural_one_does_not_fumble_the_ambushing_enemy(self):
        game = encounter_game([2, 20, 1, 1, 15, 2])
        output = game.begin_encounter()
        self.assertIn("d20 [1/15]", "\n".join(output))
        self.assertEqual(game.player.hp, 9)
        self.assertEqual(game.enemy.hp, 100)
        self.assertFalse(game.ambush_advantage)

    def test_two_natural_ones_fumble_even_when_the_monster_has_advantage(self):
        game = encounter_game([2, 20, 1, 1, 1])
        game.begin_encounter()
        self.assertEqual(game.player.hp, 12)
        self.assertEqual(game.enemy.hp, 99)
        self.assertFalse(game.ambush_advantage)
        self.assertFalse(game.rng.values)

    def test_advantaged_near_miss_does_not_damage_either_combatant(self):
        game = encounter_game([2, 20, 1, 15, 16])
        game.enemy.attack_bonus = 1
        output = game.begin_encounter()
        self.assertIn("total 17", "\n".join(output))
        self.assertIn("misses", "\n".join(output))
        self.assertEqual(game.player.hp, 12)
        self.assertEqual(game.enemy.hp, 100)
        self.assertFalse(game.ambush_advantage)

    def test_an_ambush_fumble_that_defeats_the_enemy_clears_flags_and_rewards_once(self):
        game = encounter_game([2, 20, 1, 1, 1])
        game.enemy.hp = 1
        game.begin_encounter()
        self.assertIsNone(game.enemy)
        self.assertEqual(game.player.xp, 50)
        self.assertEqual(game.player.gold, 7)
        self.assertFalse(game.ambush_advantage)
        self.assertFalse(game.free_examine_available)
        self.assertFalse(game.foe_examined)
        self.assertIsNone(game.get_state()["encounter"]["foe_details"])
        game.handle_command("end")
        self.assertEqual(game.player.xp, 50)
        self.assertEqual(game.player.gold, 7)

    def test_ambush_and_unconscious_advantage_do_not_stack_extra_d20s(self):
        game = encounter_game([18, 2, 2, 15, 1, 1])
        game.begin_encounter()
        game.player.hp = 0
        game.ambush_advantage = True
        output = game.enemy_turn()
        self.assertIn("d20 [2/15]", "\n".join(output))
        self.assertIn("Critical hit", "\n".join(output))
        self.assertEqual(game.player.death_save_failures, 2)
        self.assertFalse(game.ambush_advantage)
        self.assertFalse(game.rng.values)

    def test_perception_snapshot_is_detached_and_does_not_reroll_the_check(self):
        game = encounter_game([2, 20, 11, 2])
        game.begin_encounter()
        state = game.get_state()
        json.dumps(state)
        state["encounter"]["perception"].clear()
        self.assertTrue(game.perception_result)
        self.assertEqual(len(game.rng.calls), 4)
        self.assertFalse(game.rng.values)


if __name__ == "__main__":
    unittest.main()
