"""Probability boundaries, usable item variety, and room-table integration."""

from collections import Counter, deque
from dataclasses import FrozenInstanceError
import random
import unittest
from unittest.mock import patch

from dungeon import Dungeon
from equipment import EquipmentItem, equipment_options
from loot_library import (
    Loot, roll_enchantment, roll_equipment, roll_room_loot,
)


class ScriptedLootRNG:
    """Choose category outcomes without accidentally depending on later draws."""

    def __init__(self, categories=(), integer_rolls=(), later_random=0.0):
        self.categories = deque(categories)
        self.integer_rolls = deque(integer_rolls)
        self.later_random = later_random
        self.range_limits = []

    def random(self):
        return self.categories.popleft() if self.categories else self.later_random

    def randint(self, minimum, maximum):
        if minimum > maximum:
            raise AssertionError("Invalid gold range")
        return minimum

    def randrange(self, limit):
        self.range_limits.append(limit)
        result = self.integer_rolls.popleft() if self.integer_rolls else 0
        if not 0 <= result < limit:
            raise AssertionError("Scripted treasure roll outside its range")
        return result

    def choice(self, options):
        return options[0]


def found_categories(loot):
    return {
        "gold": bool(loot.gold),
        "potions": bool(loot.potions),
        "valuable": any(item.kind == "valuable" for item in loot.items),
        "trinket": any(item.kind in ("ember", "mana") for item in loot.items),
        "equipment": bool(loot.equipment),
    }


class RoomLootProbabilityTests(unittest.TestCase):
    # Explicit expected rates test the published design rather than deriving
    # both the expected and actual behavior from the implementation table.
    rates = {
        "cache": (0.75, 0.35, 0.40, 0.15, 0.30),
        "monster": (0.30, 0.15, 0.20, 0.10, 0.15),
        "guardian": (0.70, 0.35, 0.50, 0.25, 0.30),
    }
    categories = ("gold", "potions", "valuable", "trinket", "equipment")

    def test_each_category_has_its_own_exact_success_boundary(self):
        for source, rates in self.rates.items():
            for index, (category, chance) in enumerate(zip(self.categories, rates)):
                for roll, succeeds in ((chance - 0.000001, True), (chance, False)):
                    with self.subTest(source=source, category=category, roll=roll):
                        draws = [0.999999] * 5
                        draws[index] = roll
                        rng = ScriptedLootRNG(draws)
                        loot = roll_room_loot(rng, 1, "fighter", source)
                        expected = dict.fromkeys(self.categories, False)
                        expected[category] = succeeds
                        self.assertEqual(found_categories(loot), expected)
                        self.assertFalse(rng.categories)

    def test_multiple_categories_can_succeed_together_and_empty_loot_is_valid(self):
        for source in self.rates:
            with self.subTest(source=source):
                full = roll_room_loot(ScriptedLootRNG([0.0] * 5), 3, "rogue", source)
                self.assertTrue(all(found_categories(full).values()))
                self.assertEqual(full.potions, 1)
                self.assertEqual(len(full.equipment), 1)
                self.assertEqual(full.equipment[0].bonus, 0)
                self.assertIsNone(full.weapon_name)
                self.assertIsNone(full.armor_name)
                empty = roll_room_loot(ScriptedLootRNG([0.999999] * 5), 3, "rogue", source)
                self.assertEqual(empty, Loot())
                self.assertFalse(empty.has_treasure)

    def test_observed_room_rates_and_joint_outcomes_match_independent_rolls(self):
        count = 5000
        for source, rates in self.rates.items():
            rng = random.Random(f"room probabilities: {source}")
            found = Counter()
            both = 0
            empty = 0
            for _ in range(count):
                loot = roll_room_loot(rng, 1, "fighter", source)
                present = found_categories(loot)
                found.update(category for category, exists in present.items() if exists)
                both += present["equipment"] and present["potions"]
                empty += not loot.has_treasure
            for category, chance in zip(self.categories, rates):
                with self.subTest(source=source, category=category):
                    self.assertAlmostEqual(found[category] / count, chance, delta=0.025)
            self.assertAlmostEqual(both / count, rates[1] * rates[4], delta=0.025)
            self.assertGreater(empty, 0)

    def test_room_gold_scales_with_depth_without_guaranteeing_other_contents(self):
        for source, minimum in (("cache", 8), ("monster", 4), ("guardian", 12)):
            for floor in range(1, 6):
                with self.subTest(source=source, floor=floor):
                    rng = ScriptedLootRNG([0.0, 0.999999, 0.999999, 0.999999, 0.999999])
                    loot = roll_room_loot(rng, floor, "wizard", source)
                    self.assertEqual(loot.gold, minimum * floor)
                    self.assertEqual(loot.equipment, ())
                    self.assertEqual(loot.items, ())
                    self.assertEqual(loot.potions, 0)


class EquipmentRarityTests(unittest.TestCase):
    def test_mundane_and_magic_bands_have_exact_boundaries_on_each_floor(self):
        # The tiny final floor-one band makes +3 possible, never guaranteed.
        boundaries = {
            1: (70000, 97000, 99900),
            2: (55000, 90000, 99500),
            3: (40000, 80000, 98000),
            4: (25000, 67000, 95000),
            5: (15000, 55000, 90000),
        }
        for floor, bands in boundaries.items():
            for bonus, (lower, upper) in enumerate(zip((0, *bands), (*bands, 100000))):
                for roll in (lower, upper - 1):
                    with self.subTest(floor=floor, bonus=bonus, roll=roll):
                        rng = ScriptedLootRNG(integer_rolls=[roll])
                        self.assertEqual(roll_enchantment(rng, floor), bonus)
                        self.assertEqual(rng.range_limits, [100000])

    def test_deeper_floors_increase_magic_frequency_and_average_enchantment(self):
        magic_rates = []
        averages = []
        strongest_rates = []
        for floor in range(1, 6):
            rng = random.Random(12647)
            bonuses = [roll_enchantment(rng, floor) for _ in range(10000)]
            self.assertTrue(all(0 <= bonus <= 3 for bonus in bonuses))
            magic_rates.append(sum(bonus > 0 for bonus in bonuses) / len(bonuses))
            averages.append(sum(bonuses) / len(bonuses))
            strongest_rates.append(bonuses.count(3) / len(bonuses))
        self.assertEqual(magic_rates, sorted(magic_rates))
        self.assertEqual(averages, sorted(averages))
        self.assertEqual(strongest_rates, sorted(strongest_rates))
        self.assertTrue(0.25 < magic_rates[0] < 0.35)
        self.assertTrue(0.80 < magic_rates[-1] < 0.90)
        self.assertLess(strongest_rates[0], 0.003)
        self.assertTrue(0.08 < strongest_rates[-1] < 0.12)

    def test_both_equipment_kinds_are_possible_with_mundane_and_plus_three_variants(self):
        for class_id in ("fighter", "rogue", "wizard"):
            for kind_roll, kind in ((0.499999, "weapon"), (0.5, "armor")):
                for enchantment_roll, bonus in ((0, 0), (99999, 3)):
                    with self.subTest(class_id=class_id, kind=kind, bonus=bonus):
                        rng = ScriptedLootRNG([kind_roll], [enchantment_roll])
                        item = roll_equipment(rng, 1, class_id)
                        self.assertEqual((item.kind, item.bonus), (kind, bonus))
                        self.assertIn(class_id, item.spec.classes)
                        rarity = "mundane" if bonus == 0 else ("very rare" if kind == "weapon" else "legendary")
                        self.assertEqual(item.rarity, rarity)
                        self.assertEqual("+" in item.name, bonus > 0)

    def test_random_finds_cover_multiple_mundane_weapons_and_armor_for_every_class(self):
        for class_id in ("fighter", "rogue", "wizard"):
            with self.subTest(class_id=class_id):
                rng = random.Random(f"item variety: {class_id}")
                items = [roll_equipment(rng, 1, class_id) for _ in range(1000)]
                self.assertTrue(all(class_id in item.spec.classes for item in items))
                self.assertTrue(all(item.bonus <= 3 for item in items))
                for kind in ("weapon", "armor"):
                    expected_ids = {spec.id for spec in equipment_options(class_id, kind)}
                    mundane_ids = {item.base_id for item in items if item.kind == kind and item.bonus == 0}
                    self.assertEqual(mundane_ids, expected_ids)
                    self.assertGreaterEqual(len(mundane_ids), 3)
                weapon_dice = {item.spec.damage_dice for item in items if item.kind == "weapon"}
                armor_ac = {item.spec.base_ac for item in items if item.kind == "armor"}
                self.assertGreaterEqual(len(weapon_dice), 2)
                self.assertGreaterEqual(len(armor_ac), 2)

    def test_loot_results_are_seeded_and_equipment_objects_are_immutable(self):
        for class_id in ("fighter", "rogue", "wizard"):
            first = random.Random(87)
            second = random.Random(87)
            outcomes = [roll_room_loot(first, 4, class_id) for _ in range(100)]
            self.assertEqual(outcomes, [roll_room_loot(second, 4, class_id) for _ in range(100)])
        item = EquipmentItem("longsword", 1)
        loot = Loot(equipment=(item,))
        self.assertTrue(loot.has_treasure)
        with self.assertRaises(FrozenInstanceError):
            item.bonus = 3
        with self.assertRaises(FrozenInstanceError):
            loot.equipment = ()


class LootValidationTests(unittest.TestCase):
    def test_invalid_generation_inputs_do_not_consume_random_state(self):
        invalid_floors = (0, 6, True, 1.5, "1", None)
        calls = [(roll_enchantment, (floor,)) for floor in invalid_floors]
        calls += [(roll_equipment, (floor, "fighter")) for floor in invalid_floors]
        calls += [(roll_room_loot, (floor, "fighter")) for floor in invalid_floors]
        calls += [(roll_equipment, (1, class_id)) for class_id in ("cleric", None, [])]
        calls += [(roll_room_loot, (1, class_id)) for class_id in ("cleric", None, [])]
        calls += [(roll_room_loot, (1, "fighter", source)) for source in ("unknown", None, [])]
        for function, args in calls:
            with self.subTest(function=function.__name__, args=args):
                rng = random.Random(10)
                before = rng.getstate()
                with self.assertRaises(ValueError):
                    function(rng, *args)
                self.assertEqual(rng.getstate(), before)


class DungeonLootTableIntegrationTests(unittest.TestCase):
    def test_all_nonentrance_rooms_use_their_appropriate_table_once(self):
        for class_id in ("fighter", "rogue", "wizard"):
            for floor in range(1, 6):
                with self.subTest(class_id=class_id, floor=floor):
                    rolled = []

                    def record_roll(rng, floor, class_id, source="cache"):
                        rolled.append((floor, class_id, source))
                        return Loot(gold=1)

                    with patch("dungeon.roll_room_loot", side_effect=record_roll) as roller:
                        dungeon = Dungeon(random.Random(5), floor=floor, class_id=class_id)
                    self.assertEqual(roller.call_count, 11)
                    sources = Counter(source for _, _, source in rolled)
                    self.assertEqual(sources, {"cache": 4, "monster": 6, "guardian": 1})
                    for actual_floor, actual_class, _ in rolled:
                        self.assertEqual((actual_floor, actual_class), (floor, class_id))
                    self.assertIsNone(dungeon.get_room(dungeon.start).loot)
                    for room in dungeon.rooms.values():
                        if room.position != dungeon.start:
                            self.assertEqual(room.loot, Loot(gold=1))

    def test_no_fixed_opening_magic_or_other_loot_survives_failed_room_rolls(self):
        with patch("dungeon.roll_room_loot", return_value=Loot()):
            for class_id in ("fighter", "rogue", "wizard"):
                for seed in (0, 7, 42):
                    dungeon = Dungeon(random.Random(seed), class_id=class_id)
                    for room in dungeon.rooms.values():
                        self.assertFalse(room.loot and room.loot.has_treasure)
                    self.assertEqual(sum(bool(room.enemy) for room in dungeon.rooms.values()), 7)

    def test_class_and_depth_drops_remain_reproducible(self):
        for class_id in ("fighter", "rogue", "wizard"):
            for floor in range(1, 6):
                with self.subTest(class_id=class_id, floor=floor):
                    first = Dungeon(random.Random(927), floor=floor, class_id=class_id)
                    second = Dungeon(random.Random(927), floor=floor, class_id=class_id)
                    self.assertEqual(first.rooms, second.rooms)


if __name__ == "__main__":
    unittest.main()
