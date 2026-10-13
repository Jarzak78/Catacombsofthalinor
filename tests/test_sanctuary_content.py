"""Mira's lore, complete category views, and examined shop descriptions."""

import unittest

from campaign import (
    FLOORS,
    SANCTUARY_MENU,
    sanctuary_dialogue,
    shop_items,
    stock,
)
from equipment import ARMOR_SLOTS


class SanctuaryContentTests(unittest.TestCase):
    def test_mira_introduces_herself_then_comments_on_each_cleared_floor(self):
        dialogue = [sanctuary_dialogue(floor) for floor in range(1, 6)]
        self.assertEqual(len(set(dialogue)), 5)
        self.assertIn("I'm Mira", dialogue[0])
        self.assertIn("sanctuary", dialogue[0])
        for floor, line in zip(FLOORS, dialogue):
            with self.subTest(floor=floor.name):
                self.assertIn(floor.guardian.replace("The ", ""), line)
                self.assertLess(len(line.split()), 65)
        self.assertIn("Rootbound Depths", dialogue[1])
        self.assertIn("Ashen Forge", dialogue[2])
        self.assertIn("Starless Vault", dialogue[3])
        self.assertIn("Thalinor's Heart", dialogue[4])
        self.assertIn("way out", dialogue[4])
        self.assertNotIn("lies ahead", dialogue[4])

    def test_mira_dialogue_rejects_invalid_floor_without_index_wrapping(self):
        for invalid in (0, 6, -1, True, False, "1", 1.0, None):
            with self.subTest(floor=invalid):
                with self.assertRaises(ValueError):
                    sanctuary_dialogue(invalid)

    def test_menu_has_six_distinct_short_navigation_choices(self):
        self.assertEqual([key for key, _ in SANCTUARY_MENU],
                         [str(number) for number in range(1, 7)])
        self.assertEqual(len({label for _, label in SANCTUARY_MENU}), 6)
        self.assertTrue(all(len(label.split()) <= 4
                            for _, label in SANCTUARY_MENU))
        self.assertEqual(SANCTUARY_MENU[0][1], "Weapons")
        self.assertEqual(SANCTUARY_MENU[1][1], "Armor")

    def test_categories_partition_complete_stock_without_hiding_details(self):
        for class_id in ("fighter", "rogue", "wizard"):
            for floor in range(1, 6):
                with self.subTest(class_id=class_id, floor=floor):
                    all_items = stock(floor, class_id)
                    self.assertEqual(shop_items(floor, class_id), all_items)
                    categories = [shop_items(floor, class_id, category)
                                  for category in ("weapons", "armor", "supplies")]
                    flattened = [item for category in categories for item in category]
                    self.assertEqual(len(flattened), len(all_items))
                    self.assertEqual({item.id for item in flattened},
                                     {item.id for item in all_items})
                    self.assertTrue(all(item.description for item in flattened))
                    self.assertTrue(all(item.equipment is None
                                        for item in categories[2]))

    def test_each_class_has_all_five_armor_slots_at_every_unlocked_tier(self):
        for class_id in ("fighter", "rogue", "wizard"):
            for floor in range(1, 6):
                for slot in ARMOR_SLOTS:
                    with self.subTest(class_id=class_id, floor=floor, slot=slot):
                        items = shop_items(floor, class_id, slot)
                        self.assertTrue(items)
                        self.assertEqual({item.value for item in items},
                                         set(range(min(floor, 3) + 1)))
                        self.assertTrue(all(item.equipment.slot == slot
                                            for item in items))
                        self.assertTrue(all(class_id in item.equipment.spec.classes
                                            for item in items))
                        self.assertTrue(all(item.equipment.affix == ""
                                            for item in items))

    def test_standard_shop_gear_does_not_guarantee_random_armor_buffs(self):
        for class_id in ("fighter", "rogue", "wizard"):
            for item in shop_items(5, class_id, "armor"):
                with self.subTest(class_id=class_id, item=item.id):
                    self.assertEqual(item.equipment.affix, "")
                    self.assertFalse(item.equipment.buffs)
                    self.assertIn("Slot: " + item.equipment.slot,
                                  item.description)
                    if item.value:
                        self.assertIn("capped at +3", item.description)
                    if item.equipment.slot == "torso":
                        self.assertIn("Base AC", item.description)
                    else:
                        self.assertIn("no separate base AC",
                                      item.description)
                        self.assertNotIn("Base AC", item.description)

    def test_shop_descriptions_explain_spell_focus_and_weapon_tradeoffs(self):
        weapons = {item.id: item for item in shop_items(2, "wizard", "weapons")}
        self.assertIn("1d6", weapons["arcane_staff_2"].description)
        self.assertIn("spell save DC", weapons["arcane_staff_2"].description)
        self.assertIn("not spells", weapons["quarterstaff_2"].description)
        fighter_weapons = {item.id: item for item in shop_items(1, "fighter", "weapons")}
        self.assertIn("2d6", fighter_weapons["greatsword"].description)
        self.assertIn("cannot use a shield", fighter_weapons["greatsword"].description)

    def test_supplies_describe_consumption_and_non_slot_upgrades(self):
        supplies = {item.id: item for item in shop_items(1, "wizard", "supplies")}
        self.assertIn("2d4+2 HP", supplies["potion"].description)
        self.assertIn("bonus action", supplies["potion"].description)
        self.assertIn("3d6", supplies["ember"].description)
        self.assertIn("no attack roll", supplies["ember"].description)
        self.assertIn("higher-level", supplies["mana"].description)
        for item_id in ("charm", "ward"):
            self.assertIn("does not occupy an armor slot", supplies[item_id].description)

    def test_category_aliases_and_validation(self):
        for alias, canonical in (("weapon", "weapons"), ("ARMOR", "armor"),
                                 ("armors", "armor"), ("supply", "supplies")):
            self.assertEqual(shop_items(1, "rogue", alias),
                             shop_items(1, "rogue", canonical))
        self.assertEqual(shop_items(1, "rouge", "boots"),
                         shop_items(1, "rogue", "boots"))
        for invalid in ("jewelry", "", "cape", True, None):
            with self.subTest(category=invalid):
                with self.assertRaises(ValueError):
                    shop_items(1, "fighter", invalid)


if __name__ == "__main__":
    unittest.main()
