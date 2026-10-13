"""Treasure collection, equipment upgrades, resale, and usable trinkets."""

from dataclasses import replace
import json
import unittest

from actions import Action
from equipment import make_equipment
from game import Game
from loot_library import Loot, TreasureItem, ember_stone, mana_draught
from lore_notes import LoreNote
from room import Enemy


class NoTreasureRolls:
    def randint(self, low, high):
        raise AssertionError(f"Treasure inspection must not roll {low}..{high}")


def treasure_game(class_id="fighter", loot=None):
    game = Game(seed=7, class_id=class_id)
    game.room.enemy = None
    game.room.note = None
    game.room.loot = loot
    game.room.looted = False
    game.rng = NoTreasureRolls()
    return game


def test_gem(amount=1):
    return TreasureItem("test_gem", "Secret emerald", "A green crystal in a silver setting.",
                        11, "valuable", amount)


def test_jewel(amount=1):
    return TreasureItem("test_jewel", "Secret diadem", "A jeweled band of ancient gold.",
                        17, "valuable", amount)


class TreasureActionTests(unittest.TestCase):
    def assert_command_pure(self, game, command):
        before, clock = game.get_state(), game.elapsed_minutes
        game.handle_command(command)
        self.assertEqual(game.get_state(), before)
        self.assertEqual(game.elapsed_minutes, clock)

    def test_rich_cache_collects_each_kind_once_without_time_or_turn_cost(self):
        loot = Loot(gold=21, potions=2,
                    equipment=(make_equipment("arcane_staff", 2), make_equipment("robes", 3)),
                    items=(test_gem(2), replace(ember_stone(), amount=3),
                           replace(mana_draught(), amount=2)))
        game = treasure_game("wizard", loot)
        resources = (game.actions_remaining, game.bonus_action_available, game.elapsed_minutes)
        output = "\n".join(game.handle_command("loot"))
        self.assertEqual((game.player.gold, game.player.potions), (21, 5))
        self.assertEqual((game.player.weapon_bonus, game.player.armor_bonus), (2, 3))
        self.assertEqual((game.player.ember_stones, game.player.mana_draughts), (3, 2))
        self.assertEqual(game.player.treasure_inventory, [test_gem(2)])
        self.assertEqual((game.actions_remaining, game.bonus_action_available,
                          game.elapsed_minutes), resources)
        for detail in ("21 gold", "2 healing", "Arcane Staff +2", "Robes +3",
                       "Secret emerald x2", "Ember stone x3", "Mana draught x2"):
            self.assertIn(detail, output)
        self.assertTrue(game.room.looted)
        self.assert_command_pure(game, "loot")

    def test_gems_from_separate_rooms_stack_and_sell_for_the_full_stack(self):
        game = treasure_game(loot=Loot(items=(test_gem(2),)))
        game.handle_command("loot")
        direction, position = next(iter(game.room.exits.items()))
        destination = game.dungeon.get_room(position)
        destination.enemy = None
        destination.note = None
        destination.loot = Loot(items=(test_gem(3),))
        destination.looted = False
        game.handle_command(direction)
        game.handle_command("loot")
        self.assertEqual(game.player.treasure_inventory, [test_gem(5)])
        game.in_shop = True
        game.handle_command("sell test_gem")
        self.assertEqual(game.player.gold, 55)
        self.assertEqual(game.player.treasure_inventory, [])
        self.assert_command_pure(game, "sell test_gem")

    def test_selling_one_id_leaves_other_valuables_and_sell_all_cannot_repeat(self):
        game = treasure_game(loot=Loot(items=(test_gem(2), test_jewel(3))))
        game.handle_command("loot")
        game.in_shop = True
        game.perform(Action("sell", "test_gem"))
        self.assertEqual(game.player.gold, 22)
        self.assertEqual(game.player.treasure_inventory, [test_jewel(3)])
        game.handle_command("sell all")
        self.assertEqual(game.player.gold, 73)
        self.assertEqual(game.player.treasure_inventory, [])
        self.assert_command_pure(game, "sell all")

    def test_selling_is_shop_only_and_unknown_id_is_pure(self):
        game = treasure_game(loot=Loot(items=(test_gem(2),)))
        game.handle_command("loot")
        self.assert_command_pure(game, "sell all")
        game.in_shop = True
        self.assert_command_pure(game, "sell missing_gem")
        game.player.hp = 0
        self.assert_command_pure(game, "sell all")

    def test_collection_guards_leave_every_reward_and_note_unclaimed(self):
        for reason in ("live foe", "shop", "zero HP", "dead"):
            with self.subTest(reason=reason):
                game = treasure_game("wizard", Loot(
                    gold=17, potions=2,
                    equipment=(make_equipment("arcane_staff", 3), make_equipment("robes", 2)),
                    items=(test_gem(), ember_stone(), mana_draught())))
                game.room.note = LoreNote("test-note", 1, game.room.name,
                                          "Hidden account", "A forgotten story.", "Keep looking.")
                if reason == "live foe":
                    game.room.enemy = Enemy("Sentry", 10, 10, 12, 3, (1, 6), 1, 50, 7)
                elif reason == "shop":
                    game.in_shop = True
                elif reason == "zero HP":
                    game.player.hp = 0
                else:
                    game.player.dead = True
                self.assert_command_pure(game, "loot")
                self.assertFalse(game.room.looted)
                self.assertFalse(game.room.note_collected)

    def test_equipment_only_cache_is_visible_but_exact_identity_waits_for_loot(self):
        game = treasure_game("rogue", Loot(
            equipment=(make_equipment("rapier", 3), make_equipment("leather", 2))))
        before = game.get_state()
        look = "\n".join(game.handle_command("look"))
        self.assertIn("loot", look.lower())
        self.assertNotIn("Rapier", look)
        self.assertNotIn("Leather Armor", look)
        self.assertNotIn("+3", look)
        self.assertNotIn("+2", look)
        self.assertEqual(game.get_state(), before)
        receipt = "\n".join(game.handle_command("loot"))
        self.assertIn("Rapier +3", receipt)
        self.assertIn("Leather Armor +2", receipt)
        self.assertEqual((game.player.weapon_bonus, game.player.armor_bonus), (3, 2))
        self.assertNotIn("Type 'loot' to search", "\n".join(game.handle_command("look")))

    def test_valuable_only_cache_hides_names_counts_and_values_until_collection(self):
        game = treasure_game(loot=Loot(items=(test_gem(37), test_jewel(29))))
        self.assert_command_pure(game, "look")
        look = "\n".join(game.handle_command("look"))
        self.assertIn("loot", look.lower())
        self.assertNotIn("Secret emerald", look)
        self.assertNotIn("Secret diadem", look)
        self.assertNotIn("x37", look)
        self.assertNotIn("x29", look)
        game.handle_command("loot")
        self.assertEqual(game.player.treasure_inventory, [test_gem(37), test_jewel(29)])

    def test_weaker_and_equal_equipment_is_described_without_downgrading(self):
        for bonus in (1, 3):
            with self.subTest(bonus=bonus):
                game = treasure_game(loot=Loot(
                    equipment=(make_equipment("longsword", bonus),
                               make_equipment("chain_mail", bonus))))
                game.player.collect_equipment(make_equipment("longsword", 3))
                game.player.collect_equipment(make_equipment("chain_mail", 3))
                equipped_weapon = game.player._equipped_weapon_item
                equipped_armor = game.player._equipped_armor_item
                worn = game.player.equipped_armor_slots
                previously_owned = tuple(game.player.equipment_inventory)
                found_copies = game.room.loot.equipment
                output = "\n".join(game.handle_command("loot"))
                self.assertIn(f"Longsword +{bonus}", output)
                self.assertIn(f"Chain Mail +{bonus}", output)
                self.assertEqual(game.player.weapon_name, "Longsword +3")
                self.assertEqual((game.player.weapon_bonus, game.player.armor_bonus), (3, 3))
                self.assertIs(game.player._equipped_weapon_item, equipped_weapon)
                self.assertIs(game.player._equipped_armor_item, equipped_armor)
                self.assertEqual(len(game.player.equipment_inventory), 10)
                for item in (*previously_owned, *found_copies):
                    self.assertTrue(any(item is owned for owned in game.player.equipment_inventory))
                for slot, item in worn.items():
                    self.assertIs(game.player.equipped_armor_slots[slot], item)
                    self.assertTrue(game.player.is_equipped(item))
                self.assertTrue(all(not game.player.is_equipped(item) for item in found_copies))
                if bonus == 3:
                    for equipped, found in zip((equipped_weapon, equipped_armor), found_copies):
                        self.assertEqual(equipped, found)
                        self.assertIsNot(equipped, found)
                        self.assertEqual(sum(item.id == found.id
                                             for item in game.player.equipment_inventory), 2)
                self.assertTrue(game.room.looted)
                self.assert_command_pure(game, "loot")

    def test_new_note_can_be_collected_after_treasure_without_repeating_rewards(self):
        game = treasure_game(loot=Loot(gold=17, items=(test_gem(2),)))
        game.handle_command("loot")
        game.room.note = LoreNote("later-note", 1, game.room.name,
                                  "Last account", "The story continues.", "Descend carefully.")
        game.handle_command("loot")
        self.assertEqual(game.player.gold, 17)
        self.assertEqual(game.player.treasure_inventory, [test_gem(2)])
        self.assertEqual(len(game.journal), 1)
        self.assertTrue(game.room.note_collected)
        self.assert_command_pure(game, "loot")

    def test_nonwizard_mana_draught_is_a_sellable_find(self):
        for class_id in ("fighter", "rogue"):
            with self.subTest(class_id=class_id):
                item = replace(mana_draught(), amount=2)
                game = treasure_game(class_id, Loot(items=(item,)))
                game.handle_command("loot")
                self.assertEqual(game.player.mana_draughts, 0)
                self.assertEqual(game.player.treasure_inventory, [item])
                self.assert_command_pure(game, "mana")
                game.in_shop = True
                game.handle_command("sell mana")
                self.assertEqual(game.player.gold, 18)
                self.assertEqual(game.player.treasure_inventory, [])

    def test_wizard_mana_restores_one_slot_with_bonus_cost_and_no_rng(self):
        game = treasure_game("wizard", Loot(items=(replace(mana_draught(), amount=2),)))
        game.handle_command("loot")
        game.room.enemy = Enemy("Sentry", 10, 10, 12, 3, (1, 6), 1, 50, 7)
        game.player.spell_slots[1] = 0
        game.free_examine_available = True
        game.handle_command("mana")
        self.assertEqual(game.player.spell_slots[1], 1)
        self.assertEqual(game.player.mana_draughts, 1)
        self.assertFalse(game.bonus_action_available)
        self.assertEqual(game.actions_remaining, 1)
        self.assertTrue(game.free_examine_available)
        self.assert_command_pure(game, "mana")

    def test_full_slots_missing_draught_and_wrong_class_do_not_spend_bonus(self):
        for reason in ("full slots", "no draught", "wrong class"):
            with self.subTest(reason=reason):
                game = treasure_game("fighter" if reason == "wrong class" else "wizard")
                game.room.enemy = Enemy("Sentry", 10, 10, 12, 3, (1, 6), 1, 50, 7)
                game.player.mana_draughts = 0 if reason == "no draught" else 2
                if reason == "no draught":
                    game.player.spell_slots[1] = 0
                self.assert_command_pure(game, "mana")

    def test_carried_inventory_snapshot_is_detached_and_json_serializable(self):
        game = treasure_game(loot=Loot(items=(test_gem(2),)))
        game.handle_command("loot")
        snapshot = game.get_state()
        json.dumps(snapshot)
        snapshot["player"]["treasure_inventory"][0]["amount"] = 1000
        snapshot["player"]["treasure_inventory"].append({"id": "fake"})
        self.assertEqual(game.player.treasure_inventory, [test_gem(2)])
        output = "\n".join(game.handle_command("inventory"))
        self.assertIn("test_gem", output)
        self.assertIn("Secret emerald x2", output)
        self.assertIn("11 gold each", output)
        self.assertNotIn(test_gem().description, output)
        examined = "\n".join(game.handle_command("examine Secret emerald"))
        self.assertIn(test_gem().description, examined)
        self.assertIn("Sell value: 11 gold each", examined)
        self.assert_command_pure(game, "examine test_gem")


if __name__ == "__main__":
    unittest.main()
