"""Floor-specific creatures retain their own clues and combat narration."""

from dataclasses import asdict
import json
import unittest

from battle_flavor import hit_description, miss_description
from combat import AttackResult, roll_attack
from enemy_lore import foe_details
from monster_catalog import FLOOR_MONSTERS
from room import Enemy
from tests.test_combat import ScriptedRandom
from tests.test_game import combat_game


NEW_MONSTERS = tuple(
    spec for floor, roster in FLOOR_MONSTERS.items() if floor > 1
    for spec in roster
)


def scaled_foe(spec):
    """Use current stats deliberately different from the catalog's base values."""
    return Enemy(spec.name, spec.hp + 10, spec.hp + 7,
                 spec.armor_class + 2, spec.attack_bonus + 2,
                 spec.damage_dice, spec.damage_bonus + 2,
                 spec.xp_reward * 3, spec.gold_reward * 3,
                 initiative_bonus=spec.initiative_bonus)


class MonsterExaminationTests(unittest.TestCase):
    def test_every_new_species_has_its_authored_profile_and_current_stats(self):
        self.assertEqual(len(NEW_MONSTERS), 24)
        for spec in NEW_MONSTERS:
            foe = scaled_foe(spec)
            before = asdict(foe)
            for class_id in ("fighter", "rogue", "wizard"):
                with self.subTest(foe=spec.name, class_id=class_id):
                    details = foe_details(foe, class_id)
                    self.assertEqual(details["description"], spec.description)
                    self.assertIn(spec.tactics, details["tactics"])
                    self.assertEqual(details["hp"], foe.hp)
                    self.assertEqual(details["max_hp"], foe.max_hp)
                    self.assertEqual(details["armor_class"], foe.armor_class)
                    self.assertEqual(details["attack_bonus"], foe.attack_bonus)
                    self.assertEqual(details["damage_bonus"], foe.damage_bonus)
                    self.assertEqual(details["damage_dice"], list(foe.damage_dice))
                    json.dumps(details)
                    details["damage_dice"][0] = 999
                    details["hp"] = 0
                    self.assertEqual(asdict(foe), before)

    def test_new_profiles_keep_species_clues_with_class_appropriate_advice(self):
        for spec in NEW_MONSTERS:
            foe = scaled_foe(spec)
            with self.subTest(foe=spec.name):
                warrior = foe_details(foe)
                rogue = foe_details(foe, "rogue")
                wizard = foe_details(foe, "wizard")
                self.assertIn("Sap", warrior["tactics"])
                self.assertIn("Dodge", warrior["tactics"])
                self.assertIn("opening Hide", rogue["tactics"])
                self.assertIn("Sneak Attack once per turn", rogue["tactics"])
                self.assertIn("Mage Armor", wizard["tactics"])
                self.assertIn("Magic Missile", wizard["tactics"])
                for details in (rogue, wizard):
                    self.assertNotIn("Sap", details["tactics"])
                    self.assertNotIn("longsword", details["tactics"].lower())


class MonsterNarrationTests(unittest.TestCase):
    def test_new_species_hit_and_near_miss_prose_uses_its_own_traits(self):
        hit = AttackResult((16,), 16, 21, True, False, 7, 12)
        miss = AttackResult((13,), 13, 18, False, False, 0, 20)
        for spec in NEW_MONSTERS:
            with self.subTest(foe=spec.name):
                self.assertIn(spec.strike, hit_description(spec.name, "you", hit))
                self.assertIn(spec.surface, hit_description("You", spec.name, hit))
                self.assertIn(spec.strike, miss_description(spec.name, "you", miss))
                self.assertIn(spec.surface, miss_description("You", spec.name, miss))
                for attacker, defender in ((spec.name, "you"), ("You", spec.name)):
                    text = miss_description(attacker, defender, miss)
                    self.assertIn("Near miss!", text)
                    self.assertIn("No damage is dealt.", text)
                    self.assertEqual(text, miss_description(attacker, defender, miss))

    def test_every_new_fumble_uses_species_mishap_and_hurts_only_attacker(self):
        for spec in NEW_MONSTERS:
            with self.subTest(foe=spec.name):
                game = combat_game()
                enemy = scaled_foe(spec)
                game.room.enemy = enemy
                hp = enemy.hp
                player_hp = game.player.hp
                rng = ScriptedRandom(1)
                game.rng = rng
                output = "\n".join(game.handle_command("end"))
                self.assertIn(spec.fumble.format(attacker=spec.name), output)
                self.assertIn("Critical fail!", output)
                self.assertIn("1 HP of self-damage", output)
                self.assertEqual(enemy.hp, hp - 1)
                self.assertEqual(game.player.hp, player_hp)
                self.assertEqual(rng.calls, [(1, 20)])
                self.assertEqual(game.player.xp, 0)

    def test_narration_preserves_hit_result_and_spends_no_extra_dice(self):
        spec = FLOOR_MONSTERS[4][0]
        rng = ScriptedRandom(20, 1, 1)
        result = roll_attack(rng, spec.attack_bonus, 20,
                             spec.damage_dice, spec.damage_bonus)
        before = asdict(result)
        text = hit_description(spec.name, "you", result)
        self.assertIn("Glancing blow!", text)
        self.assertIn(spec.strike, text)
        self.assertIn("exposed angle", text)
        self.assertEqual(miss_description(spec.name, "you", result), "")
        self.assertEqual(asdict(result), before)
        self.assertEqual(rng.calls, [(1, 20), (1, spec.damage_dice[1]),
                                     (1, spec.damage_dice[1])])


if __name__ == "__main__":
    unittest.main()
