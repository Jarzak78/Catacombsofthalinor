"""Expanded treasure, class equipment, and reproducible drop generation."""

from dataclasses import FrozenInstanceError
import random
import unittest
from unittest.mock import patch

from campaign import stock
from dungeon import Dungeon
from equipment import EquipmentItem, equipment_options
from loot_library import (
    Loot, RUNEBLADE_CACHE, TreasureItem, ember_stone, mana_draught,
    suitable_armor_name, suitable_weapon_name, valuable,
)


class TreasureModelTests(unittest.TestCase):
    def test_legacy_positional_bundle_and_runeblade_remain_compatible(self):
        self.assertEqual(Loot(12, 0, "Thalinor Longsword +1", 1), RUNEBLADE_CACHE)
        self.assertEqual(RUNEBLADE_CACHE.items, ())
        self.assertIsNone(RUNEBLADE_CACHE.armor_name)

    def test_item_only_and_armor_only_bundles_are_real_treasure(self):
        for loot in (Loot(gold=1), Loot(potions=1), Loot(weapon_name="Sword"),
                     Loot(items=(valuable(1),)), Loot(armor_name="Runic robes +1", armor_bonus=1)):
            self.assertTrue(loot.has_treasure)
        self.assertFalse(Loot().has_treasure)

    def test_items_and_bundles_reject_invalid_values_and_equipment(self):
        for kwargs in ({"value": -1}, {"amount": 0}, {"amount": -1},
                       {"amount": 1.5}, {"value": 1.5}, {"kind": "unknown"}, {"id": ""}):
            fields = dict(id="gem", name="Gem", description="A gem.", value=5, kind="valuable")
            fields.update(kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                TreasureItem(**fields)
        for kwargs in ({"armor_bonus": -1}, {"armor_bonus": 1}, {"weapon_bonus": 1},
                       {"gold": 1.5}, {"potions": True}, {"armor_name": ""},
                       {"items": [valuable(1)]}, {"items": ("gem",)}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Loot(**kwargs)

    def test_items_are_frozen_and_ids_keep_stable_unit_values(self):
        item = valuable(1)
        with self.assertRaises(FrozenInstanceError):
            item.value = 100
        by_id = {}
        for floor in range(1, 6):
            for variant in range(4):
                gem = valuable(floor, variant)
                previous = by_id.setdefault(gem.id, (gem.name, gem.value))
                self.assertEqual(previous, (gem.name, gem.value))
        self.assertEqual(ember_stone().kind, "ember")
        self.assertEqual(mana_draught().kind, "mana")

    def test_class_equipment_names_and_invalid_choices(self):
        for class_id, weapon, armor in (("fighter", "Longsword", "mail"),
                                         ("rogue", "Rapier", "leather"),
                                         ("wizard", "Staff", "robes")):
            self.assertIn(weapon.lower(), suitable_weapon_name(class_id, 2).lower())
            self.assertIn(armor.lower(), suitable_armor_name(class_id, 2).lower())
            self.assertNotIn("+0", suitable_weapon_name(class_id, 0))
            self.assertNotIn("+0", suitable_armor_name(class_id, 0))
        for helper in (suitable_weapon_name, suitable_armor_name):
            with self.assertRaises(ValueError):
                helper("cleric", 1)
            with self.assertRaises(ValueError):
                helper("fighter", -1)
            with self.assertRaises(ValueError):
                helper("fighter", 4)


class ExpandedDropTests(unittest.TestCase):
    def test_each_floor_can_produce_varied_collectible_and_usable_treasure(self):
        for floor in range(1, 6):
            items = []
            for seed in range(100):
                dungeon = Dungeon(random.Random(seed), floor=floor)
                items.extend(item for room in dungeon.rooms.values()
                             if room.loot for item in room.loot.items)
            self.assertEqual({item.kind for item in items}, {"valuable", "ember", "mana"})
            self.assertEqual(len({item.id for item in items if item.kind == "valuable"}), 4)
            for item in items:
                self.assertGreater(item.value, 0)
                self.assertEqual(item.amount, 1)

    def test_generation_reproduces_all_drops_for_each_class(self):
        for class_id in ("fighter", "rogue", "wizard"):
            for floor in range(1, 6):
                first = Dungeon(random.Random(321), floor=floor, class_id=class_id)
                second = Dungeon(random.Random(321), floor=floor, class_id=class_id)
                self.assertEqual(first.rooms, second.rooms)
                self.assertEqual(first.class_id, class_id)

    def test_random_equipment_has_varied_base_types_and_suits_the_class(self):
        for class_id in ("fighter", "rogue", "wizard"):
            found = {"weapon": set(), "armor": set()}
            no_opening_magic = 0
            for seed in range(100):
                dungeon = Dungeon(random.Random(seed), class_id=class_id)
                adjacent = set(dungeon.get_room(dungeon.start).exits.values())
                no_opening_magic += not any(room.position in adjacent and room.loot
                                           and any(item.bonus for item in room.loot.equipment)
                                           for room in dungeon.rooms.values())
                for room in dungeon.rooms.values():
                    if not room.loot:
                        continue
                    for item in room.loot.equipment:
                        self.assertIn(class_id, item.spec.classes)
                        self.assertLessEqual(item.bonus, 3)
                        found[item.kind].add(item.base_id)
            self.assertGreater(no_opening_magic, 0)
            for kind in ("weapon", "armor"):
                self.assertGreater(len(found[kind]), 1)

    def test_rare_upgrades_are_less_common_than_items_and_not_guaranteed(self):
        cache_equipment = monster_equipment = guardian_equipment = monster_items = 0
        runs_without_cache_upgrade = 0
        for seed in range(300):
            dungeon = Dungeon(random.Random(seed), floor=3)
            run_cache_equipment = 0
            for room in dungeon.rooms.values():
                loot = room.loot
                if not loot:
                    continue
                equipment = bool(loot.equipment)
                if room.enemy:
                    if room.enemy.boss:
                        guardian_equipment += equipment
                    else:
                        monster_equipment += equipment
                        monster_items += bool(loot.items)
                else:
                    run_cache_equipment += equipment
            cache_equipment += run_cache_equipment
            runs_without_cache_upgrade += run_cache_equipment == 0
        # Broad bands catch accidental guaranteed drops without brittle seeds.
        self.assertTrue(0.25 < cache_equipment / (300 * 4) < 0.35)
        self.assertTrue(0.10 < monster_equipment / (300 * 6) < 0.20)
        self.assertTrue(0.24 < guardian_equipment / 300 < 0.36)
        self.assertTrue(0.22 < monster_items / (300 * 6) < 0.34)
        self.assertGreater(monster_items, monster_equipment)
        self.assertGreater(runs_without_cache_upgrade, 40)

    def test_added_loot_does_not_change_layout_monsters_or_progressive_stats(self):
        for floor in range(1, 6):
            for seed in (0, 7, 42):
                expanded = Dungeon(random.Random(seed), floor=floor)
                with patch("dungeon.roll_room_loot", return_value=Loot()):
                    original = Dungeon(random.Random(seed), floor=floor)
                self.assertEqual(len([r for r in expanded.rooms.values() if r.enemy]), 7)
                for position, room in expanded.rooms.items():
                    expected = original.get_room(position)
                    self.assertEqual((room.name, room.description, room.exits, room.enemy),
                                     (expected.name, expected.description, expected.exits, expected.enemy))

    def test_invalid_class_fails_before_consuming_generator(self):
        rng = random.Random(7)
        before = rng.getstate()
        with self.assertRaises(ValueError):
            Dungeon(rng, class_id="cleric")
        self.assertEqual(rng.getstate(), before)


class ClassShopTests(unittest.TestCase):
    def test_stock_reliably_supplies_every_proficient_type_and_unlocked_tier(self):
        for class_id in ("fighter", "rogue", "wizard"):
            for floor in range(1, 6):
                with self.subTest(class_id=class_id, floor=floor):
                    items = stock(floor, class_id)
                    gear = [item for item in items if item.equipment]
                    expected = {EquipmentItem(spec.id, bonus).id
                                for spec in equipment_options(class_id)
                                for bonus in range(min(floor, 3) + 1)}
                    self.assertEqual({item.id for item in gear}, expected)
                    self.assertEqual(len({item.id for item in items}), len(items))
                    self.assertEqual(items, stock(floor, class_id))
                    self.assertTrue(all(item.price > 0 for item in items))
                    self.assertTrue(all(class_id in item.equipment.spec.classes for item in gear))
                    self.assertLessEqual(max(item.value for item in gear), 3)
        fighter = {item.id: item for item in stock(1)}
        self.assertEqual([fighter[key].price for key in ("potion", "charm", "ward", "ember")],
                         [12, 35, 65, 18])
        self.assertEqual((fighter["longsword"].name, fighter["longsword"].price), ("Longsword", 10))
        self.assertEqual((fighter["longsword_1"].name, fighter["longsword_1"].price), ("Longsword +1", 45))
        self.assertEqual(fighter["chain_mail_1"].price, 55)

    def test_rogue_and_wizard_get_correct_gear_and_wizard_can_buy_mana(self):
        rogue = {item.id: item for item in stock(2, "rogue")}
        wizard = {item.id: item for item in stock(2, "wizard")}
        self.assertEqual(rogue["rapier_2"].name, "Rapier +2")
        self.assertEqual(rogue["studded_leather_2"].name, "Studded Leather +2")
        self.assertEqual(wizard["arcane_staff_2"].name, "Arcane Staff +2")
        self.assertEqual(wizard["robes_2"].name, "Robes +2")
        self.assertTrue(wizard["arcane_staff_2"].equipment.spec.focus)
        self.assertTrue(wizard["robes_2"].equipment.spec.unarmored)
        self.assertEqual((wizard["mana"].kind, wizard["mana"].price), ("mana", 18))
        self.assertNotIn("mana", rogue)
        for items in (rogue, wizard):
            self.assertNotIn("longsword", items)
            self.assertNotIn("chain_mail", items)


if __name__ == "__main__":
    unittest.main()
