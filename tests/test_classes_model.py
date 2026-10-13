"""Class statistics, rest boundaries, and spell-resource progression."""

import unittest

from equipment import ARMOR_SLOTS, DEFAULT_ARMOR_PIECES, make_equipment
from player import ABILITY_NAMES, Player
from tests.test_models import FixedRolls


class ClassModelTests(unittest.TestCase):
    def test_default_warrior_remains_original_character(self):
        player = Player()
        self.assertEqual(player.class_id, "fighter")
        self.assertEqual(player.class_name, "Warrior (Fighter)")
        self.assertEqual((player.hp, player.max_hp, player.armor_class), (12, 12, 18))
        self.assertEqual((player.attack_bonus, player.damage_bonus), (5, 5))
        self.assertEqual((player.second_wind_uses, player.action_surge_available), (2, True))
        self.assertEqual(player.spell_slots, {})
        self.assertFalse(player.arcane_recovery_available)

    def test_factory_presets_use_class_hp_equipment_and_attacks(self):
        expectations = {
            "fighter": (12, 18, "Longsword", 5, 5, (1, 8)),
            "rogue": (10, 15, "Rapier", 5, 3, (1, 8)),
            "wizard": (8, 12, "Quarterstaff", 1, -1, (1, 6)),
        }
        for class_id, expected in expectations.items():
            with self.subTest(class_id=class_id):
                player = Player.create(name="Mira", class_id=class_id)
                self.assertEqual(player.name, "Mira")
                self.assertEqual((player.hp, player.armor_class, player.weapon_name,
                                  player.attack_bonus, player.damage_bonus,
                                  player.weapon_dice), expected)
                self.assertEqual(player.hp, player.max_hp)
                self.assertEqual({slot: item.base_id for slot, item in player.equipped_armor_slots.items()},
                                 DEFAULT_ARMOR_PIECES[class_id])
                self.assertEqual(set(player.equipped_armor_slots), set(ARMOR_SLOTS))
                self.assertEqual(len(player.equipment_inventory), 6)
                self.assertTrue(all(player.is_equipped(item)
                                    for item in player.equipment_inventory))
                self.assertTrue(all(item.bonus == 0 and not item.buffs
                                    for item in player.equipment_inventory))

    def test_warrior_alias_and_case_normalize_but_unknown_class_is_rejected(self):
        self.assertEqual(Player.create(class_id=" Warrior ").class_id, "fighter")
        self.assertEqual(Player(class_id="ROGUE").class_id, "rogue")
        for class_id in ("bard", "", None, 2):
            with self.subTest(class_id=class_id):
                with self.assertRaises(ValueError):
                    Player.create(class_id=class_id)

    def test_factory_applies_all_six_rolled_stats_without_mutating_them(self):
        stats = dict(zip(ABILITY_NAMES, (18, 17, 3, 16, 15, 14)))
        original = stats.copy()
        player = Player.create(class_id="rogue", stats=stats)
        self.assertEqual([getattr(player, name) for name in ABILITY_NAMES], list(stats.values()))
        self.assertEqual((player.hp, player.max_hp), (4, 4))
        self.assertEqual(player.armor_class, 15)
        self.assertEqual(player.attack_bonus, 6)  # Finesse uses the higher Strength modifier.
        self.assertEqual(player.damage_bonus, 4)
        self.assertEqual(stats, original)

    def test_factory_rejects_missing_extra_out_of_range_and_non_integer_stats(self):
        valid = dict.fromkeys(ABILITY_NAMES, 10)
        invalid = [
            {"strength": 10},
            {**valid, "luck": 10},
            {**valid, "dexterity": 2},
            {**valid, "intelligence": 19},
            {**valid, "wisdom": True},
            {**valid, "charisma": 10.0},
            list(valid.values()),
        ]
        for stats in invalid:
            with self.subTest(stats=stats):
                with self.assertRaises(ValueError):
                    Player.create(stats=stats)

    def test_direct_constructor_keeps_explicit_hp_and_ability_fixtures(self):
        player = Player(class_id="wizard", hp=3, max_hp=31, strength=18, intelligence=17)
        self.assertEqual((player.hp, player.max_hp, player.strength, player.intelligence),
                         (3, 31, 18, 17))
        self.assertEqual(player.spell_slots, {1: 2})
        self.assertEqual((player.second_wind_uses, player.action_surge_available), (0, False))

    def test_class_armor_and_weapon_bonuses_are_independent(self):
        rogue = Player.create(class_id="rogue")
        wizard = Player.create(class_id="wizard")
        wizard.collect_equipment(make_equipment("arcane_staff", 3))
        for player in (rogue, wizard):
            player.armor_bonus = 2
            player.ward_bonus = 1
            player.weapon_bonus = 3
        self.assertEqual((rogue.armor_class, rogue.attack_bonus, rogue.damage_bonus), (18, 8, 6))
        self.assertEqual((wizard.armor_class, wizard.attack_bonus, wizard.damage_bonus), (15, 4, 2))
        wizard.mage_armor_active = True
        self.assertEqual(wizard.armor_class, 18)
        self.assertEqual(wizard.spell_attack_bonus, 8)
        self.assertEqual(wizard.spell_save_dc, 16)

    def test_rogue_expertise_and_sneak_attack_scale_with_level(self):
        rogue = Player.create(class_id="rogue")
        self.assertEqual((rogue.perception_bonus, rogue.stealth_bonus,
                          rogue.sneak_attack_dice_count), (6, 7, 1))
        rogue.gain_xp(900)
        self.assertEqual(rogue.sneak_attack_dice_count, 2)
        rogue.gain_xp(5600)
        self.assertEqual((rogue.perception_bonus, rogue.stealth_bonus,
                          rogue.sneak_attack_dice_count), (8, 9, 3))
        self.assertEqual(Player().sneak_attack_dice_count, 0)

    def test_non_warriors_cannot_use_second_wind_even_if_resource_is_corrupted(self):
        for class_id in ("rogue", "wizard"):
            with self.subTest(class_id=class_id):
                player = Player.create(class_id=class_id)
                player.hp = 1
                player.second_wind_uses = 5
                rng = FixedRolls()
                self.assertEqual(player.max_second_wind_uses, 0)
                self.assertFalse(player.second_wind_available)
                self.assertEqual(player.second_wind(rng), 0)
                self.assertEqual(player.hp, 1)
                self.assertEqual(rng.calls, [])

    def test_class_hit_dice_have_their_correct_sizes(self):
        for class_id, sides in (("fighter", 10), ("rogue", 8), ("wizard", 6)):
            with self.subTest(class_id=class_id):
                player = Player.create(class_id=class_id)
                player.hp = 1
                rng = FixedRolls(2)
                self.assertEqual(player.spend_hit_die(rng), 4)
                self.assertEqual(rng.calls, [(1, sides)])
                self.assertEqual(player.hit_dice_remaining, 0)

    def test_only_wizard_has_spell_slots_and_only_unlocked_slots_can_be_spent(self):
        wizard = Player.create(class_id="wizard")
        self.assertEqual(wizard.max_spell_slots, {1: 2})
        self.assertTrue(wizard.spend_spell_slot(1))
        self.assertTrue(wizard.spend_spell_slot(1))
        self.assertFalse(wizard.spend_spell_slot(1))
        self.assertFalse(wizard.spend_spell_slot(2))
        self.assertFalse(wizard.spend_spell_slot(True))
        wizard.spell_slots[9] = 10
        self.assertFalse(wizard.spend_spell_slot(9))
        for class_id in ("fighter", "rogue"):
            player = Player.create(class_id=class_id)
            self.assertEqual(player.max_spell_slots, {})
            self.assertFalse(player.spend_spell_slot(1))

    def test_spell_casting_cannot_spend_slots_at_zero_hp(self):
        wizard = Player.create(class_id="wizard")
        wizard.hp = 0
        self.assertFalse(wizard.spend_spell_slot(1))
        self.assertEqual(wizard.spell_slots, {1: 2})

    def test_slot_and_inventory_maps_are_not_shared_between_characters(self):
        first = Player.create(class_id="wizard")
        second = Player.create(class_id="wizard")
        first.spend_spell_slot(1)
        first.treasure_inventory.append("sentinel")
        self.assertEqual(second.spell_slots, {1: 2})
        self.assertEqual(second.treasure_inventory, [])
        explicit = {1: 0}
        third = Player(class_id="wizard", spell_slots=explicit)
        third.spell_slots[1] = 1
        self.assertEqual(explicit, {1: 0})

    def test_wizard_leveling_grants_only_new_slots_and_preserves_expenditures(self):
        wizard = Player.create(class_id="wizard")
        wizard.spell_slots[1] = 0
        wizard.arcane_recovery_available = False
        wizard.gain_xp(300)
        self.assertEqual(wizard.spell_slots, {1: 1})
        wizard.spell_slots[1] = 0
        wizard.gain_xp(600)
        self.assertEqual(wizard.spell_slots, {1: 1, 2: 2})
        wizard.spell_slots = {1: 0, 2: 0}
        wizard.gain_xp(1800)
        self.assertEqual(wizard.spell_slots, {1: 0, 2: 1})
        wizard.spell_slots[2] = 0
        wizard.gain_xp(3800)
        self.assertEqual(wizard.spell_slots, {1: 0, 2: 0, 3: 2})
        self.assertFalse(wizard.arcane_recovery_available)

    def test_level_hp_uses_class_fixed_values_without_full_healing(self):
        for class_id, initial_hp, increase in (("fighter", 12, 8),
                                               ("rogue", 10, 7), ("wizard", 8, 6)):
            with self.subTest(class_id=class_id):
                player = Player.create(class_id=class_id)
                player.hp = 1
                player.gain_xp(300)
                self.assertEqual((player.hp, player.max_hp), (1 + increase, initial_hp + increase))
                self.assertEqual(player.hit_dice_remaining, 2)

    def test_low_constitution_wizard_hp_growth_has_a_one_hp_floor(self):
        wizard = Player.create(class_id="wizard", stats=dict.fromkeys(ABILITY_NAMES, 3))
        self.assertEqual(wizard.hp, 2)
        wizard.gain_xp(300)
        self.assertEqual((wizard.hp, wizard.max_hp), (3, 3))
        wizard.hp = 0
        wizard.gain_xp(600)
        self.assertEqual((wizard.hp, wizard.max_hp), (0, 4))

    def test_short_rest_does_not_recover_spell_slots_or_grant_warrior_resources(self):
        for class_id in ("rogue", "wizard"):
            with self.subTest(class_id=class_id):
                player = Player.create(class_id=class_id)
                if class_id == "wizard":
                    player.spend_spell_slot(1)
                before = dict(player.spell_slots)
                player.refresh_short_rest()
                self.assertEqual(player.spell_slots, before)
                self.assertEqual((player.second_wind_uses, player.action_surge_available), (0, False))

    def test_long_rest_refills_wizard_slots_and_clears_mage_armor(self):
        wizard = Player.create(class_id="wizard")
        wizard.gain_xp(6500)
        wizard.spell_slots = {1: 0, 2: 0, 3: 0}
        wizard.arcane_recovery_available = False
        wizard.mage_armor_active = True
        wizard.hp = 1
        wizard.hit_dice_remaining = 0
        wizard.long_rest()
        self.assertEqual(wizard.spell_slots, {1: 4, 2: 3, 3: 2})
        self.assertTrue(wizard.arcane_recovery_available)
        self.assertFalse(wizard.mage_armor_active)
        self.assertEqual((wizard.hp, wizard.hit_dice_remaining), (wizard.max_hp, 5))
        self.assertEqual((wizard.second_wind_uses, wizard.action_surge_available), (0, False))

    def test_arcane_recovery_is_not_wasted_when_nothing_can_be_restored(self):
        wizard = Player.create(class_id="wizard")
        self.assertEqual(wizard.recover_arcane_slots(), {})
        self.assertTrue(wizard.arcane_recovery_available)
        wizard.spend_spell_slot(1)
        self.assertEqual(wizard.recover_arcane_slots(), {1: 1})
        self.assertFalse(wizard.arcane_recovery_available)
        wizard.spend_spell_slot(1)
        self.assertEqual(wizard.recover_arcane_slots(), {})

    def test_arcane_recovery_restores_lowest_slots_first_with_total_level_budget(self):
        wizard = Player.create(class_id="wizard")
        wizard.gain_xp(6500)
        wizard.spell_slots = {1: 2, 2: 1, 3: 0}
        self.assertEqual(wizard.recover_arcane_slots(), {1: 2})
        self.assertEqual(wizard.spell_slots, {1: 4, 2: 1, 3: 0})
        wizard.long_rest()
        wizard.spell_slots = {1: 3, 2: 1, 3: 0}
        self.assertEqual(wizard.recover_arcane_slots(), {1: 1, 2: 1})
        self.assertEqual(wizard.spell_slots, {1: 4, 2: 2, 3: 0})

    def test_arcane_recovery_cannot_restore_third_level_slots(self):
        wizard = Player.create(class_id="wizard")
        wizard.gain_xp(6500)
        wizard.spell_slots[3] = 0
        self.assertEqual(wizard.recover_arcane_slots(), {})
        self.assertTrue(wizard.arcane_recovery_available)
        self.assertEqual(wizard.spell_slots[3], 0)

    def test_magic_item_restores_only_a_missing_first_level_wizard_slot(self):
        wizard = Player.create(class_id="wizard")
        self.assertFalse(wizard.restore_level_one_slot())
        wizard.spend_spell_slot(1)
        self.assertTrue(wizard.restore_level_one_slot())
        self.assertEqual(wizard.spell_slots, {1: 2})
        self.assertFalse(wizard.restore_level_one_slot())
        self.assertFalse(Player.create(class_id="rogue").restore_level_one_slot())
        self.assertFalse(Player().restore_level_one_slot())


if __name__ == "__main__":
    unittest.main()
