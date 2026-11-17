"""Foe examination gives usable guidance for each adventurer class."""

from dataclasses import asdict
import json
import unittest

from campaign import FLOORS
from enemy_lore import foe_details
from room import Enemy
from room_library import ENEMY_TEMPLATES


PROFILE_NAMES = tuple(template[0] for template in ENEMY_TEMPLATES) + tuple(
    floor.guardian for floor in FLOORS
)


class ClassFoeLoreTests(unittest.TestCase):
    def foe(self, name):
        return Enemy(name, 31, 23, 17, 6, (1, 8), 4, 100, 10,
                     boss=name in {floor.guardian for floor in FLOORS})

    def test_all_authored_foes_have_class_appropriate_tactics(self):
        self.assertEqual(len(PROFILE_NAMES), 11)
        for name in PROFILE_NAMES:
            foe = self.foe(name)
            warrior = foe_details(foe)
            self.assertEqual(warrior, foe_details(foe, "fighter"))
            for class_id in ("rogue", "wizard"):
                with self.subTest(name=name, class_id=class_id):
                    details = foe_details(foe, class_id)
                    self.assertEqual(details["description"], warrior["description"])
                    self.assertEqual(details["damage_dice"], [1, 8])
                    self.assertEqual(details["hp"], 23)
                    self.assertNotIn("Sap", details["tactics"])
                    self.assertNotIn("longsword", details["tactics"].lower())
                    if class_id == "rogue":
                        self.assertIn("Hide", details["tactics"])
                        self.assertIn("Vex", details["tactics"])
                        self.assertIn("Sneak Attack once per turn", details["tactics"])
                        self.assertIn("critical hit", details["tactics"])
                    else:
                        self.assertIn("Mage Armor", details["tactics"])
                        self.assertIn("bonus action", details["tactics"])
                        self.assertIn("next enemy strike", details["tactics"])
                        self.assertIn("When available, a Frost Lance", details["tactics"])

    def test_unknown_foes_get_class_guidance_without_invented_enemy_abilities(self):
        foe = self.foe("Unknown sentry")
        for class_id in ("fighter", "rogue", "wizard"):
            with self.subTest(class_id=class_id):
                details = foe_details(foe, class_id)
                self.assertIn("no further clues", details["description"])
                self.assertEqual(details["damage_bonus"], foe.damage_bonus)
                self.assertEqual(details["attack_bonus"], foe.attack_bonus)
                self.assertEqual(details["boss"], foe.boss)

    def test_class_details_are_detached_and_do_not_mutate_the_foe(self):
        foe = self.foe("Crypt Rat")
        before = asdict(foe)
        for class_id in ("fighter", "rogue", "wizard"):
            with self.subTest(class_id=class_id):
                details = foe_details(foe, class_id)
                json.dumps(details)
                details["damage_dice"][0] = 100
                details["hp"] = 0
                details["tactics"] = "A renderer's temporary text"
                self.assertEqual(asdict(foe), before)
                self.assertEqual(foe_details(foe, class_id)["damage_dice"], [1, 8])


if __name__ == "__main__":
    unittest.main()
