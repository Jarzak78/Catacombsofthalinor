"""Equipment choices, ownership, and real inventory/shop command boundaries."""

from dataclasses import asdict
import unittest

from actions import Action
from campaign import preferred_item_id
from equipment import equipment_price, make_equipment
from game import Game
from loot_library import Loot, TreasureItem
from player import Player
from room import Enemy


def equipment_game(class_id="fighter", *, shop=False):
    game = Game(seed=7, class_id=class_id)
    game.room.enemy = None
    game.room.note = None
    game.room.loot = None
    game.room.looted = False
    game.in_shop = shop
    return game


def budget(game):
    return (game.elapsed_minutes, game.actions_remaining,
            game.bonus_action_available, game.rng.getstate())


class WeaponRolls:
    def __init__(self, *values):
        self.values = iter(values)
        self.calls = []

    def randint(self, low, high):
        self.calls.append((low, high))
        value = next(self.values)
        if not low <= value <= high:
            raise AssertionError(f"Roll {value} outside {low}..{high}")
        return value


class EquipmentPlayerTests(unittest.TestCase):
    def test_each_class_owns_its_starting_mundane_weapon_and_armor(self):
        for class_id, weapon, armor, ac in (
            ("fighter", "longsword", "chain_mail", 18),
            ("rogue", "rapier", "studded_leather", 15),
            ("wizard", "quarterstaff", "robes", 12),
        ):
            with self.subTest(class_id=class_id):
                player = Player.create(class_id=class_id)
                self.assertEqual((player.weapon_id, player.armor_id), (weapon, armor))
                self.assertEqual(player.armor_class, ac)
                self.assertEqual(len(player.equipment_inventory), 2)
                self.assertTrue(all(item.bonus == 0 for item in player.equipment_inventory))
                self.assertTrue(player.is_equipped(player.equipped_weapon))
                self.assertTrue(player.is_equipped(player.equipped_armor))

    def test_two_handed_weapon_is_a_manual_shield_and_dueling_tradeoff(self):
        player = Player.create()
        greatsword = make_equipment("greatsword", 1)
        self.assertFalse(player.collect_equipment(greatsword))
        self.assertEqual(player.weapon_id, "longsword")
        self.assertTrue(player.equip_equipment(greatsword))
        self.assertEqual((player.weapon_dice, player.armor_class, player.damage_bonus),
                         ((2, 6), 16, 4))
        starter = next(item for item in player.equipment_inventory
                       if item.base_id == "longsword")
        self.assertTrue(player.equip_equipment(starter))
        self.assertEqual((player.weapon_dice, player.armor_class, player.damage_bonus),
                         ((1, 8), 18, 5))

    def test_same_weapon_enchantment_auto_equips_without_discarding_old_copy(self):
        player = Player.create()
        starter = player.equipped_weapon
        upgrade = make_equipment("longsword", 2)
        self.assertTrue(player.collect_equipment(upgrade))
        self.assertIs(player.equipped_weapon, upgrade)
        self.assertIn(starter, player.equipment_inventory)
        self.assertIn(starter, player.sellable_equipment())

    def test_auto_equipping_does_not_exchange_or_remove_weapon_mastery(self):
        for class_id, alternative in (("fighter", "battleaxe"),
                                      ("fighter", "rapier"),
                                      ("rogue", "dagger")):
            with self.subTest(class_id=class_id, alternative=alternative):
                player = Player.create(class_id=class_id)
                original = player.equipped_weapon
                candidate = make_equipment(alternative, 3)
                self.assertFalse(player.collect_equipment(candidate))
                self.assertIs(player.equipped_weapon, original)
                self.assertTrue(player.equip_equipment(candidate))
                self.assertEqual(player.weapon_mastery, candidate.spec.mastery)

    def test_finesse_uses_the_higher_strength_or_dexterity_for_any_class(self):
        for class_id in ("fighter", "rogue", "wizard"):
            with self.subTest(class_id=class_id):
                player = Player.create(class_id=class_id)
                dagger = make_equipment("dagger", 1)
                player.collect_equipment(dagger, auto_equip=False)
                self.assertTrue(player.equip_equipment(dagger))
                player.strength, player.dexterity = 18, 12
                self.assertEqual((player.weapon_ability, player.attack_bonus), ("strength", 7))
                player.strength, player.dexterity = 10, 20
                self.assertEqual((player.weapon_ability, player.attack_bonus), ("dexterity", 8))

    def test_light_medium_and_heavy_armor_apply_their_dexterity_rules(self):
        player = Player.create()
        for armor_id, dexterity, expected in (
            ("leather", 20, 18),
            ("scale_mail", 20, 18),
            ("scale_mail", 6, 14),
            ("chain_mail", 6, 18),
            ("plate", 20, 20),
        ):
            with self.subTest(armor_id=armor_id, dexterity=dexterity):
                player.dexterity = dexterity
                candidate = make_equipment(armor_id)
                player.collect_equipment(candidate, auto_equip=False)
                player.equip_equipment(candidate)
                self.assertEqual(player.armor_class, expected)

    def test_armor_upgrade_avoids_new_stealth_disadvantage(self):
        player = Player.create(class_id="rogue")
        padded = make_equipment("padded", 3)
        self.assertFalse(player.collect_equipment(padded))
        self.assertFalse(player.stealth_disadvantage)
        self.assertTrue(player.equip_equipment(padded))
        self.assertTrue(player.stealth_disadvantage)
        self.assertEqual(player.armor_class, 17)

    def test_only_arcane_staff_enchantment_improves_wizard_spells(self):
        player = Player.create(class_id="wizard")
        spell_bonus, spell_dc = player.spell_attack_bonus, player.spell_save_dc
        quarterstaff = make_equipment("quarterstaff", 2)
        self.assertTrue(player.collect_equipment(quarterstaff))
        self.assertEqual((player.focus_bonus, player.spell_attack_bonus, player.spell_save_dc),
                         (0, spell_bonus, spell_dc))
        focus = make_equipment("arcane_staff", 2)
        self.assertTrue(player.collect_equipment(focus))
        self.assertEqual((player.spell_attack_bonus, player.spell_save_dc),
                         (spell_bonus + 2, spell_dc + 2))
        dagger = make_equipment("dagger", 3)
        self.assertFalse(player.collect_equipment(dagger))
        self.assertIs(player.equipped_weapon, focus)

    def test_mage_armor_improves_clothing_base_before_enchantment_and_ward(self):
        player = Player.create(class_id="wizard")
        robes = make_equipment("battlemage_robes", 2)
        self.assertTrue(player.collect_equipment(robes))
        player.ward_bonus = 1
        self.assertEqual(player.armor_class, 17)
        player.mage_armor_active = True
        self.assertEqual(player.armor_class, 18)

    def test_mage_armor_cannot_auto_equip_a_post_rest_armor_downgrade(self):
        player = Player.create(class_id="wizard")
        original = make_equipment("battlemage_robes", 1)
        self.assertTrue(player.collect_equipment(original))
        self.assertEqual(player.armor_class, 15)
        player.mage_armor_active = True
        self.assertEqual(player.armor_class, 16)
        apparent_upgrade = make_equipment("robes", 2)
        self.assertFalse(player.collect_equipment(apparent_upgrade))
        self.assertIs(player.equipped_armor, original)
        self.assertEqual(player.armor_class, 16)
        self.assertIn(apparent_upgrade, player.equipment_inventory)
        player.long_rest()
        self.assertEqual(player.armor_class, 15)
        # Choosing the tradeoff manually remains possible.
        self.assertTrue(player.equip_equipment(apparent_upgrade))
        self.assertEqual(player.armor_class, 14)

    def test_armor_auto_upgrade_is_safe_with_and_without_mage_armor(self):
        player = Player.create(class_id="wizard")
        player.mage_armor_active = True
        robes = make_equipment("battlemage_robes", 1)
        self.assertTrue(player.collect_equipment(robes))
        self.assertEqual(player.armor_class, 16)
        player.long_rest()
        self.assertEqual(player.armor_class, 15)
        player.mage_armor_active = True
        better = make_equipment("battlemage_robes", 2)
        self.assertTrue(player.collect_equipment(better))
        self.assertEqual(player.armor_class, 17)
        player.long_rest()
        self.assertEqual(player.armor_class, 16)

    def test_base_robes_upgrade_is_safe_when_mage_armor_masks_its_current_gain(self):
        player = Player.create(class_id="wizard")
        player.mage_armor_active = True
        before = player.armor_class
        robes = make_equipment("warded_robes")
        self.assertTrue(player.collect_equipment(robes))
        self.assertEqual(player.armor_class, before)
        player.long_rest()
        self.assertEqual(player.armor_class, 13)

    def test_wrong_class_gear_is_retained_but_cannot_be_equipped(self):
        player = Player.create(class_id="wizard")
        plate = make_equipment("plate", 3)
        self.assertFalse(player.collect_equipment(plate))
        self.assertIn(plate, player.equipment_inventory)
        self.assertFalse(player.can_equip(plate))
        self.assertFalse(player.equip_equipment(plate))

    def test_equip_requires_an_owned_copy_and_guards_duplicate_identity(self):
        player = Player.create()
        unowned = make_equipment("longsword", 1)
        before = asdict(player)
        self.assertFalse(player.equip_equipment(unowned))
        self.assertEqual(asdict(player), before)
        self.assertTrue(player.collect_equipment(unowned))
        self.assertFalse(player.collect_equipment(unowned))
        self.assertEqual(sum(item is unowned for item in player.equipment_inventory), 1)
        duplicate = make_equipment("longsword", 1)
        self.assertFalse(player.collect_equipment(duplicate))
        self.assertTrue(player.is_equipped(unowned))
        self.assertFalse(player.is_equipped(duplicate))
        self.assertIn(duplicate, player.sellable_equipment())

    def test_dead_player_cannot_collect_equip_or_use_legacy_upgrade_helper(self):
        for death in ("zero hp", "dead flag"):
            with self.subTest(death=death):
                player = Player.create()
                item = make_equipment("greatsword", 3)
                player.collect_equipment(item, auto_equip=False)
                if death == "zero hp":
                    player.hp = 0
                else:
                    player.dead = True
                before = asdict(player)
                self.assertFalse(player.collect_equipment(make_equipment("plate", 3)))
                self.assertFalse(player.equip_equipment(item))
                self.assertFalse(player.equip_weapon("Longsword +3", 3))
                self.assertEqual(asdict(player), before)

    def test_invalid_starting_equipment_slots_and_legacy_over_cap_are_rejected(self):
        for fields in ({"weapon_id": "chain_mail"}, {"armor_id": "longsword"},
                       {"weapon_id": "arcane_staff"}):
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):
                    Player(**fields)
        player = Player.create()
        before = asdict(player)
        self.assertFalse(player.equip_weapon("Longsword +4", 4))
        self.assertEqual(asdict(player), before)

    def test_characters_do_not_share_default_or_explicit_inventory_lists(self):
        first, second = Player.create(), Player.create()
        first.collect_equipment(make_equipment("longsword", 1))
        self.assertEqual(len(first.equipment_inventory), 3)
        self.assertEqual(len(second.equipment_inventory), 2)
        supplied = [make_equipment("greatsword")]
        player = Player(equipment_inventory=supplied)
        self.assertEqual(len(supplied), 1)
        self.assertEqual(len(player.equipment_inventory), 3)


class EquipmentActionTests(unittest.TestCase):
    def assert_pure(self, game, command):
        before, resources = game.get_state(), budget(game)
        game.handle_command(command)
        self.assertEqual(game.get_state(), before)
        self.assertEqual(budget(game), resources)

    def test_explicit_equip_by_id_and_display_name_is_free_in_safe_rooms(self):
        game = equipment_game()
        greatsword = make_equipment("greatsword", 1)
        game.player.collect_equipment(greatsword, auto_equip=False)
        resources = budget(game)
        game.perform(Action("equip", "greatsword_1"))
        self.assertIs(game.player.equipped_weapon, greatsword)
        self.assertEqual(game.player.armor_class, 16)
        self.assertEqual(budget(game), resources)
        game.handle_command("equip Longsword")
        self.assertEqual(game.player.weapon_id, "longsword")
        game.handle_command("equip Greatsword +1")
        self.assertIs(game.player.equipped_weapon, greatsword)
        self.assertEqual(budget(game), resources)

    def test_equip_is_free_at_vendor_and_allows_intentional_downgrade(self):
        game = equipment_game(shop=True)
        starter = game.player.equipped_weapon
        upgrade = make_equipment("longsword", 3)
        game.player.collect_equipment(upgrade)
        resources = budget(game)
        game.handle_command("equip longsword")
        self.assertIs(game.player.equipped_weapon, starter)
        self.assertEqual(game.player.weapon_bonus, 0)
        self.assertEqual(budget(game), resources)

    def test_equip_cannot_change_gear_in_combat_even_with_unspent_actions(self):
        game = equipment_game()
        item = make_equipment("greatsword", 2)
        game.player.collect_equipment(item, auto_equip=False)
        game.room.enemy = Enemy("Guard", 100, 100, 12, 3, (1, 6), 1, 50, 0)
        game.enemy_unaware = True
        game.opening_hide_available = True
        self.assert_pure(game, "equip greatsword_2")

    def test_invalid_unowned_incompatible_or_dead_equip_does_not_change_state(self):
        game = equipment_game("wizard")
        item = make_equipment("plate", 3)
        game.player.collect_equipment(item, auto_equip=False)
        for command in ("equip", "equip missing_item", "equip longsword_3", "equip plate_3"):
            with self.subTest(command=command):
                self.assert_pure(game, command)
        game.player.hp = 0
        self.assert_pure(game, "equip quarterstaff")

    def test_buy_accepts_same_enchantment_on_a_different_weapon_type(self):
        game = equipment_game(shop=True)
        game.player.gold = 1000
        game.handle_command("buy longsword_1")
        before = game.player.gold
        resources = budget(game)
        game.handle_command("buy battleaxe_1")
        axe = make_equipment("battleaxe", 1)
        self.assertIn(axe, game.player.equipment_inventory)
        self.assertEqual(game.player.gold, before - equipment_price(axe))
        self.assertEqual(budget(game), resources)
        self.assert_pure(game, "buy battleaxe_1")

    def test_buy_legacy_shortcuts_and_full_item_names_resolve_supported_gear(self):
        for class_id in ("fighter", "rogue", "wizard"):
            with self.subTest(class_id=class_id):
                game = equipment_game(class_id, shop=True)
                game.player.gold = 1000
                game.handle_command("buy weapon")
                expected = preferred_item_id(1, class_id, "weapon")
                self.assertTrue(any(item.id == expected for item in game.player.equipment_inventory))
                game.handle_command("buy armor")
                armor_id = preferred_item_id(1, class_id, "armor")
                self.assertTrue(any(item.id == armor_id for item in game.player.equipment_inventory))
        game = equipment_game(shop=True)
        game.player.gold = 1000
        game.handle_command("buy Greatsword +1")
        self.assertIn(make_equipment("greatsword", 1), game.player.equipment_inventory)

    def test_every_shop_supply_can_be_bought_by_its_full_display_name(self):
        supplies = (
            ("Healing potion", "potions", 1, 12),
            ("Vitality charm", "max_hp", 4, 35),
            ("Warding ring", "ward_bonus", 1, 65),
            ("Ember stone", "ember_stones", 1, 18),
        )
        for class_id in ("fighter", "rogue", "wizard"):
            for name, attribute, increase, price in supplies:
                with self.subTest(class_id=class_id, name=name):
                    game = equipment_game(class_id, shop=True)
                    game.player.gold = 1000
                    previous = getattr(game.player, attribute)
                    resources = budget(game)
                    game.handle_command("buy " + name)
                    self.assertEqual(getattr(game.player, attribute), previous + increase)
                    self.assertEqual(game.player.gold, 1000 - price)
                    self.assertEqual(budget(game), resources)
        game = equipment_game("wizard", shop=True)
        game.player.gold = 1000
        resources = budget(game)
        game.handle_command("buy Mana draught")
        self.assertEqual((game.player.mana_draughts, game.player.gold), (1, 982))
        self.assertEqual(budget(game), resources)

    def test_display_name_purchases_charge_each_consumable_and_block_unique_duplicates(self):
        game = equipment_game(shop=True)
        game.player.gold = 1000
        game.handle_command("buy potion")
        game.handle_command("buy HEALING   POTION")
        self.assertEqual((game.player.potions, game.player.gold), (5, 976))
        for name in ("Vitality charm", "Warding ring", "Longsword +1"):
            with self.subTest(name=name):
                game.handle_command("buy " + name)
                self.assert_pure(game, "buy " + name.upper())
        for command in ("buy Healing potionn", "buy Unknown magic ring"):
            with self.subTest(command=command):
                self.assert_pure(game, command)

    def test_invalid_buy_wrong_class_unavailable_tier_or_insufficient_gold_is_pure(self):
        game = equipment_game("rogue", shop=True)
        game.player.gold = 1000
        for command in ("buy missing_item", "buy greatsword", "buy rapier_3", "buy rapier"):
            with self.subTest(command=command):
                self.assert_pure(game, command)
        game.player.gold = 0
        self.assert_pure(game, "buy shortsword_1")
        game.player.hp = 0
        self.assert_pure(game, "buy potion")

    def test_sale_protects_one_equipped_copy_and_sells_its_duplicate_for_half_price(self):
        game = equipment_game(shop=True)
        equipped = game.player.equipped_weapon
        duplicate = make_equipment("longsword")
        game.player.collect_equipment(duplicate)
        resources = budget(game)
        game.handle_command("sell longsword")
        self.assertEqual(game.player.gold, duplicate.sale_value)
        self.assertTrue(any(item is equipped for item in game.player.equipment_inventory))
        self.assertFalse(any(item is duplicate for item in game.player.equipment_inventory))
        self.assertIs(game.player.equipped_weapon, equipped)
        self.assertEqual(budget(game), resources)
        self.assert_pure(game, "sell longsword")

    def test_sell_all_sells_pack_and_valuables_without_stripping_equipped_gear(self):
        game = equipment_game("rogue", shop=True)
        weapon, armor = game.player.equipped_weapon, game.player.equipped_armor
        plate = make_equipment("plate", 2)
        dagger = make_equipment("dagger")
        game.player.collect_equipment(plate)
        game.player.collect_equipment(dagger)
        game.player.treasure_inventory = [TreasureItem(
            "test_gem", "Emerald", "A green stone.", 7, "valuable", 2)]
        resources = budget(game)
        game.handle_command("sell all")
        self.assertEqual(game.player.gold, plate.sale_value + dagger.sale_value + 14)
        self.assertEqual(len(game.player.equipment_inventory), 2)
        self.assertIs(game.player.equipped_weapon, weapon)
        self.assertIs(game.player.equipped_armor, armor)
        self.assertEqual(game.player.treasure_inventory, [])
        self.assertEqual(budget(game), resources)
        self.assert_pure(game, "sell all")

    def test_sell_is_vendor_only_and_unknown_or_dead_sales_are_pure(self):
        game = equipment_game()
        game.player.collect_equipment(make_equipment("battleaxe", 1))
        self.assert_pure(game, "sell battleaxe_1")
        game.in_shop = True
        self.assert_pure(game, "sell missing_item")
        game.player.hp = 0
        self.assert_pure(game, "sell all")

    def test_gems_and_jewelry_sell_by_full_display_names_without_repeat_gold(self):
        game = equipment_game(shop=True)
        gem = TreasureItem("test_emerald", "Moss emerald", "A green stone.", 7, "valuable", 2)
        jewel = TreasureItem("test_ring", "Engraved silver ring", "A fine silver ring.", 9, "valuable")
        game.player.treasure_inventory = [gem, jewel]
        resources = budget(game)
        game.handle_command("sell MOSS   EMERALD")
        self.assertEqual(game.player.gold, 14)
        self.assertEqual(game.player.treasure_inventory, [jewel])
        self.assert_pure(game, "sell Moss emerald")
        game.handle_command("sell Engraved silver ring")
        self.assertEqual(game.player.gold, 23)
        self.assertEqual(game.player.treasure_inventory, [])
        self.assertEqual(len(game.player.equipment_inventory), 2)
        self.assertEqual(budget(game), resources)
        self.assert_pure(game, "sell Engraved silver ring")

    def test_new_equipment_loot_is_claimed_once_and_keeps_tradeoffs_in_the_pack(self):
        game = equipment_game()
        sword = make_equipment("longsword", 1)
        axe = make_equipment("greataxe", 2)
        inferior = make_equipment("leather")
        game.room.loot = Loot(gold=15, equipment=(sword, axe, inferior))
        resources = budget(game)
        output = "\n".join(game.handle_command("loot"))
        self.assertIs(game.player.equipped_weapon, sword)
        self.assertTrue(any(item is axe for item in game.player.equipment_inventory))
        self.assertTrue(any(item is inferior for item in game.player.equipment_inventory))
        self.assertEqual(game.player.gold, 15)
        self.assertTrue(game.room.looted)
        self.assertEqual(budget(game), resources)
        for name in (sword.name, axe.name, inferior.name):
            self.assertIn(name, output)
        self.assert_pure(game, "loot")

    def test_inventory_and_detached_snapshots_expose_stable_ids_and_equipped_status(self):
        game = equipment_game()
        greatsword = make_equipment("greatsword", 2)
        game.player.collect_equipment(greatsword)
        resources = budget(game)
        state = game.get_state()
        inventory = state["player"]["equipment_inventory"]
        self.assertEqual({item["id"] for item in inventory},
                         {"longsword", "chain_mail", "greatsword_2"})
        self.assertEqual(sum(item["equipped"] for item in inventory), 2)
        inventory.clear()
        self.assertEqual(len(game.player.equipment_inventory), 3)
        display = "\n".join(game.handle_command("inventory"))
        self.assertIn("greatsword_2", display)
        self.assertIn("Greatsword +2", display)
        self.assertEqual(budget(game), resources)
        self.assert_pure(game, "inventory")

    def test_real_weapon_attack_uses_greatsword_dice_without_shield_or_dueling(self):
        game = equipment_game()
        greatsword = make_equipment("greatsword")
        game.player.collect_equipment(greatsword)
        game.handle_command("equip greatsword")
        enemy = Enemy("Guard", 100, 100, 12, 3, (1, 6), 1, 50, 0)
        game.room.enemy = enemy
        rolls = WeaponRolls(10, 2, 3)
        game.rng = rolls
        game.handle_command("strike")
        self.assertEqual(rolls.calls, [(1, 20), (1, 6), (1, 6)])
        self.assertEqual(enemy.hp, 92)
        self.assertEqual(game.player.armor_class, 16)
        self.assertFalse(game.enemy_sapped)

    def test_fighter_rapier_applies_vex_instead_of_longsword_sap(self):
        game = equipment_game()
        rapier = make_equipment("rapier")
        game.player.collect_equipment(rapier)
        game.handle_command("equip rapier")
        enemy = Enemy("Guard", 100, 100, 12, 3, (1, 6), 1, 50, 0)
        game.room.enemy = enemy
        rolls = WeaponRolls(10, 3, 4, 15, 2)
        game.rng = rolls
        game.handle_command("strike")
        self.assertTrue(game.rogue_vex)
        self.assertFalse(game.enemy_sapped)
        game.begin_turn()
        game.handle_command("strike")
        self.assertEqual(rolls.calls, [(1, 20), (1, 8), (1, 20), (1, 20), (1, 8)])
        self.assertEqual(enemy.hp, 85)

    def test_rogue_dagger_still_delivers_sneak_attack_without_granting_vex(self):
        game = equipment_game("rogue")
        dagger = make_equipment("dagger")
        game.player.collect_equipment(dagger)
        game.handle_command("equip dagger")
        enemy = Enemy("Guard", 100, 100, 12, 3, (1, 6), 1, 50, 0)
        game.room.enemy = enemy
        game.hidden = True
        rolls = WeaponRolls(10, 12, 3, 4)
        game.rng = rolls
        output = "\n".join(game.handle_command("strike"))
        self.assertEqual(rolls.calls, [(1, 20), (1, 20), (1, 4), (1, 6)])
        self.assertEqual(enemy.hp, 90)
        self.assertTrue(game.sneak_attack_used)
        self.assertFalse(game.rogue_vex)
        self.assertIn("Sneak Attack", output)

    def test_padded_armor_makes_actual_rogue_hide_check_roll_at_disadvantage(self):
        game = equipment_game("rogue")
        padded = make_equipment("padded", 3)
        game.player.collect_equipment(padded)
        game.handle_command("equip padded_3")
        game.room.enemy = Enemy("Guard", 100, 100, 12, 3, (1, 6), 1, 50, 0)
        rolls = WeaponRolls(19, 2)
        game.rng = rolls
        game.handle_command("hide")
        self.assertEqual(rolls.calls, [(1, 20), (1, 20)])
        self.assertFalse(game.hidden)
        self.assertEqual(game.actions_remaining, 0)
        self.assertTrue(game.bonus_action_available)


if __name__ == "__main__":
    unittest.main()
