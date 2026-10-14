"""Damage notation describes the actual dice without changing their rolls."""

from dataclasses import replace
import random
import unittest

from combat import AttackResult, damage_notation, format_damage_pool, roll_attack
from game import Game
from room import Enemy
from tests.test_combat import ScriptedRandom


def combat_fixture(class_id, *faces, level=1):
    """Use ordinary engine actions against a durable, deterministic foe."""
    game = Game(seed=7, class_id=class_id)
    game.player.level = level
    if class_id == "wizard":
        game.player.spell_slots = dict(game.player.max_spell_slots)
    game.room.enemy = Enemy("Damage test foe", 100, 100, 12, 3, (1, 6), 1, 50, 0)
    game.rng = ScriptedRandom(*faces)
    game.begin_turn()
    return game


class DamageBreakdownTests(unittest.TestCase):
    def test_normal_hit_records_each_die_and_modifier(self):
        rng = ScriptedRandom(14, 3, 4)
        result = roll_attack(rng, 4, 12, (2, 6), 3)
        self.assertEqual(result.damage_rolls, (3, 4))
        self.assertEqual(result.extra_damage_rolls, ())
        self.assertEqual(result.raw_damage, 10)
        self.assertEqual(damage_notation(result), "2d6 + 3 (10)")
        self.assertEqual(rng.calls, [(1, 20), (1, 6), (1, 6)])

    def test_critical_rolls_two_dice_and_adds_bonus_once(self):
        rng = ScriptedRandom(20, 6, 5)
        result = roll_attack(rng, 3, 99, (1, 6), 1)
        self.assertEqual(result.damage_rolls, (6, 5))
        self.assertEqual(result.damage, 12)
        self.assertEqual(damage_notation(result), "1d6 × 2 + 1 (12)")
        self.assertEqual(rng.calls, [(1, 20), (1, 6), (1, 6)])

    def test_critical_sneak_damage_shows_both_doubled_pools(self):
        rng = ScriptedRandom(20, 8, 4, 2, 4)
        result = roll_attack(
            rng, 4, 15, (1, 8), 3, extra_damage_dice=(1, 6)
        )
        self.assertEqual(result.damage_rolls, (8, 4))
        self.assertEqual(result.extra_damage_rolls, (2, 4))
        self.assertEqual(result.extra_damage, 6)
        self.assertEqual(result.damage, 21)
        self.assertEqual(
            damage_notation(result), "1d8 × 2 + 1d6 × 2 + 3 (21)"
        )
        self.assertEqual(rng.calls, [(1, 20), (1, 8), (1, 8), (1, 6), (1, 6)])

    def test_sneak_damage_and_negative_modifier_combine_before_zero_floor(self):
        rng = ScriptedRandom(15, 1, 6)
        result = roll_attack(
            rng, 4, 12, (1, 8), -4, extra_damage_dice=(1, 6)
        )
        self.assertEqual(result.damage, 3)
        self.assertEqual(damage_notation(result), "1d8 + 1d6 - 4 (3)")
        self.assertEqual(result.damage_rolls, (1,))
        self.assertEqual(result.extra_damage_rolls, (6,))

    def test_zero_floor_does_not_invent_extra_rolls(self):
        rng = ScriptedRandom(12, 1)
        result = roll_attack(rng, 4, 12, (1, 8), -4)
        self.assertEqual((result.raw_damage, result.damage), (0, 0))
        self.assertEqual(damage_notation(result), "1d8 - 4 (0)")
        self.assertEqual(rng.calls, [(1, 20), (1, 8)])

    def test_misses_record_no_damage_rolls_or_false_dice_formula(self):
        for face in (1, 2):
            with self.subTest(face=face):
                rng = ScriptedRandom(face)
                result = roll_attack(
                    rng, 4, 20, (1, 8), 3, extra_damage_dice=(1, 6)
                )
                self.assertEqual(result.damage_rolls, ())
                self.assertEqual(result.extra_damage_rolls, ())
                self.assertEqual(result.raw_damage, 0)
                self.assertEqual(damage_notation(result), "0")
                self.assertEqual(rng.calls, [(1, 20)])
                self.assertEqual(result.fumble_damage, 1 if face == 1 else 0)

    def test_uncanny_dodge_preserves_original_damage_roll(self):
        result = roll_attack(ScriptedRandom(13, 6), 4, 12, (1, 8), 3)
        reduced = replace(result, damage=result.damage // 2)
        self.assertEqual(damage_notation(reduced), "1d8 + 3 (9; halved to 4)")
        self.assertEqual(result.damage, 9)
        self.assertEqual(reduced.raw_damage, 9)
        self.assertEqual(reduced.damage_rolls, (6,))

    def test_other_reduction_is_not_called_halving(self):
        result = roll_attack(ScriptedRandom(13, 6), 4, 12, (1, 8), 3)
        self.assertEqual(
            damage_notation(replace(result, damage=2)), "1d8 + 3 (9; reduced to 2)"
        )

    def test_old_positional_results_keep_numeric_fallback(self):
        result = AttackResult((12,), 12, 15, True, False, 7, 13, 2)
        self.assertEqual(damage_notation(result), "7")
        self.assertEqual(result.extra_damage, 2)

    def test_notation_does_not_mutate_or_use_rng(self):
        rng = random.Random(723)
        result = roll_attack(rng, 20, 10, (2, 6), 2)
        before = rng.getstate()
        for _ in range(5):
            self.assertIn("2d6", damage_notation(result))
        self.assertEqual(rng.getstate(), before)

    def test_advantage_damage_roll_order_remains_unchanged(self):
        rng = ScriptedRandom(1, 17, 3, 5)
        result = roll_attack(
            rng, 4, 12, (1, 8), 2, advantage=True, extra_damage_dice=(1, 6)
        )
        self.assertEqual(result.rolls, (1, 17))
        self.assertEqual(result.damage_rolls, (3,))
        self.assertEqual(result.extra_damage_rolls, (5,))
        self.assertEqual(damage_notation(result), "1d8 + 1d6 + 2 (10)")
        self.assertEqual(rng.calls, [(1, 20), (1, 20), (1, 8), (1, 6)])


class SpellDamageNotationTests(unittest.TestCase):
    def test_automatic_spell_and_consumable_damage(self):
        self.assertEqual(format_damage_pool((3, 4), 3, 10), "3d4 + 3 (10)")
        self.assertEqual(format_damage_pool((3, 6), 0, 12), "3d6 (12)")

    def test_fireball_save_shows_original_and_reduced_total(self):
        self.assertEqual(
            format_damage_pool((8, 6), 0, 13, original_total=27),
            "8d6 (27; halved to 13)",
        )

    def test_equal_original_total_has_no_reduction_clause(self):
        self.assertEqual(
            format_damage_pool((1, 6), 0, 3, original_total=3), "1d6 (3)"
        )

    def test_invalid_pool_rejected_without_randomness(self):
        for pool in ((0, 6), (1, 1), (-1, 6)):
            with self.subTest(pool=pool):
                with self.assertRaises(ValueError):
                    format_damage_pool(pool, 0, 0)


class DamageNotationIntegrationTests(unittest.TestCase):
    def test_uncanny_dodge_prints_original_and_actual_damage(self):
        game = combat_fixture("rogue", 15, 6, level=5)
        hp = game.player.hp
        output = "\n".join(game.handle_command("end"))
        self.assertIn("for 1d6 + 1 (7; halved to 3) damage", output)
        self.assertIn("Uncanny Dodge", output)
        self.assertEqual(game.player.hp, hp - 3)
        self.assertEqual(game.rng.calls, [(1, 20), (1, 6)])

    def test_fire_bolt_critical_displays_two_dice_without_a_flat_bonus(self):
        game = combat_fixture("wizard", 20, 1, 1)
        slots = dict(game.player.spell_slots)
        output = "\n".join(game.handle_command("cast firebolt"))
        self.assertIn("for 1d10 × 2 (2) damage", output)
        self.assertIn("Critical hit!", output)
        self.assertEqual(game.enemy.hp, 98)
        self.assertEqual(game.player.spell_slots, slots)
        self.assertEqual(game.rng.calls, [(1, 20), (1, 10), (1, 10)])

    def test_frost_lance_critical_shows_doubled_three_die_pool(self):
        game = combat_fixture("wizard", 20, 1, 2, 3, 4, 5, 6, level=3)
        output = "\n".join(game.handle_command("cast frost"))
        self.assertIn("for 3d8 × 2 (21) damage", output)
        self.assertIn("Critical hit!", output)
        self.assertEqual(game.enemy.hp, 79)
        self.assertTrue(game.enemy_sapped)
        self.assertEqual(game.rng.calls, [(1, 20), *([(1, 8)] * 6)])

    def test_magic_missile_displays_three_d4_and_flat_bonus(self):
        game = combat_fixture("wizard", 1, 2, 4)
        game.enemy.armor_class = 99
        output = "\n".join(game.handle_command("cast missile"))
        self.assertIn("for 3d4 + 3 (10) force damage", output)
        self.assertEqual(game.enemy.hp, 90)
        self.assertEqual(game.player.spell_slots[1], 1)
        self.assertEqual(game.actions_remaining, 0)
        self.assertEqual(game.rng.calls, [(1, 4)] * 3)

    def test_ember_stone_displays_its_three_d6_pool(self):
        game = combat_fixture("fighter", 1, 2, 3)
        game.player.ember_stones = 1
        output = "\n".join(game.handle_command("ember"))
        self.assertIn("for 3d6 (6) magic damage", output)
        self.assertEqual(game.enemy.hp, 94)
        self.assertEqual(game.player.ember_stones, 0)
        self.assertEqual(game.actions_remaining, 0)
        self.assertTrue(game.bonus_action_available)
        self.assertEqual(game.rng.calls, [(1, 6)] * 3)

    def test_fireball_displays_pool_and_only_halves_on_a_successful_save(self):
        for save, expected, notation in (
            (9, 24, "8d6 (24)"),
            (10, 12, "8d6 (24; halved to 12)"),
        ):
            with self.subTest(save=save):
                game = combat_fixture("wizard", *([3] * 8), save, level=5)
                game.enemy.initiative_bonus = 4
                output = "\n".join(game.handle_command("cast fireball"))
                self.assertIn(f"Flames deal {notation} damage", output)
                self.assertEqual(game.enemy.hp, 100 - expected)
                self.assertEqual(game.player.spell_slots[3], 1)
                self.assertEqual(game.actions_remaining, 0)
                self.assertEqual(game.rng.calls, [*([(1, 6)] * 8), (1, 20)])

    def test_critical_failure_has_fixed_self_damage_without_damage_dice(self):
        game = combat_fixture("fighter", 1)
        hp = game.player.hp
        output = "\n".join(game.handle_command("attack"))
        self.assertIn("Critical fail!", output)
        self.assertIn("1 HP of self-damage", output)
        self.assertNotIn("1d8", output)
        self.assertEqual(game.player.hp, hp - 1)
        self.assertEqual(game.enemy.hp, 100)
        self.assertEqual(game.rng.calls, [(1, 20)])


if __name__ == "__main__":
    unittest.main()
