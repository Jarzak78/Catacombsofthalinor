"""Five-slot equipment, inspected effects, and conditional armor affix rolls."""

from collections import Counter, deque
from dataclasses import FrozenInstanceError
import random
import unittest

from equipment import (
    ARMOR_SLOTS, DEFAULT_ARMOR, DEFAULT_ARMOR_PIECES, EQUIPMENT,
    EquipmentSpec, armor_affix_options, equipment_options, equipment_price,
    make_equipment, resolve_equipment_id,
)
from loot_library import roll_equipment


class EquipmentRolls:
    def __init__(self, random_rolls, enchantment_roll):
        self.random_rolls = deque(random_rolls)
        self.enchantment_roll = enchantment_roll
        self.choices = []

    def random(self):
        return self.random_rolls.popleft()

    def choice(self, options):
        self.choices.append(tuple(options))
        return options[0]

    def randrange(self, limit):
        if not 0 <= self.enchantment_roll < limit:
            raise AssertionError("Enchantment roll outside its range")
        return self.enchantment_roll


class FiveSlotCatalogTests(unittest.TestCase):
    def test_every_class_has_mundane_starting_pieces_and_options_in_all_five_slots(self):
        self.assertEqual(set(ARMOR_SLOTS), {"boots", "gloves", "pants", "torso", "helmet"})
        for class_id in ("fighter", "rogue", "wizard"):
            with self.subTest(class_id=class_id):
                defaults = DEFAULT_ARMOR_PIECES[class_id]
                self.assertEqual(set(defaults), set(ARMOR_SLOTS))
                self.assertEqual(defaults["torso"], DEFAULT_ARMOR[class_id])
                armor = equipment_options(class_id, "armor")
                self.assertEqual({spec.slot for spec in armor}, set(ARMOR_SLOTS))
                for slot, base_id in defaults.items():
                    item = make_equipment(base_id)
                    self.assertEqual((item.slot, item.kind, item.bonus, item.affix),
                                     (slot, "armor", 0, ""))
                    self.assertIn(class_id, item.spec.classes)

    def test_accessories_do_not_supply_a_second_torso_armor_profile(self):
        for spec in EQUIPMENT.values():
            with self.subTest(item=spec.id):
                if spec.kind == "armor" and spec.slot != "torso":
                    self.assertEqual(spec.base_ac, 0)
                    self.assertIsNone(spec.dex_cap)
                    self.assertFalse(spec.stealth_disadvantage)
                    self.assertIn("no separate base AC", make_equipment(spec.id).description)
                elif spec.kind == "weapon":
                    self.assertEqual(spec.slot, "weapon")

    def test_kind_and_slot_mismatches_are_rejected(self):
        for kind, slot in (("weapon", "boots"), ("armor", "weapon"),
                           ("armor", "ring"), ("armor", [])):
            with self.subTest(kind=kind, slot=slot):
                with self.assertRaises(ValueError):
                    EquipmentSpec("example", "Example", kind, ("fighter",), 5,
                                  "A test piece.", slot=slot)

    def test_item_descriptions_explain_real_gear_materials_and_tradeoffs(self):
        for spec in EQUIPMENT.values():
            with self.subTest(item=spec.id):
                self.assertGreaterEqual(len(spec.description), 100)
                description = make_equipment(spec.id, 1).description
                self.assertIn(f"Slot: {spec.slot}", description)
                if spec.kind == "weapon":
                    self.assertIn(f"{spec.damage_dice[0]}d{spec.damage_dice[1]}", description)
                else:
                    self.assertIn("capped at +3 across all five slots", description)
        self.assertIn("cannot use a shield", make_equipment("greatsword").description)
        self.assertIn("Dexterity does not alter", make_equipment("chain_mail").description)
        self.assertIn("maximum +2", make_equipment("scale_mail").description)
        self.assertIn("spell save DC", make_equipment("arcane_staff", 1).description)
        self.assertIn("not spells", make_equipment("quarterstaff", 1).description)


class ArmorAffixTests(unittest.TestCase):
    examples = (
        ("mail_gloves", "might", "strength"),
        ("leather_boots", "agility", "dexterity"),
        ("cloth_helmet", "insight", "wisdom"),
        ("robes", "intellect", "intelligence"),
        ("leather_pants", "presence", "charisma"),
        ("leather_gloves", "shadow", "stealth"),
        ("mail_helmet", "vigilance", "perception"),
    )

    def test_affix_effect_magnitude_equals_gear_enchantment_and_effects_are_detached(self):
        for base_id, affix, target in self.examples:
            for bonus in (1, 2, 3):
                with self.subTest(base_id=base_id, affix=affix, bonus=bonus):
                    item = make_equipment(base_id, bonus, affix)
                    self.assertEqual(item.buffs, {target: bonus})
                    buffs = item.buffs
                    buffs[target] = 99
                    self.assertEqual(item.buffs, {target: bonus})
                    self.assertNotIn("constitution", item.buffs)
                    self.assertIn("strongest equipped bonus", item.description)
                    if target in ("stealth", "perception"):
                        self.assertIn(f"+{bonus} to {target.title()} checks", item.description)
                    else:
                        self.assertIn(f"+{bonus} to your {target.title()} score", item.description)
                        self.assertIn("up to a score of 20", item.description)
                    with self.assertRaises(FrozenInstanceError):
                        item.affix = ""

    def test_affixes_require_enchanted_compatible_armor(self):
        for fields in (("longsword", 1, "might"), ("mail_gloves", 0, "might"),
                       ("cloth_boots", 1, "might"), ("mail_helmet", 1, "intellect"),
                       ("leather_boots", 1, "unknown"), ("robes", 1, None)):
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):
                    make_equipment(*fields)
        self.assertEqual(make_equipment("longsword", 3).buffs, {})
        self.assertEqual(make_equipment("leather_boots").buffs, {})

    def test_affix_names_and_ids_roundtrip_without_accepting_unavailable_items(self):
        for base_id, affix, _ in self.examples:
            for bonus in (1, 2, 3):
                with self.subTest(base_id=base_id, affix=affix, bonus=bonus):
                    item = make_equipment(base_id, bonus, affix)
                    self.assertEqual(resolve_equipment_id(item.id.upper()), item.id)
                    self.assertEqual(resolve_equipment_id(item.name), item.id)
                    self.assertEqual(resolve_equipment_id("  " + item.name.replace(" ", "  ") + "  "), item.id)
        for unknown in ("longsword_1_might", "robes of Intellect", "mail_helmet_1_intellect",
                        "leather_boots_4_agility", "leather_boots_1_unknown"):
            with self.subTest(unknown=unknown):
                self.assertIsNone(resolve_equipment_id(unknown))
        self.assertEqual(resolve_equipment_id("leather +1"), "leather_1")
        self.assertEqual(resolve_equipment_id("Longsword +3"), "longsword_3")

    def test_affix_price_premium_is_paid_and_recovered_equipment_sells_for_half(self):
        for bonus in (1, 2, 3):
            plain = make_equipment("leather_boots", bonus)
            affixed = make_equipment("leather_boots", bonus, "agility")
            self.assertEqual(equipment_price(affixed) - equipment_price(plain), 15 * bonus)
            self.assertEqual(affixed.sale_value, equipment_price(affixed) // 2)

    def test_each_magical_armor_tier_has_its_exact_conditional_affix_boundary(self):
        for bonus, enchantment_roll, chance in ((1, 15000, .20), (2, 55000, .30), (3, 90000, .40)):
            for draw, succeeds in ((chance - .000001, True), (chance, False)):
                with self.subTest(bonus=bonus, draw=draw):
                    rng = EquipmentRolls([.5, draw], enchantment_roll)
                    item = roll_equipment(rng, 5, "fighter")
                    self.assertEqual(item.bonus, bonus)
                    self.assertEqual(bool(item.affix), succeeds)
                    self.assertEqual(item.slot, "boots")
                    self.assertEqual(len(rng.choices), 3 if succeeds else 2)
                    self.assertFalse(rng.random_rolls)

    def test_weapons_and_mundane_armor_do_not_roll_for_affixes(self):
        for kind_roll, enchantment_roll in ((.0, 99999), (.5, 0)):
            with self.subTest(kind_roll=kind_roll):
                rng = EquipmentRolls([kind_roll], enchantment_roll)
                item = roll_equipment(rng, 1, "rogue")
                self.assertEqual(item.affix, "")
                self.assertFalse(rng.random_rolls)

    def test_armor_slots_are_equally_likely_despite_more_torso_base_types(self):
        rng = random.Random(58901)
        counts = Counter()
        for _ in range(15000):
            item = roll_equipment(rng, 4, "fighter")
            if item.kind == "armor":
                counts[item.slot] += 1
        self.assertEqual(set(counts), set(ARMOR_SLOTS))
        for slot, count in counts.items():
            with self.subTest(slot=slot):
                self.assertAlmostEqual(count / sum(counts.values()), .20, delta=.02)

    def test_random_affixes_suit_the_class_and_never_exceed_plus_three(self):
        for class_id in ("fighter", "rogue", "wizard"):
            rng = random.Random(f"buffs: {class_id}")
            found = set()
            for _ in range(2500):
                item = roll_equipment(rng, 5, class_id)
                self.assertIn(class_id, item.spec.classes)
                self.assertLessEqual(item.bonus, 3)
                if item.affix:
                    self.assertEqual(item.kind, "armor")
                    self.assertIn(item.affix, armor_affix_options(class_id))
                    found.add(item.affix)
            self.assertEqual(found, set(armor_affix_options(class_id)))


if __name__ == "__main__":
    unittest.main()
