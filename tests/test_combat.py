"""Deterministic checks of the 2024 attack-roll and damage rules."""

import unittest

from combat import roll_attack, roll_dice, roll_healing_potion, roll_initiative


class ScriptedRandom:
    """Supply fixed dice and reject unexpected rolls or invalid faces."""

    def __init__(self, *values: int):
        self.values = list(values)
        self.calls: list[tuple[int, int]] = []

    def randint(self, lower: int, upper: int) -> int:
        self.calls.append((lower, upper))
        if not self.values:
            raise AssertionError("Unexpected extra dice roll.")
        value = self.values.pop(0)
        if not lower <= value <= upper:
            raise AssertionError(f"Scripted face {value} is outside {lower}..{upper}.")
        return value


class AttackTests(unittest.TestCase):
    def test_natural_one_misses_despite_large_bonus(self):
        rng = ScriptedRandom(1)
        result = roll_attack(rng, 99, 10, (1, 8), 3)
        self.assertFalse(result.hit)
        self.assertFalse(result.critical)
        self.assertEqual(result.total, 100)
        self.assertEqual(result.damage, 0)
        self.assertEqual(rng.calls, [(1, 20)])

    def test_natural_twenty_hits_despite_high_armor_class(self):
        rng = ScriptedRandom(20, 4, 6)
        result = roll_attack(rng, -10, 99, (1, 8), 3)
        self.assertTrue(result.hit)
        self.assertTrue(result.critical)
        self.assertEqual(result.total, 10)
        self.assertEqual(result.damage, 13)
        self.assertEqual(rng.calls, [(1, 20), (1, 8), (1, 8)])

    def test_critical_doubles_all_weapon_dice_but_not_flat_bonus(self):
        rng = ScriptedRandom(20, 1, 2, 3, 4)
        result = roll_attack(rng, 4, 12, (2, 6), 5)
        self.assertEqual(result.damage, 15)
        self.assertEqual(rng.calls.count((1, 6)), 4)

    def test_advantage_uses_the_higher_roll(self):
        rng = ScriptedRandom(1, 15, 7)
        result = roll_attack(rng, 3, 16, (1, 8), 2, advantage=True)
        self.assertEqual(result.rolls, (1, 15))
        self.assertEqual((result.roll, result.total), (15, 18))
        self.assertTrue(result.hit)
        self.assertFalse(result.critical)
        self.assertEqual(result.damage, 9)

    def test_disadvantage_uses_the_lower_roll_even_with_natural_twenty(self):
        rng = ScriptedRandom(20, 8)
        result = roll_attack(rng, 3, 12, (1, 8), 2, disadvantage=True)
        self.assertEqual(result.rolls, (20, 8))
        self.assertEqual(result.roll, 8)
        self.assertFalse(result.hit)
        self.assertFalse(result.critical)
        self.assertEqual(rng.calls, [(1, 20), (1, 20)])

    def test_advantage_and_disadvantage_cancel_to_one_die(self):
        rng = ScriptedRandom(12, 6)
        result = roll_attack(
            rng, 3, 15, (1, 8), 2, advantage=True, disadvantage=True
        )
        self.assertEqual(result.rolls, (12,))
        self.assertEqual(result.roll, 12)
        self.assertEqual(rng.calls, [(1, 20), (1, 8)])

    def test_attack_total_equal_to_armor_class_hits(self):
        result = roll_attack(ScriptedRandom(10, 4), 3, 13, (1, 8), 2)
        self.assertTrue(result.hit)
        self.assertEqual(result.damage, 6)

    def test_attack_below_armor_class_misses_without_rolling_damage(self):
        rng = ScriptedRandom(9)
        result = roll_attack(rng, 3, 13, (1, 8), 2)
        self.assertFalse(result.hit)
        self.assertEqual(result.damage, 0)
        self.assertEqual(rng.calls, [(1, 20)])

    def test_forced_critical_on_hit_doubles_damage_dice(self):
        rng = ScriptedRandom(12, 5, 7)
        result = roll_attack(rng, 3, 13, (1, 8), 2, critical_on_hit=True)
        self.assertTrue(result.hit)
        self.assertTrue(result.critical)
        self.assertEqual(result.damage, 14)

    def test_critical_on_hit_does_not_override_a_miss(self):
        for natural in (1, 5):
            with self.subTest(natural=natural):
                rng = ScriptedRandom(natural)
                result = roll_attack(rng, 3, 13, (1, 8), 2, critical_on_hit=True)
                self.assertFalse(result.hit)
                self.assertFalse(result.critical)
                self.assertEqual(rng.calls, [(1, 20)])

    def test_damage_cannot_be_negative(self):
        result = roll_attack(ScriptedRandom(12, 1), 3, 13, (1, 8), -5)
        self.assertTrue(result.hit)
        self.assertEqual(result.damage, 0)


class DiceTests(unittest.TestCase):
    def test_dice_pool_sums_independent_rolls(self):
        rng = ScriptedRandom(3, 6, 2)
        self.assertEqual(roll_dice(rng, 3, 6), 11)
        self.assertEqual(rng.calls, [(1, 6)] * 3)

    def test_invalid_dice_pool_fails_before_rolling(self):
        for count, sides in ((0, 6), (-1, 6), (1, 1), (1, 0)):
            with self.subTest(count=count, sides=sides):
                rng = ScriptedRandom()
                with self.assertRaises(ValueError):
                    roll_dice(rng, count, sides)
                self.assertEqual(rng.calls, [])

    def test_initiative_is_d20_plus_bonus(self):
        rng = ScriptedRandom(14)
        self.assertEqual(roll_initiative(rng, 3), 17)
        self.assertEqual(rng.calls, [(1, 20)])

    def test_healing_potion_is_two_d4_plus_two(self):
        rng = ScriptedRandom(1, 4)
        self.assertEqual(roll_healing_potion(rng), 7)
        self.assertEqual(rng.calls, [(1, 4), (1, 4)])


if __name__ == "__main__":
    unittest.main()
