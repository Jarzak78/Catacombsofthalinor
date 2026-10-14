"""Foe examination offers class advice for the weapon actually equipped."""

from dataclasses import asdict
import unittest

from enemy_lore import foe_details
from equipment import make_equipment
from game import Game
from monster_catalog import FLOOR_MONSTERS
from room import Enemy


def foe(name="Bone Sentry"):
    return Enemy(name, 20, 16, 14, 4, (1, 6), 2, 50, 8)


class EquipmentFoeAdviceTests(unittest.TestCase):
    def test_explicit_masteries_match_supported_class_abilities(self):
        for class_id in ("fighter", "rogue", "wizard"):
            for mastery in ("", "sap", "vex"):
                with self.subTest(class_id=class_id, mastery=mastery):
                    tactics = foe_details(foe(), class_id, mastery)["tactics"]
                    self.assertEqual("Sap" in tactics,
                                     class_id == "fighter" and mastery == "sap")
                    self.assertEqual("Vex" in tactics,
                                     class_id in ("fighter", "rogue") and mastery == "vex")
                    self.assertNotIn("longsword", tactics.lower())
                    self.assertNotIn("rapier", tactics.lower())
                    if class_id == "fighter":
                        self.assertIn("Dodge", tactics)
                        self.assertIn("use remaining", tactics)
                        self.assertIn("from level 2", tactics)
                    elif class_id == "rogue":
                        self.assertIn("Hide", tactics)
                        self.assertIn("finesse-weapon", tactics)
                        self.assertIn("Sneak Attack once per turn", tactics)
                        self.assertIn("stealth", tactics)
                    else:
                        self.assertIn("Arcane Staff", tactics)
                        self.assertIn("physical strikes only", tactics)

    def test_new_species_keep_their_neutral_tactical_clues(self):
        for floor in range(2, 6):
            for spec in FLOOR_MONSTERS[floor]:
                with self.subTest(foe=spec.name):
                    details = foe_details(foe(spec.name), "fighter", "")
                    self.assertEqual(details["description"], spec.description)
                    self.assertTrue(details["tactics"].startswith(spec.tactics))
                    self.assertNotIn("Sap", details["tactics"])
                    self.assertNotIn("Vex", details["tactics"])

    def test_omitted_mastery_preserves_legacy_advice(self):
        for class_id in ("fighter", "rogue", "wizard"):
            self.assertEqual(foe_details(foe(), class_id),
                             foe_details(foe(), class_id, None))
        self.assertIn("longsword", foe_details(foe())["tactics"])
        self.assertIn("rapier", foe_details(foe(), "rogue")["tactics"])

    def test_unknown_foes_get_detached_equipment_aware_advice(self):
        enemy = foe("Unknown test foe")
        before = asdict(enemy)
        details = foe_details(enemy, "fighter", "vex")
        self.assertIn("no further clues", details["description"])
        self.assertIn("Vex", details["tactics"])
        details["hp"] = 0
        details["damage_dice"][0] = 100
        self.assertEqual(asdict(enemy), before)

    def test_invalid_mastery_is_rejected(self):
        for mastery in (False, 0, "topple", [], {}, "SAP"):
            with self.subTest(mastery=mastery):
                with self.assertRaises(ValueError):
                    foe_details(foe(), "fighter", mastery)

    def test_examination_and_snapshot_use_current_equipment(self):
        cases = (("fighter", "greatsword", ""),
                 ("fighter", "mace", "sap"),
                 ("fighter", "rapier", "vex"),
                 ("rogue", "dagger", ""),
                 ("rogue", "shortsword", "vex"),
                 ("wizard", "arcane_staff", ""))
        for class_id, base_id, mastery in cases:
            with self.subTest(class_id=class_id, weapon=base_id):
                game = Game(seed=7, class_id=class_id)
                item = make_equipment(base_id, 1)
                game.player.collect_equipment(item, auto_equip=False)
                self.assertTrue(game.player.equip_equipment(item))
                game.room.enemy = foe()
                game.free_examine_available = True
                game.foe_examined = False
                game.rng = None  # Examination and snapshots must consume no dice.
                expected = foe_details(game.enemy, class_id, mastery)
                output = "\n".join(game.examine_foe())
                self.assertIn(expected["tactics"], output)
                self.assertEqual(game.get_state()["encounter"]["foe_details"], expected)


if __name__ == "__main__":
    unittest.main()
