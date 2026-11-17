"""Hide-only Sneak Attack and the consequences of a detected opening Hide."""

import unittest
from unittest.mock import patch

from combat import roll_attack
from equipment import EquipmentItem, make_equipment
from tests.test_class_actions import class_game
from tests.test_room_scouting import entry_game


class HiddenSneakAttackTests(unittest.TestCase):
    def test_visible_vex_critical_doubles_weapon_dice_without_sneak_dice(self):
        game = class_game("rogue", [20, 3, 2, 5])
        game.rogue_vex = True
        with patch("game.roll_attack", wraps=roll_attack) as attack:
            output = game.handle_command("attack")
        self.assertIsNone(attack.call_args.kwargs["extra_damage_dice"])
        self.assertTrue(attack.call_args.kwargs["advantage"])
        self.assertEqual(game.enemy.hp, 90)  # Two weapon dice + Dexterity once.
        self.assertFalse(game.sneak_attack_used)
        self.assertFalse(game.hidden)
        self.assertNotIn("Sneak Attack", "\n".join(output))
        self.assertEqual(game.rng.calls,
                         [(1, 20, 20), (1, 20, 3), (1, 8, 2), (1, 8, 5)])
        self.assertFalse(game.rng.values)

    def test_visible_advantaged_hit_preserves_sneak_for_a_hidden_hit_same_turn(self):
        game = class_game("rogue", [15, 2, 4, 15, 2, 4, 5])
        game.actions_remaining = 2
        game.rogue_vex = True
        first = game.handle_command("attack")
        self.assertEqual(game.enemy.hp, 93)
        self.assertFalse(game.sneak_attack_used)
        self.assertNotIn("Sneak Attack", "\n".join(first))
        # Isolate eligibility from the action cost of obtaining Hide: this
        # character has an additional action and is hidden for the next hit.
        game.hidden = True
        second = game.handle_command("attack")
        self.assertEqual(game.enemy.hp, 81)
        self.assertTrue(game.sneak_attack_used)
        self.assertIn("Sneak Attack", "\n".join(second))
        self.assertFalse(game.hidden)
        self.assertEqual(sum(high == 6 for _, high, _ in game.rng.calls), 1)
        self.assertFalse(game.rng.values)

    def test_a_second_hidden_hit_cannot_repeat_sneak_in_the_same_turn(self):
        game = class_game("rogue", [15, 2, 4, 5, 15, 2, 4])
        game.actions_remaining = 2
        game.hidden = True
        game.handle_command("attack")
        game.hidden = True
        with patch("game.roll_attack", wraps=roll_attack) as attack:
            second = game.handle_command("attack")
        self.assertIsNone(attack.call_args.kwargs["extra_damage_dice"])
        self.assertEqual(game.enemy.hp, 81)
        self.assertNotIn("Sneak Attack", "\n".join(second))
        self.assertTrue(game.sneak_attack_used)
        self.assertFalse(game.hidden)
        self.assertFalse(game.rng.values)

    def test_a_hidden_finesse_warrior_does_not_gain_the_rogue_ability(self):
        game = class_game("fighter", [15, 2, 4])
        rapier = make_equipment("rapier")
        game.player.collect_equipment(rapier, auto_equip=False)
        self.assertTrue(game.player.equip_equipment(rapier))
        game.hidden = True
        with patch("game.roll_attack", wraps=roll_attack) as attack:
            game.handle_command("attack")
        self.assertTrue(attack.call_args.kwargs["advantage"])
        self.assertIsNone(attack.call_args.kwargs["extra_damage_dice"])
        self.assertFalse(game.sneak_attack_used)
        self.assertFalse(game.rng.values)


class StrictHideTests(unittest.TestCase):
    def test_noisy_armor_uses_the_lower_of_two_rolls_against_dc_twenty(self):
        for lower, success in ((12, False), (13, True)):
            with self.subTest(lower=lower):
                game = class_game("rogue", [19, lower], level=2)
                armor = make_equipment("padded")
                game.player.collect_equipment(armor, auto_equip=False)
                self.assertTrue(game.player.equip_equipment(armor))
                self.assertTrue(game.player.stealth_disadvantage)
                output = game.handle_command("hide")
                self.assertEqual(game.hidden, success)
                self.assertEqual(game.actions_remaining, 1)
                self.assertFalse(game.bonus_action_available)
                self.assertIn(f"d20 [19/{lower}]", "\n".join(output))
                self.assertIn("DC 20", "\n".join(output))
                self.assertEqual(game.rng.calls, [(1, 20, 19), (1, 20, lower)])
                self.assertFalse(game.rng.values)

    def test_hide_uses_current_dexterity_and_expertise_at_dc_twenty(self):
        game = class_game("rogue", [11], level=5)
        game.player.dexterity = 16
        self.assertEqual(game.player.stealth_bonus, 9)  # +3 Dexterity, +6 expertise.
        output = game.handle_command("hide")
        self.assertTrue(game.hidden)
        self.assertIn("= 20 vs DC 20", "\n".join(output))
        self.assertEqual(game.rng.calls, [(1, 20, 11)])

    def test_shadow_boots_change_hide_only_while_actually_equipped(self):
        for worn in (False, True):
            with self.subTest(worn=worn):
                game = class_game("rogue", [11], level=2)
                boots = EquipmentItem("leather_boots", 2, "shadow")
                game.player.collect_equipment(boots, auto_equip=False)
                if worn:
                    self.assertTrue(game.player.equip_equipment(boots))
                self.assertEqual(game.player.stealth_bonus, 9 if worn else 7)
                output = game.handle_command("hide")
                self.assertEqual(game.hidden, worn)
                self.assertIn("DC 20", "\n".join(output))
                self.assertEqual(game.rng.calls, [(1, 20, 11)])
                self.assertFalse(game.rng.values)

    def test_a_detected_midfight_hide_spends_its_bonus_without_reinitiative(self):
        game = class_game("rogue", [12, 2], level=2)
        hp = game.player.hp
        game.handle_command("hide")  # Total 19 fails DC 20.
        self.assertFalse(game.hidden)
        self.assertFalse(game.bonus_action_available)
        self.assertEqual(game.actions_remaining, 1)
        self.assertEqual(game.player.hp, hp)
        self.assertIsNone(game.initiative_result)
        self.assertFalse(game.ambush_advantage)
        output = game.handle_command("end")
        self.assertIn("d20 [2]", "\n".join(output))
        self.assertEqual(game.player.hp, hp)
        self.assertEqual(game.rng.calls, [(1, 20, 12), (1, 20, 2)])
        self.assertFalse(game.rng.values)


class DetectedOpeningHideTests(unittest.TestCase):
    def test_detection_gives_exactly_one_advantaged_strike_without_perception_reroll(self):
        game, direction, _ = entry_game(values=[12, 12, 2, 20, 2, 19, 2, 2])
        game.handle_command(direction)
        hp = game.player.hp
        first = game.handle_command("hide")
        self.assertFalse(game.hidden)
        self.assertFalse(game.enemy_unaware)
        self.assertFalse(game.opening_hide_available)
        self.assertFalse(game.initiative_result["hero_first"])
        self.assertIsNone(game.perception_result)
        self.assertEqual(game.player.hp, hp - 3)
        self.assertIn("d20 [2/19]", "\n".join(first))
        self.assertFalse(game.ambush_advantage)
        self.assertEqual(game.actions_remaining, 1)
        self.assertTrue(game.bonus_action_available)
        second = game.handle_command("end")
        self.assertIn("d20 [2]", "\n".join(second))
        self.assertEqual(game.player.hp, hp - 3)
        self.assertEqual(game.rng.calls,
                         [(1, 20, 12), (1, 20, 12), (1, 20, 2), (1, 20, 20),
                          (1, 20, 2), (1, 20, 19), (1, 6, 2), (1, 20, 2)])
        self.assertFalse(game.rng.values)

    def test_discarded_one_on_the_detecting_foes_advantaged_attack_does_not_fumble(self):
        game, direction, _ = entry_game(values=[12, 1, 2, 20, 1, 19, 2])
        game.handle_command(direction)
        hp, foe_hp = game.player.hp, game.enemy.hp
        output = game.handle_command("hide")
        self.assertEqual(game.player.hp, hp - 3)
        self.assertEqual(game.enemy.hp, foe_hp)
        self.assertIn("d20 [1/19]", "\n".join(output))
        self.assertFalse(game.ambush_advantage)
        self.assertIsNone(game.perception_result)
        self.assertFalse(game.rng.values)

    def test_two_ones_fumble_once_on_the_detecting_foes_advantaged_attack(self):
        game, direction, _ = entry_game(values=[12, 1, 2, 20, 1, 1])
        game.handle_command(direction)
        hp, foe_hp = game.player.hp, game.enemy.hp
        game.handle_command("hide")
        self.assertEqual(game.player.hp, hp)
        self.assertEqual(game.enemy.hp, foe_hp - 1)
        self.assertFalse(game.ambush_advantage)
        self.assertIsNone(game.perception_result)
        self.assertEqual(game.actions_remaining, 1)
        self.assertTrue(game.bonus_action_available)
        self.assertFalse(game.rng.values)

    def test_successful_hide_never_rolls_initiative_or_arms_ambush_advantage(self):
        game, direction, _ = entry_game(values=[12, 13])
        game.handle_command(direction)
        game.handle_command("hide")
        self.assertTrue(game.hidden)
        self.assertTrue(game.enemy_unaware)
        self.assertFalse(game.ambush_advantage)
        self.assertEqual(game.initiative_result["source"], "scouting")
        self.assertIsNone(game.perception_result)
        self.assertEqual(game.actions_remaining, 1)
        self.assertTrue(game.bonus_action_available)
        self.assertEqual(game.rng.calls, [(1, 20, 12), (1, 20, 13)])
        self.assertFalse(game.rng.values)


if __name__ == "__main__":
    unittest.main()
