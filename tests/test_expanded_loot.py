"""Expanded treasure, class equipment, and reproducible drop generation."""

from dataclasses import FrozenInstanceError
import random
import unittest
from unittest.mock import patch

from campaign import stock
from dungeon import Dungeon
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
            self.assertIn(weapon, suitable_weapon_name(class_id, 2))
            self.assertIn(armor, suitable_armor_name(class_id, 2))
        for helper in (suitable_weapon_name, suitable_armor_name):
            with self.assertRaises(ValueError):
                helper("cleric", 1)
            with self.assertRaises(ValueError):
                helper("fighter", -1)


class ExpandedDropTests(unittest.TestCase):
    def test_every_floor_has_varied_collectible_and_usable_treasure(self):
        for floor in range(1, 6):
            dungeon = Dungeon(random.Random(7), floor=floor)
            caches = [room for room in dungeon.rooms.values() if room.loot and not room.enemy]
            self.assertEqual(len(caches), 4)
            items = [item for room in caches for item in room.loot.items]
            self.assertEqual({item.kind for item in items}, {"valuable", "ember", "mana"})
            self.assertEqual(len({item.id for item in items if item.kind == "valuable"}), 4)
            self.assertEqual(sum(room.loot.gold for room in caches), 30 * floor)
            self.assertEqual(sum(room.loot.potions for room in caches), 3 if floor == 1 else 5)

    def test_generation_reproduces_all_drops_for_each_class(self):
        for class_id in ("fighter", "rogue", "wizard"):
            for floor in range(1, 6):
                first = Dungeon(random.Random(321), floor=floor, class_id=class_id)
                second = Dungeon(random.Random(321), floor=floor, class_id=class_id)
                self.assertEqual(first.rooms, second.rooms)
                self.assertEqual(first.class_id, class_id)

    def test_opening_upgrade_and_all_random_gear_suit_the_class(self):
        for class_id, weapon, armor in (("fighter", "longsword", "mail"),
                                         ("rogue", "rapier", "leather"),
                                         ("wizard", "staff", "robes")):
            for seed in range(30):
                dungeon = Dungeon(random.Random(seed), class_id=class_id)
                adjacent = set(dungeon.get_room(dungeon.start).exits.values())
                self.assertTrue(any(room.position in adjacent and room.loot
                                    and room.loot.weapon_bonus == 1
                                    for room in dungeon.rooms.values()))
                for room in dungeon.rooms.values():
                    if not room.loot:
                        continue
                    if room.loot.weapon_name:
                        self.assertIn(weapon, room.loot.weapon_name.lower())
                    if room.loot.armor_name:
                        self.assertIn(armor, room.loot.armor_name.lower())

    def test_rare_upgrades_are_less_common_than_items_and_not_guaranteed(self):
        cache_upgrades = monster_upgrades = monster_items = 0
        runs_without_cache_upgrade = 0
        for seed in range(300):
            dungeon = Dungeon(random.Random(seed), floor=3)
            run_cache_upgrades = 0
            for room in dungeon.rooms.values():
                loot = room.loot
                if not loot:
                    continue
                equipment = bool(loot.weapon_name or loot.armor_name)
                if room.enemy:
                    monster_upgrades += equipment
                    monster_items += bool(loot.items)
                else:
                    run_cache_upgrades += equipment
            cache_upgrades += run_cache_upgrades
            runs_without_cache_upgrade += run_cache_upgrades == 0
        # Broad bands catch accidental guaranteed drops without brittle seeds.
        self.assertTrue(0.10 < cache_upgrades / (300 * 4) < 0.20)
        self.assertTrue(0.04 < monster_upgrades / (300 * 7) < 0.12)
        self.assertTrue(0.25 < monster_items / (300 * 7) < 0.45)
        self.assertGreater(monster_items, monster_upgrades)
        self.assertGreater(runs_without_cache_upgrade, 50)

    def test_added_loot_does_not_change_layout_monsters_or_progressive_stats(self):
        for floor in range(1, 6):
            for seed in (0, 7, 42):
                expanded = Dungeon(random.Random(seed), floor=floor)
                with patch.object(Dungeon, "_enrich_treasure", lambda *args: None):
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
    def test_fighter_stock_keeps_existing_ids_and_prices(self):
        items = stock(1)
        self.assertEqual([item.id for item in items], ["potion", "sword", "armor", "charm", "ward", "ember"])
        self.assertEqual([item.price for item in items], [12, 45, 40, 35, 65, 18])
        self.assertEqual(items[1].name, "Longsword +2")
        self.assertEqual(stock(5)[1].value, 5)

    def test_rogue_and_wizard_get_correct_gear_and_wizard_can_buy_mana(self):
        rogue = {item.id: item for item in stock(2, "rogue")}
        wizard = {item.id: item for item in stock(2, "wizard")}
        self.assertIn("Rapier", rogue["sword"].name)
        self.assertIn("leather", rogue["armor"].name)
        self.assertIn("Staff", wizard["sword"].name)
        self.assertIn("robes", wizard["armor"].name)
        self.assertEqual((wizard["mana"].kind, wizard["mana"].price), ("mana", 18))
        self.assertNotIn("mana", rogue)


if __name__ == "__main__":
    unittest.main()
