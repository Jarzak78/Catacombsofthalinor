"""Successful-hit prose follows damage without changing combat resolution."""

import random
import unittest
from unittest.mock import patch

from battle_flavor import hit_description
from combat import AttackResult, roll_attack
from game import Game
from tests.test_combat import ScriptedRandom
from tests.test_game import combat_game


def hit_result(damage, *, roll=15, total=20, critical=False):
    return AttackResult((roll,), roll, total, True, critical, damage, 12)


def scripted_game(*values):
    game = combat_game()
    game.rng = ScriptedRandom(*values)
    return game


class HitDescriptionTests(unittest.TestCase):
    def test_damage_bands_include_each_lower_and_upper_boundary_for_both_sides(self):
        cases = ((1, "glancing"), (5, "glancing"), (6, "solid"),
                 (10, "solid"), (11, "heavy"), (15, "heavy"),
                 (16, "devastating"), (100, "devastating"))
        for attacker, defender in (("You", "Crypt Rat"), ("Crypt Rat", "you")):
            for damage, severity in cases:
                with self.subTest(attacker=attacker, damage=damage):
                    text = hit_description(attacker, defender, hit_result(damage)).lower()
                    self.assertIn(severity, text)
                    for other in {"glancing", "solid", "heavy", "devastating"} - {severity}:
                        self.assertNotIn(other, text)

    def test_severity_uses_damage_even_with_a_huge_attack_total(self):
        text = hit_description("You", "Crypt Rat", hit_result(1, total=200)).lower()
        self.assertIn("glancing", text)
        self.assertNotIn("devastating", text)
        text = hit_description("You", "Crypt Rat", hit_result(16, total=12)).lower()
        self.assertIn("devastating", text)

    def test_low_damage_critical_stays_glancing_and_has_critical_narration(self):
        result = roll_attack(ScriptedRandom(20, 1, 1), 5, 12, (1, 6), 1)
        description = hit_description("You", "Crypt Rat", result)
        self.assertIn("glancing", description.lower())
        self.assertNotEqual(description, hit_description(
            "You", "Crypt Rat", hit_result(3, roll=20, total=25)))
        text = Game.attack_text("You", "Crypt Rat", result)
        self.assertIn("Critical hit!", text)
        self.assertIn("for 1d6 × 2 + 1 (3) damage", text)
        self.assertNotIn("devastating", text.lower())

    def test_zero_damage_hit_has_clear_no_damage_narration(self):
        for attacker, defender in (("You", "Crypt Rat"), ("Crypt Rat", "you")):
            for critical in (False, True):
                with self.subTest(attacker=attacker, critical=critical):
                    result = hit_result(0, critical=critical)
                    text = hit_description(attacker, defender, result).lower()
                    self.assertTrue(text)
                    self.assertRegex(text, r"(?:no|without) (?:\w+ )?damage|no (?:\w+ )?harm")
                    self.assertNotIn("devastating", text)
                    self.assertIn("for 0 damage", Game.attack_text(attacker, defender, result))

    def test_misses_never_receive_successful_hit_narration(self):
        for natural in (1, 5, 13):
            result = roll_attack(ScriptedRandom(natural), 5, 20, (1, 8), 3)
            for attacker, defender in (("You", "Crypt Rat"), ("Crypt Rat", "you")):
                with self.subTest(natural=natural, attacker=attacker):
                    self.assertEqual(hit_description(attacker, defender, result), "")
                    text = Game.attack_text(attacker, defender, result)
                    self.assertIn("miss", text.lower())
                    if natural == 1:
                        self.assertIn("Critical fail!", text)
                    elif natural == 13:
                        self.assertIn("Near miss!", text)

    def test_attack_roll_damage_and_critical_marker_remain_visible(self):
        result = roll_attack(
            ScriptedRandom(12, 20, 5, 8), 5, 18, (1, 8), 3, advantage=True
        )
        for attacker, defender in (("You", "Crypt Rat"), ("Crypt Rat", "you")):
            with self.subTest(attacker=attacker):
                text = Game.attack_text(attacker, defender, result)
                self.assertIn("d20 [12/20], total 25", text)
                self.assertIn("for 1d8 × 2 + 3 (16) damage", text)
                self.assertIn("Critical hit!", text)
                self.assertIn(hit_description(attacker, defender, result), text)

    def test_monster_descriptions_use_their_existing_weapon_traits(self):
        cases = (("Crypt Rat", r"claw"), ("Catacomb Stalker", r"claw"),
                 ("Thornbound Sentinel", r"root|thorn"),
                 ("Ember Colossus", r"fist|metal|iron"),
                 ("Warden of Thalinor", r"blade|sword"),
                 ("Restless Knight", r"blade|sword"),
                 ("Void Knight", r"blade|sword"),
                 ("Hollow King", r"dark|shadow"))
        for name, trait in cases:
            with self.subTest(name=name):
                text = hit_description(name, "you", hit_result(7)).lower()
                self.assertRegex(text, trait)
                self.assertIn(name.lower(), text)
                self.assertIn("solid", text)
        self.assertRegex(hit_description("You", "Crypt Rat", hit_result(7)).lower(),
                         r"sword|blade")

    def test_unknown_monster_has_a_named_generic_strike(self):
        text = hit_description("Practice guardian", "you", hit_result(7))
        self.assertIn("Practice guardian", text)
        self.assertIn("solid", text.lower())
        self.assertRegex(text.lower(), r"strike|blow")

    def test_prose_variation_is_repeatable_without_random_draws_or_result_mutation(self):
        before = random.getstate()
        result = hit_result(7)
        with patch("random.choice", side_effect=AssertionError("Narration used RNG")), \
                patch("random.randint", side_effect=AssertionError("Narration used RNG")):
            for attacker, defender in (("You", "Crypt Rat"), ("Crypt Rat", "you")):
                first = hit_description(attacker, defender, result)
                self.assertEqual(hit_description(attacker, defender, result), first)
                variants = {hit_description(attacker, defender,
                                            hit_result(7, roll=roll, total=roll + 5))
                            for roll in range(10, 20)}
                self.assertGreater(len(variants), 1)
        self.assertEqual(random.getstate(), before)
        self.assertEqual(result, hit_result(7))

    def test_narration_does_not_claim_unimplemented_conditions_or_healing(self):
        names = ("You", "Crypt Rat", "Thornbound Sentinel", "Ember Colossus",
                 "Warden of Thalinor", "Hollow King", "Practice guardian")
        for name in names:
            for damage in (0, 1, 7, 13, 20):
                with self.subTest(name=name, damage=damage):
                    text = hit_description(name, "you" if name != "You" else "Crypt Rat",
                                           hit_result(damage)).lower()
                    self.assertNotRegex(text, r"\b(?:stunned|paralyzed|bleeding|heals|regains|healing)\b")


class SuccessfulHitIntegrationTests(unittest.TestCase):
    def test_player_hit_preserves_damage_action_sap_time_and_dice_calls(self):
        game = scripted_game(15, 4)
        elapsed = game.elapsed_minutes
        output = "\n".join(game.handle_command("attack"))
        self.assertIn("solid", output.lower())
        self.assertIn("d20 [15], total 20", output)
        self.assertIn("for 1d8 + 5 (9) damage", output)
        self.assertEqual(game.enemy.hp, 91)
        self.assertEqual(game.player.hp, 12)
        self.assertEqual(game.actions_remaining, 0)
        self.assertTrue(game.bonus_action_available)
        self.assertTrue(game.enemy_sapped)
        self.assertEqual(game.elapsed_minutes, elapsed)
        self.assertEqual(game.rng.calls, [(1, 20), (1, 8)])

    def test_enemy_hit_preserves_damage_round_time_and_dice_calls(self):
        game = scripted_game(15, 2)
        game.enemy.name = "Crypt Rat"
        elapsed = game.elapsed_minutes
        output = "\n".join(game.handle_command("end"))
        self.assertIn("glancing", output.lower())
        self.assertIn("claw", output.lower())
        self.assertIn("for 1d6 + 1 (3) damage", output)
        self.assertEqual(game.player.hp, 9)
        self.assertEqual(game.enemy.hp, 100)
        self.assertEqual(game.round_number, 2)
        self.assertEqual(game.actions_remaining, 1)
        self.assertAlmostEqual(game.elapsed_minutes, elapsed + 0.1)
        self.assertEqual(game.rng.calls, [(1, 20), (1, 6)])

    def test_extra_attack_gets_separate_severities_without_extra_rolls(self):
        game = scripted_game(15, 1, 15, 8)
        game.player.gain_xp(6500)
        hp = game.player.hp
        output = "\n".join(game.handle_command("attack"))
        self.assertIn("Extra Attack", output)
        self.assertIn("solid", output.lower())
        self.assertIn("heavy", output.lower())
        self.assertIn("for 1d8 + 5 (6) damage", output)
        self.assertIn("for 1d8 + 5 (13) damage", output)
        self.assertEqual(game.enemy.hp, 81)
        self.assertEqual(game.player.hp, hp)
        self.assertEqual(game.actions_remaining, 0)
        self.assertEqual(game.rng.calls, [(1, 20), (1, 8), (1, 20), (1, 8)])

    def test_finishing_blow_uses_rolled_damage_not_remaining_hit_points(self):
        game = scripted_game(15, 8)
        enemy = game.enemy
        enemy.hp = 1
        output = "\n".join(game.handle_command("attack"))
        self.assertIn("heavy", output.lower())
        self.assertIn("for 1d8 + 5 (13) damage", output)
        self.assertIsNone(game.enemy)
        self.assertEqual(enemy.hp, 0)
        self.assertEqual(game.player.xp, 50)
        self.assertEqual(game.rng.calls, [(1, 20), (1, 8)])

    def test_low_damage_enemy_critical_keeps_critical_dice_and_glancing_flavor(self):
        game = scripted_game(20, 1, 1)
        output = "\n".join(game.handle_command("end"))
        self.assertIn("Critical hit!", output)
        self.assertIn("glancing", output.lower())
        self.assertIn("for 1d6 × 2 + 1 (3) damage", output)
        self.assertEqual(game.player.hp, 9)
        self.assertEqual(game.rng.calls, [(1, 20), (1, 6), (1, 6)])


if __name__ == "__main__":
    unittest.main()
