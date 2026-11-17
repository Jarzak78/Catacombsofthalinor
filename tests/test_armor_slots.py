"""Actual worn copies, ensemble protection, and temporary magical effects."""

from dataclasses import asdict
import unittest

from equipment import ARMOR_SLOTS, DEFAULT_ARMOR_PIECES, make_equipment
from player import Player


def piece(player, slot, bonus=0, affix=""):
    return make_equipment(DEFAULT_ARMOR_PIECES[player.class_id][slot], bonus, affix)


def wear(player, item):
    player.collect_equipment(item, auto_equip=False)
    return player.equip_equipment(item)


class ArmorSlotTests(unittest.TestCase):
    def test_starters_fill_five_independent_slots_without_inflating_ac(self):
        for class_id, ac in (("fighter", 18), ("rogue", 15), ("wizard", 12)):
            with self.subTest(class_id=class_id):
                player = Player.create(class_id=class_id)
                self.assertEqual(set(player.equipped_armor_slots), set(ARMOR_SLOTS))
                self.assertEqual(len(player.equipment_inventory), 6)
                self.assertEqual(player.armor_class, ac)
                self.assertEqual(player.combined_armor_bonus, 0)
                for slot, item in player.equipped_armor_slots.items():
                    self.assertEqual(item.slot, slot)
                    self.assertTrue(any(item is owned for owned in player.equipment_inventory))
                    self.assertTrue(player.is_equipped(item))

    def test_boot_upgrade_does_not_replace_the_torso_or_other_slots(self):
        player = Player.create()
        before = player.equipped_armor_slots
        torso = player.equipped_armor
        boots = piece(player, "boots", 1)
        self.assertTrue(player.collect_equipment(boots))
        self.assertIs(player.equipped_armor_slots["boots"], boots)
        self.assertIs(player.equipped_armor, torso)
        self.assertEqual((player.armor_id, player.armor_bonus), (torso.base_id, 0))
        self.assertEqual((player.combined_armor_bonus, player.armor_class), (1, 19))
        for slot in ("gloves", "pants", "torso", "helmet"):
            self.assertIs(player.equipped_armor_slots[slot], before[slot])

    def test_all_five_enchantments_share_the_three_point_ac_cap(self):
        for class_id, ac in (("fighter", 18), ("rogue", 15), ("wizard", 12)):
            with self.subTest(class_id=class_id):
                player = Player.create(class_id=class_id)
                for slot in ARMOR_SLOTS:
                    self.assertTrue(wear(player, piece(player, slot, 3)))
                self.assertEqual(sum(item.bonus for item in player.equipped_armor_slots.values()), 15)
                self.assertEqual(player.combined_armor_bonus, 3)
                self.assertEqual(player.armor_class, ac + 3)

    def test_equipped_copy_protection_applies_to_every_slot_and_weapon(self):
        player = Player.create()
        starters = (player.equipped_weapon, *player.equipped_armor_slots.values())
        duplicates = [make_equipment(item.base_id) for item in starters]
        for duplicate in duplicates:
            self.assertFalse(player.collect_equipment(duplicate))
        self.assertEqual(len(player.sellable_equipment()), 6)
        for original, duplicate in zip(starters, duplicates):
            self.assertTrue(player.is_equipped(original))
            self.assertFalse(player.is_equipped(duplicate))
            self.assertTrue(any(item is duplicate for item in player.sellable_equipment()))

    def test_returned_slot_mapping_cannot_replace_owned_pieces(self):
        player = Player.create()
        original = player.equipped_armor_slots["boots"]
        returned = player.equipped_armor_slots
        returned["boots"] = piece(player, "boots", 3)
        returned.clear()
        self.assertIs(player.equipped_armor_slots["boots"], original)
        self.assertEqual(player.combined_armor_bonus, 0)

    def test_characters_never_share_slot_containers_or_default_owned_copies(self):
        first, second = Player.create(), Player.create()
        self.assertTrue(wear(first, piece(first, "helmet", 2)))
        self.assertEqual((first.combined_armor_bonus, second.combined_armor_bonus), (2, 0))
        for slot in ARMOR_SLOTS:
            self.assertIsNot(first.equipped_armor_slots[slot], second.equipped_armor_slots[slot])

    def test_wrong_class_and_unowned_accessories_cannot_be_equipped(self):
        wizard = Player.create(class_id="wizard")
        incompatible = make_equipment("mail_boots", 3)
        self.assertFalse(wizard.collect_equipment(incompatible))
        self.assertFalse(wizard.can_equip(incompatible))
        self.assertFalse(wizard.equip_equipment(incompatible))
        self.assertFalse(wizard.equip_equipment(piece(wizard, "boots", 3)))
        self.assertEqual(wizard.combined_armor_bonus, 0)

    def test_starting_torso_slot_rejects_a_boot_even_when_class_compatible(self):
        with self.assertRaises(ValueError):
            Player(armor_id="mail_boots")

    def test_plain_accessories_do_not_override_torso_dexterity_limits(self):
        player = Player.create()
        player.dexterity = 20
        for slot in ("boots", "gloves", "pants", "helmet"):
            self.assertTrue(wear(player, make_equipment(f"leather_{slot}")))
        self.assertEqual(player.armor_class, 18)
        self.assertTrue(wear(player, make_equipment("breastplate")))
        self.assertEqual(player.armor_class, 18)
        player.dexterity = 6
        self.assertEqual(player.armor_class, 14)

    def test_legacy_torso_bonus_still_contributes_to_ensemble_cap(self):
        player = Player.create()
        player.armor_bonus = 2
        self.assertTrue(wear(player, piece(player, "gloves", 2)))
        self.assertEqual((player.combined_armor_bonus, player.armor_class), (3, 21))

    def test_dead_characters_cannot_change_slots_or_gain_equipment_effects(self):
        for death in ("zero_hp", "dead_flag"):
            with self.subTest(death=death):
                player = Player.create()
                boots = piece(player, "boots", 3, "might")
                player.collect_equipment(boots, auto_equip=False)
                if death == "zero_hp":
                    player.hp = 0
                else:
                    player.dead = True
                slots, state = player.equipped_armor_slots, asdict(player)
                self.assertFalse(player.equip_equipment(boots))
                self.assertFalse(player.collect_equipment(piece(player, "helmet", 2, "agility")))
                self.assertEqual(player.equipped_armor_slots, slots)
                self.assertEqual(asdict(player), state)
                self.assertEqual(player.equipment_buffs, {})


class ArmorEffectTests(unittest.TestCase):
    def test_strength_magic_changes_attacks_without_rewriting_starting_stats(self):
        player = Player.create()
        attack, damage = player.attack_bonus, player.damage_bonus
        self.assertTrue(player.collect_equipment(piece(player, "gloves", 3, "might")))
        self.assertEqual((player.strength, player.effective_strength), (16, 19))
        self.assertEqual(player.strength_modifier, 4)
        self.assertEqual((player.attack_bonus, player.damage_bonus), (attack + 1, damage + 1))
        self.assertEqual(player.equipment_buffs, {"strength": 3})

    def test_dexterity_magic_affects_finesse_initiative_and_uncapped_light_ac(self):
        player = Player.create(class_id="rogue")
        player.strength, player.dexterity = 16, 14
        before = player.attack_bonus, player.initiative_bonus, player.armor_class
        self.assertEqual(player.weapon_ability, "strength")
        self.assertTrue(wear(player, piece(player, "boots", 3, "agility")))
        self.assertEqual((player.weapon_ability, player.effective_dexterity), ("dexterity", 17))
        self.assertEqual(player.attack_bonus, before[0])
        self.assertEqual(player.initiative_bonus, before[1] + 1)
        self.assertEqual(player.armor_class, before[2] + 4)

    def test_intelligence_magic_changes_spell_attack_and_save_dc(self):
        wizard = Player.create(class_id="wizard")
        before = wizard.spell_attack_bonus, wizard.spell_save_dc
        self.assertTrue(wizard.collect_equipment(piece(wizard, "helmet", 2, "intellect")))
        self.assertEqual((wizard.intelligence, wizard.effective_intelligence), (16, 18))
        self.assertEqual((wizard.spell_attack_bonus, wizard.spell_save_dc),
                         (before[0] + 1, before[1] + 1))

    def test_wisdom_and_skill_effects_work_with_rogue_expertise(self):
        rogue = Player.create(class_id="rogue")
        perception, stealth = rogue.perception_bonus, rogue.stealth_bonus
        self.assertTrue(wear(rogue, piece(rogue, "helmet", 2, "insight")))
        self.assertTrue(wear(rogue, piece(rogue, "gloves", 3, "vigilance")))
        self.assertTrue(wear(rogue, piece(rogue, "boots", 2, "shadow")))
        self.assertEqual(rogue.perception_bonus, perception + 1 + 3)
        self.assertEqual(rogue.stealth_bonus, stealth + 2)
        self.assertEqual(rogue.equipment_buffs,
                         {"wisdom": 2, "perception": 3, "stealth": 2})

    def test_matching_effects_use_the_best_piece_and_recalculate_when_replaced(self):
        rogue = Player.create(class_id="rogue")
        self.assertTrue(wear(rogue, piece(rogue, "boots", 2, "shadow")))
        self.assertTrue(wear(rogue, piece(rogue, "helmet", 3, "shadow")))
        self.assertEqual(rogue.equipment_buffs, {"stealth": 3})
        self.assertEqual(rogue.stealth_bonus, 10)
        self.assertTrue(wear(rogue, piece(rogue, "helmet", 3)))
        self.assertEqual(rogue.equipment_buffs, {"stealth": 2})
        self.assertEqual(rogue.stealth_bonus, 9)

    def test_unequipped_affixes_do_nothing_and_effects_leave_with_the_piece(self):
        rogue = Player.create(class_id="rogue")
        original = rogue.equipped_armor_slots["boots"]
        enchanted = piece(rogue, "boots", 2, "agility")
        rogue.collect_equipment(enchanted, auto_equip=False)
        self.assertEqual(rogue.equipment_buffs, {})
        self.assertTrue(rogue.equip_equipment(enchanted))
        self.assertEqual(rogue.effective_dexterity, 18)
        self.assertTrue(rogue.equip_equipment(original))
        self.assertEqual(rogue.effective_dexterity, 16)
        self.assertEqual(rogue.equipment_buffs, {})
        self.assertTrue(any(item is enchanted for item in rogue.sellable_equipment()))

    def test_ability_score_cap_does_not_change_hp_constitution_or_base_scores(self):
        player = Player.create()
        player.dexterity = 19
        hp = player.hp, player.max_hp, player.constitution
        self.assertTrue(wear(player, piece(player, "boots", 3, "agility")))
        self.assertTrue(wear(player, piece(player, "helmet", 3, "agility")))
        self.assertEqual((player.dexterity, player.effective_dexterity), (19, 20))
        self.assertEqual(player.dexterity_modifier, 5)
        self.assertEqual((player.hp, player.max_hp, player.constitution), hp)
        self.assertEqual(player.effective_abilities["constitution"], player.constitution)

    def test_charisma_effects_and_all_returned_effect_maps_are_detached(self):
        player = Player.create()
        self.assertTrue(wear(player, piece(player, "helmet", 3, "presence")))
        self.assertEqual((player.charisma, player.effective_charisma, player.charisma_modifier),
                         (10, 13, 1))
        returned = player.equipment_buffs
        returned["charisma"] = 100
        abilities = player.effective_abilities
        abilities["charisma"] = 100
        self.assertEqual(player.effective_charisma, 13)

    def test_equipping_magic_never_refreshes_health_or_class_resources(self):
        wizard = Player.create(class_id="wizard")
        wizard.hp -= 2
        wizard.spell_slots[1] = 0
        wizard.hit_dice_remaining = 0
        wizard.arcane_recovery_available = False
        before = (wizard.hp, wizard.max_hp, dict(wizard.spell_slots),
                  wizard.hit_dice_remaining, wizard.arcane_recovery_available)
        self.assertTrue(wizard.collect_equipment(piece(wizard, "helmet", 3, "intellect")))
        self.assertEqual((wizard.hp, wizard.max_hp, wizard.spell_slots,
                          wizard.hit_dice_remaining, wizard.arcane_recovery_available), before)

    def test_armor_auto_equipping_refuses_to_remove_a_useful_affix(self):
        player = Player.create()
        original = piece(player, "helmet", 1, "insight")
        self.assertTrue(player.collect_equipment(original))
        stronger_plain = piece(player, "helmet", 3)
        self.assertFalse(player.collect_equipment(stronger_plain))
        self.assertIs(player.equipped_armor_slots["helmet"], original)
        self.assertEqual(player.equipment_buffs, {"wisdom": 1})
        self.assertTrue(player.equip_equipment(stronger_plain))
        self.assertEqual(player.equipment_buffs, {})

    def test_same_enchantment_can_auto_equip_if_it_adds_an_effect_without_a_tradeoff(self):
        rogue = Player.create(class_id="rogue")
        self.assertTrue(rogue.collect_equipment(piece(rogue, "gloves", 2)))
        utility = piece(rogue, "gloves", 2, "vigilance")
        self.assertTrue(rogue.collect_equipment(utility))
        self.assertIs(rogue.equipped_armor_slots["gloves"], utility)
        self.assertEqual(rogue.equipment_buffs, {"perception": 2})

    def test_capped_armor_enchantment_alone_does_not_auto_replace_equivalent_piece(self):
        player = Player.create()
        self.assertTrue(player.collect_equipment(piece(player, "boots", 3)))
        helmet = piece(player, "helmet", 1)
        self.assertFalse(player.collect_equipment(helmet))
        self.assertEqual(player.equipped_armor_slots["helmet"].bonus, 0)
        self.assertTrue(player.equip_equipment(helmet))
        self.assertEqual((player.combined_armor_bonus, player.armor_class), (3, 21))

    def test_mage_armor_and_accessory_buffs_recalculate_safely_after_long_rest(self):
        wizard = Player.create(class_id="wizard")
        self.assertTrue(wear(wizard, make_equipment("battlemage_robes", 1)))
        self.assertTrue(wear(wizard, piece(wizard, "boots", 2, "agility")))
        wizard.mage_armor_active = True
        self.assertEqual(wizard.armor_class, 19)
        apparent_upgrade = make_equipment("robes", 3)
        self.assertFalse(wizard.collect_equipment(apparent_upgrade))
        wizard.long_rest()
        self.assertEqual(wizard.armor_class, 18)
        self.assertEqual(wizard.equipment_buffs, {"dexterity": 2})
        self.assertEqual(wizard.equipped_armor.base_id, "battlemage_robes")


if __name__ == "__main__":
    unittest.main()
