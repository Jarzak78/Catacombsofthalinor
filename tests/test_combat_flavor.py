"""Near misses and critical fumbles through dice, actions, and instant death."""

import random
import unittest
from unittest.mock import patch

from combat import roll_attack
from game import Game
from tests.test_combat import ScriptedRandom
from tests.test_game import combat_game


def scripted_game(*values):
    game = combat_game()
    game.rng = ScriptedRandom(*values)
    return game


class AttackFlavorTests(unittest.TestCase):
    def test_near_miss_uses_final_total_one_or_two_below_target_ac(self):
        for natural, near_miss in ((12, False), (13, True), (14, True)):
            with self.subTest(natural=natural):
                rng = ScriptedRandom(natural)
                result = roll_attack(rng, 5, 20, (1, 8), 3)
                self.assertEqual(result.armor_class, 20)
                self.assertEqual(result.near_miss, near_miss)
                self.assertFalse(result.critical_fail)
                self.assertFalse(result.hit)
                self.assertEqual(result.damage, 0)
                self.assertEqual(result.fumble_damage, 0)
                self.assertEqual(rng.calls, [(1, 20)])

    def test_equal_ac_is_a_hit_without_near_miss_flavor(self):
        result = roll_attack(ScriptedRandom(15, 4), 5, 20, (1, 8), 3)
        self.assertTrue(result.hit)
        self.assertFalse(result.near_miss)
        self.assertFalse(result.critical_fail)
        self.assertEqual(result.damage, 7)
        text = Game.attack_text("You", "guardian", result)
        self.assertNotIn("Near miss", text)
        self.assertNotIn("Critical fail", text)

    def test_natural_one_is_fumble_even_if_total_is_near_ac_or_above_it(self):
        for bonus in (17, 99):
            with self.subTest(bonus=bonus):
                rng = ScriptedRandom(1)
                result = roll_attack(rng, bonus, 20, (1, 8), 3)
                self.assertTrue(result.critical_fail)
                self.assertFalse(result.near_miss)
                self.assertFalse(result.hit)
                self.assertFalse(result.critical)
                self.assertEqual(result.damage, 0)
                self.assertEqual(result.fumble_damage, 1)
                self.assertEqual(rng.calls, [(1, 20)])

    def test_natural_twenty_is_critical_hit_even_when_total_below_ac(self):
        result = roll_attack(ScriptedRandom(20, 1, 1), -2, 20, (1, 8), 3)
        self.assertTrue(result.hit)
        self.assertTrue(result.critical)
        self.assertFalse(result.near_miss)
        self.assertFalse(result.critical_fail)
        self.assertEqual(result.fumble_damage, 0)

    def test_advantage_discards_natural_one_without_fumble(self):
        result = roll_attack(ScriptedRandom(1, 15, 4), 5, 20, (1, 8), 3,
                             advantage=True)
        self.assertEqual(result.roll, 15)
        self.assertTrue(result.hit)
        self.assertFalse(result.critical_fail)
        self.assertEqual(result.fumble_damage, 0)

    def test_disadvantage_selected_one_fumbles_despite_other_natural_twenty(self):
        rng = ScriptedRandom(20, 1)
        result = roll_attack(rng, 5, 20, (1, 8), 3, disadvantage=True,
                             critical_on_hit=True)
        self.assertEqual(result.roll, 1)
        self.assertTrue(result.critical_fail)
        self.assertFalse(result.critical)
        self.assertEqual(result.fumble_damage, 1)
        self.assertEqual(rng.calls, [(1, 20), (1, 20)])

    def test_advantage_two_ones_and_cancelled_advantage_still_fumble(self):
        for values, advantage, disadvantage in (((1, 1), True, False),
                                                 ((1,), True, True)):
            with self.subTest(values=values):
                rng = ScriptedRandom(*values)
                result = roll_attack(rng, 5, 20, (1, 8), 3,
                                     advantage=advantage, disadvantage=disadvantage)
                self.assertTrue(result.critical_fail)
                self.assertEqual(result.fumble_damage, 1)
                self.assertEqual(rng.calls, [(1, 20)] * len(values))

    def test_near_miss_and_fumble_narration_for_both_combatants(self):
        near_miss = roll_attack(ScriptedRandom(13), 5, 20, (1, 8), 3)
        fumble = roll_attack(ScriptedRandom(1), 5, 20, (1, 8), 3)
        for attacker, defender in (("You", "guardian"), ("guardian", "you")):
            with self.subTest(attacker=attacker):
                text = Game.attack_text(attacker, defender, near_miss)
                self.assertIn("Near miss", text)
                self.assertIn("no damage", text.lower())
                self.assertIn("total 18", text)
                text = Game.attack_text(attacker, defender, fumble)
                self.assertIn("Critical fail!", text)
                self.assertIn("1 HP of self-damage", text)


class CombatFumbleTests(unittest.TestCase):
    def test_player_near_miss_spends_action_without_damage_or_sap(self):
        game = scripted_game(13)
        game.enemy.armor_class = 20
        output = game.handle_command("attack")
        self.assertIn("Near miss", "\n".join(output))
        self.assertEqual(game.enemy.hp, 100)
        self.assertEqual(game.player.hp, 12)
        self.assertFalse(game.enemy_sapped)
        self.assertEqual(game.actions_remaining, 0)
        self.assertTrue(game.bonus_action_available)
        self.assertEqual(game.rng.calls, [(1, 20)])

    def test_enemy_near_miss_does_not_damage_either_combatant(self):
        game = scripted_game(15)
        game.player.armor_bonus = 2
        output = game.handle_command("end")
        self.assertIn("Near miss", "\n".join(output))
        self.assertEqual(game.player.hp, 12)
        self.assertEqual(game.enemy.hp, 100)
        self.assertEqual(game.round_number, 2)
        self.assertEqual(game.rng.calls, [(1, 20)])

    def test_player_fumble_uses_damage_model_and_only_hurts_attacker(self):
        game = scripted_game(1)
        with patch.object(game.player, "take_damage", wraps=game.player.take_damage) as damage:
            output = game.handle_command("attack")
        self.assertIn("Critical fail!", "\n".join(output))
        self.assertEqual(game.player.hp, 11)
        self.assertEqual(game.enemy.hp, 100)
        self.assertFalse(game.enemy_sapped)
        self.assertEqual(game.actions_remaining, 0)
        self.assertEqual(damage.call_count, 1)
        self.assertEqual(damage.call_args.args[0], 1)
        self.assertFalse(damage.call_args.kwargs.get("critical", False))
        self.assertEqual(game.rng.calls, [(1, 20)])

    def test_enemy_fumble_uses_damage_model_and_only_hurts_attacker(self):
        game = scripted_game(1)
        enemy = game.enemy
        with patch.object(enemy, "take_damage", wraps=enemy.take_damage) as damage:
            output = game.handle_command("end")
        self.assertIn("Critical fail!", "\n".join(output))
        self.assertEqual(enemy.hp, 99)
        self.assertEqual(game.player.hp, 12)
        self.assertEqual(game.player.xp, 0)
        damage.assert_called_once_with(1)
        self.assertEqual(game.rng.calls, [(1, 20)])

    def test_lethal_fumble_stops_extra_attack_and_ends_adventure(self):
        game = scripted_game(1)
        game.player.gain_xp(6500)
        game.player.hp = 1
        output = game.handle_command("attack")
        self.assertEqual(game.player.hp, 0)
        self.assertFalse(game.player.is_conscious)
        self.assertTrue(game.player.dead)
        self.assertTrue(game.over)
        self.assertIn("You die", "\n".join(output))
        self.assertEqual(game.enemy.hp, 100)
        self.assertEqual(game.actions_remaining, 0)
        self.assertNotIn("Extra Attack", "\n".join(output))
        self.assertEqual(game.rng.calls, [(1, 20)])

    def test_second_extra_attack_can_fumble_without_undoing_first_hit(self):
        game = scripted_game(15, 4, 1)
        game.player.gain_xp(6500)
        game.player.hp = 1
        output = game.handle_command("attack")
        self.assertIn("Extra Attack", "\n".join(output))
        self.assertIn("Critical fail!", "\n".join(output))
        self.assertEqual(game.player.hp, 0)
        self.assertTrue(game.player.dead)
        self.assertTrue(game.over)
        self.assertIn("You die", "\n".join(output))
        self.assertEqual(game.enemy.hp, 91)
        self.assertTrue(game.enemy_sapped)
        self.assertEqual(game.actions_remaining, 0)
        self.assertEqual(game.rng.calls, [(1, 20), (1, 8), (1, 20)])

    def test_conscious_player_can_finish_extra_attack_after_first_strike_fumbles(self):
        game = scripted_game(1, 15, 4)
        game.player.gain_xp(6500)
        hp = game.player.hp
        output = game.handle_command("attack")
        self.assertIn("Extra Attack", "\n".join(output))
        self.assertEqual(game.player.hp, hp - 1)
        self.assertEqual(game.enemy.hp, 91)
        self.assertEqual(game.actions_remaining, 0)
        self.assertEqual(game.rng.calls, [(1, 20), (1, 20), (1, 8)])

    def test_sapped_enemy_fumbles_on_selected_one_instead_of_other_natural_twenty(self):
        game = scripted_game(20, 1)
        game.enemy_sapped = True
        output = game.handle_command("end")
        self.assertIn("Critical fail!", "\n".join(output))
        self.assertEqual(game.player.hp, 12)
        self.assertEqual(game.enemy.hp, 99)
        self.assertFalse(game.enemy_sapped)
        self.assertEqual(game.rng.calls, [(1, 20)] * 2)

    def test_enemy_self_kill_awards_rewards_once_and_ends_combat(self):
        game = scripted_game(1)
        enemy = game.enemy
        enemy.hp = 1
        enemy.gold_reward = 17
        output = game.handle_command("end")
        self.assertEqual(enemy.hp, 0)
        self.assertIsNone(game.enemy)
        self.assertEqual(game.player.xp, 50)
        self.assertEqual(game.player.gold, 17)
        self.assertEqual(game.player.hp, 12)
        self.assertEqual(game.round_number, 1)
        self.assertIn("You defeat", "\n".join(output))
        game.handle_command("end")
        game.handle_command("attack")
        self.assertEqual(game.player.xp, 50)
        self.assertEqual(game.player.gold, 17)
        self.assertEqual(game.rng.calls, [(1, 20)])

    def test_guardian_self_kill_opens_portal_and_preserves_campaign_transition(self):
        game = Game(seed=7)
        game.position = game.dungeon.boss_position
        guardian = game.enemy
        guardian.hp = 1
        game.rng = ScriptedRandom(1)
        output = game.handle_command("end")
        self.assertTrue(game.floor_cleared)
        self.assertIsNone(game.enemy)
        self.assertIn("portal opens", "\n".join(output).lower())
        self.assertEqual(game.player.xp, guardian.xp_reward)
        self.assertEqual(game.player.gold, guardian.gold_reward)
        game.handle_command("portal")
        self.assertTrue(game.in_shop)
        # Descent generates the next floor with the usual campaign RNG.
        game.rng = random.Random(7)
        game.handle_command("descend")
        self.assertEqual(game.floor, 2)
        self.assertFalse(game.floor_cleared)
        self.assertFalse(game.in_shop)

    def test_enemy_self_kill_before_first_player_turn_does_not_start_combat(self):
        game = scripted_game(2, 20, 12, 1)
        game.enemy.hp = 1
        output = game.begin_encounter()
        self.assertIsNone(game.enemy)
        self.assertEqual(game.player.xp, 50)
        self.assertEqual(game.round_number, 0)
        self.assertNotIn("Actions left", "\n".join(output))
        self.assertEqual(game.rng.calls, [(1, 20)] * 4)

    def test_dead_player_cannot_wait_for_enemy_self_kill_or_gain_rewards(self):
        game = scripted_game()
        game.enemy.hp = 1
        game.player.take_damage(game.player.hp)
        before = game.get_state()
        output = game.handle_command("end")
        self.assertIsNotNone(game.enemy)
        self.assertEqual(game.enemy.hp, 1)
        self.assertEqual(game.player.hp, 0)
        self.assertTrue(game.player.dead)
        self.assertTrue(game.over)
        self.assertIn("over", "\n".join(output).lower())
        self.assertEqual(game.get_state(), before)
        self.assertEqual((game.player.xp, game.player.gold), (0, 0))
        self.assertEqual(game.rng.calls, [])

    def test_death_in_a_safe_room_cannot_recover_by_ending_turn(self):
        game = scripted_game()
        game.room.enemy = None
        game.player.take_damage(game.player.hp)
        before = game.get_state()
        for _ in range(4):
            game.handle_command("end")
            self.assertEqual(game.get_state(), before)
        self.assertTrue(game.over)
        self.assertEqual(game.rng.calls, [])

    def test_enemy_turn_after_death_does_not_roll_or_award_rewards(self):
        game = scripted_game()
        game.enemy.hp = 1
        game.player.take_damage(game.player.hp)
        before = game.get_state()
        self.assertEqual(game.enemy_turn(), [])
        self.assertEqual(game.get_state(), before)
        self.assertEqual((game.player.xp, game.player.gold), (0, 0))
        self.assertEqual(game.rng.calls, [])


if __name__ == "__main__":
    unittest.main()
