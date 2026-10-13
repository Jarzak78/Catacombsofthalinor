"""Vendor choices, enchantment progression, and readable equipment IDs."""

from dataclasses import asdict
import json
import unittest

from campaign import FLOORS, ShopItem, preferred_item_id, stock
from equipment import EQUIPMENT, equipment_options, equipment_price


class VendorStockTests(unittest.TestCase):
    def test_every_proficient_equipment_type_is_available_at_each_unlocked_tier(self):
        for class_id in ("fighter", "rogue", "wizard"):
            options = equipment_options(class_id)
            for floor in range(1, len(FLOORS) + 1):
                with self.subTest(class_id=class_id, floor=floor):
                    shop = stock(floor, class_id)
                    gear = tuple(item for item in shop if item.equipment is not None)
                    expected = {(spec.id, bonus) for spec in options
                                for bonus in range(min(floor, 3) + 1)}
                    self.assertEqual({(item.equipment.base_id, item.value)
                                      for item in gear}, expected)
                    self.assertEqual(len(gear), len(expected))
                    self.assertEqual(len({item.id for item in shop}), len(shop))
                    for item in gear:
                        self.assertEqual(item.id, item.equipment.id)
                        self.assertEqual(item.name, item.equipment.name)
                        self.assertEqual(item.kind, item.equipment.kind)
                        self.assertEqual(item.price, equipment_price(item.equipment))
                        self.assertIn(class_id, item.equipment.spec.classes)

    def test_supplies_are_reliable_and_mana_is_only_stocked_for_wizards(self):
        expected = {"potion": 12, "ember": 18, "charm": 35, "ward": 65}
        for class_id in ("fighter", "rogue", "wizard"):
            for floor in range(1, len(FLOORS) + 1):
                with self.subTest(class_id=class_id, floor=floor):
                    supplies = {item.id: item for item in stock(floor, class_id)
                                if item.equipment is None}
                    prices = dict(expected, **({"mana": 18} if class_id == "wizard" else {}))
                    self.assertEqual({name: item.price for name, item in supplies.items()}, prices)
                    self.assertIn("2d4+2", supplies["potion"].description)
                    self.assertIn("3d6", supplies["ember"].description)
                    self.assertEqual(stock(floor, class_id), stock(floor, class_id))

    def test_shortcuts_select_class_appropriate_default_gear_and_never_exceed_plus_three(self):
        preferred = {
            "fighter": ("longsword", "chain_mail"),
            "rogue": ("rapier", "studded_leather"),
            "wizard": ("arcane_staff", "robes"),
        }
        for class_id, base_ids in preferred.items():
            for floor in range(1, len(FLOORS) + 1):
                for kind, base_id in zip(("weapon", "armor"), base_ids):
                    with self.subTest(class_id=class_id, floor=floor, kind=kind):
                        item_id = preferred_item_id(floor, class_id, kind)
                        self.assertEqual(item_id, f"{base_id}_{min(floor, 3)}")
                        self.assertIn(item_id, {item.id for item in stock(floor, class_id)})

    def test_class_aliases_use_the_same_stock_and_shortcuts(self):
        for alias, canonical in (("warrior", "fighter"), ("rouge", "rogue"),
                                 (" WIZARD ", "wizard")):
            self.assertEqual(stock(2, alias), stock(2, canonical))
            for kind in ("weapon", "armor"):
                self.assertEqual(preferred_item_id(2, alias, kind),
                                 preferred_item_id(2, canonical, kind))

    def test_floor_one_supports_an_affordable_standard_magic_upgrade(self):
        warrior = {item.id: item for item in stock(1, "fighter")}
        self.assertEqual(warrior["longsword_1"].price, 45)
        self.assertEqual(warrior["chain_mail_1"].price, 55)
        for class_id in ("fighter", "rogue", "wizard"):
            for kind in ("weapon", "armor"):
                items = [item for item in stock(1, class_id) if item.kind == kind]
                self.assertTrue(any(item.value == 0 and item.price <= 10 for item in items))
                self.assertTrue(any(item.value == 1 and item.price <= 50 for item in items))

    def test_descriptions_explain_damage_defense_and_important_equipment_tradeoffs(self):
        warrior = {item.id: item for item in stock(1, "fighter")}
        self.assertIn("2d6", warrior["greatsword"].description)
        self.assertIn("two-handed", warrior["greatsword"].description)
        self.assertIn("cannot use a shield", warrior["greatsword"].description)
        self.assertIn("Base AC 16", warrior["chain_mail"].description)
        self.assertNotIn("+ full Dexterity", warrior["chain_mail"].description)
        self.assertIn("maximum +2", warrior["scale_mail"].description)
        self.assertIn("stealth", warrior["scale_mail"].description)
        self.assertIn("+ full Dexterity", warrior["leather"].description)
        wizard = {item.id: item for item in stock(1, "wizard")}
        self.assertIn("spell save DC", wizard["arcane_staff_1"].description)
        self.assertIn("not spells", wizard["quarterstaff_1"].description)
        self.assertIn("Mage Armor", wizard["robes"].description)

    def test_stock_is_serializable_and_equipment_prices_increase_with_rarity(self):
        for class_id in ("fighter", "rogue", "wizard"):
            items = stock(5, class_id)
            json.dumps([asdict(item) for item in items])
            by_id = {item.id: item for item in items}
            for spec in equipment_options(class_id):
                prices = [by_id[spec.id if not bonus else f"{spec.id}_{bonus}"].price
                          for bonus in range(4)]
                self.assertTrue(all(lower < higher for lower, higher in zip(prices, prices[1:])))
                self.assertEqual(prices[0], EQUIPMENT[spec.id].base_price)

    def test_invalid_shop_parameters_are_rejected(self):
        for floor in (0, 6, -1, True, False, 1.0, "1", None):
            with self.subTest(floor=floor):
                with self.assertRaises(ValueError):
                    stock(floor)
                with self.assertRaises(ValueError):
                    preferred_item_id(floor, "fighter", "weapon")
        for class_id in ("cleric", "", None, True):
            with self.subTest(class_id=class_id):
                with self.assertRaises(ValueError):
                    stock(1, class_id)
                with self.assertRaises(ValueError):
                    preferred_item_id(1, class_id, "armor")
        with self.assertRaises(ValueError):
            preferred_item_id(1, "fighter", "trinket")

    def test_non_equipment_shop_items_keep_the_existing_constructor_contract(self):
        item = ShopItem("potion", "Healing potion", 12, "potion", 1, "Healing.")
        self.assertIsNone(item.equipment)


if __name__ == "__main__":
    unittest.main()
