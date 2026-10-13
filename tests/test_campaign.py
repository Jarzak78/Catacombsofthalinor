"""Campaign transitions, economy, and device-independent engine contracts."""
import json
import random
import subprocess
import sys
import unittest
from copy import deepcopy
from math import ceil
from pathlib import Path
from tempfile import TemporaryDirectory

from actions import Action
from campaign import sanctuary_dialogue, shop_items
from dungeon import Dungeon
from equipment import equipment_options, make_equipment
from game import Game
from tests.test_game import complete_adventure, ScriptedRandom


class CampaignTests(unittest.TestCase):
    def shop_game(self):
        game = Game(seed=7)
        game.position = game.dungeon.boss_position
        game.room.enemy.hp = 0
        game.floor_cleared = True
        game.handle_command('portal')
        return game

    def test_portal_locked_until_guardian_defeated_and_player_at_portal(self):
        game = Game(seed=7)
        original = game.get_state()
        game.perform(Action('portal'))
        game.perform(Action('descend'))
        game.perform(Action('buy', 'sword'))
        self.assertEqual(game.get_state(), original)
        game.floor_cleared = True
        game.perform(Action('portal'))
        self.assertFalse(game.in_shop)

    def test_vendor_heals_once_and_blocks_dungeon_commands(self):
        game = self.shop_game()
        game.player.hp = 1
        game.handle_command('portal')
        self.assertEqual(game.player.hp, 1)
        original = game.get_state()
        for command in ('north', 'loot', 'attack', 'rest', 'long rest', 'ember'):
            game.handle_command(command)
        self.assertEqual(game.get_state(), original)

    def test_sanctuary_arrival_introduces_mira_and_shows_a_compact_menu(self):
        game = self.shop_game()
        lines = game.handle_command('look')
        self.assertEqual(lines[0], 'Mira: ' + sanctuary_dialogue(1))
        self.assertLessEqual(len(lines), 10)
        for number in range(1, 7):
            self.assertTrue(any(line.startswith(str(number) + '.') for line in lines))
        self.assertFalse(any('Longsword +1' in line for line in lines))
        self.assertEqual(game.handle_command('shop'), game.handle_command('menu'))
        self.assertEqual(game.handle_command('1'), game.handle_command('shop weapons'))
        self.assertEqual(game.handle_command('2'), game.handle_command('shop armor'))
        self.assertEqual(game.handle_command('3'), game.handle_command('shop supplies'))
        self.assertEqual(game.handle_command('4'), game.handle_command('inventory'))

    def test_each_shop_page_has_compact_rows_and_all_items_remain_reachable(self):
        game = self.shop_game()
        state, rng_state = game.get_state(), game.rng.getstate()
        for category in ('weapons', 'boots', 'gloves', 'pants', 'torso', 'helmet', 'supplies'):
            with self.subTest(category=category):
                offers = shop_items(game.floor, game.player.class_id, category)
                rows = []
                for page in range(1, ceil(len(offers) / 8) + 1):
                    lines = game.handle_command(f'shop {category} {page}')
                    page_rows = [line for line in lines
                                 if any(line.startswith(item.id + ':') for item in offers)]
                    self.assertLessEqual(len(page_rows), 8)
                    rows.extend(page_rows)
                    self.assertTrue(all(item.description not in '\n'.join(lines)
                                        for item in offers))
                self.assertEqual({line.split(':', 1)[0] for line in rows},
                                 {item.id for item in offers})
                self.assertEqual(len(rows), len(offers))
        self.assertEqual(game.get_state(), state)
        self.assertEqual(game.rng.getstate(), rng_state)

    def test_shop_examination_by_id_and_name_is_free_and_has_full_mechanics(self):
        game = self.shop_game()
        state, rng_state = game.get_state(), game.rng.getstate()
        self.assertEqual(game.handle_command('examine'),
                         ["Use 'examine <item id or name>'."])
        by_id = game.handle_command('examine greatsword_1')
        self.assertEqual(by_id, game.handle_command('examine Greatsword +1'))
        self.assertIn('2d6', '\n'.join(by_id))
        self.assertIn('cannot use a shield', '\n'.join(by_id))
        self.assertIn('Price: 70 gold | buy greatsword_1', by_id)
        self.assertEqual(game.get_state(), state)
        self.assertEqual(game.rng.getstate(), rng_state)

    def test_inventory_pages_list_owned_gear_without_its_descriptions(self):
        game = Game(seed=7)
        for spec in equipment_options('fighter', 'weapon'):
            game.player.collect_equipment(make_equipment(spec.id, 1), auto_equip=False)
        owned = {item.id: item for item in game.player.equipment_inventory}
        state, rng_state = game.get_state(), game.rng.getstate()
        rows = []
        for page in range(1, ceil(len(owned) / 8) + 1):
            lines = game.handle_command(f'inventory {page}')
            page_rows = [line for line in lines
                         if any(line.startswith(item_id + ':') for item_id in owned)]
            self.assertLessEqual(len(page_rows), 8)
            rows.extend(page_rows)
            self.assertTrue(all(item.description not in '\n'.join(lines)
                                for item in owned.values()))
        self.assertEqual({line.split(':', 1)[0] for line in rows}, set(owned))
        self.assertEqual(len(rows), len(owned))
        detail = game.handle_command('examine longsword_1')
        self.assertIn('Description: ' + owned['longsword_1'].description, detail)
        self.assertEqual(game.get_state(), state)
        self.assertEqual(game.rng.getstate(), rng_state)

    def test_item_examination_cannot_reveal_unowned_shop_gear_in_dungeon(self):
        game = Game(seed=7)
        state, rng_state = game.get_state(), game.rng.getstate()
        lines = game.handle_command('examine greatsword_1')
        self.assertIn('not in your pack', '\n'.join(lines))
        self.assertNotIn('2d6', '\n'.join(lines))
        self.assertEqual(game.get_state(), state)
        self.assertEqual(game.rng.getstate(), rng_state)

    def test_invalid_shop_categories_and_page_numbers_change_no_state(self):
        game = self.shop_game()
        state, rng_state = game.get_state(), game.rng.getstate()
        for command in ('shop weapons 0', 'shop weapons 999', 'shop weapons bad',
                        'shop weapons 1 extra', 'shop unknown', 'inventory 0',
                        'inventory 999', 'inventory bad', 'examine nonexistent'):
            with self.subTest(command=command):
                self.assertTrue(game.handle_command(command))
                self.assertEqual(game.get_state(), state)
                self.assertEqual(game.rng.getstate(), rng_state)

    def test_portal_rest_restores_spent_resources(self):
        game = Game(seed=7)
        game.position = game.dungeon.boss_position
        game.room.enemy.hp = 0
        game.floor_cleared = True
        game.player.hp = 1
        game.player.potions = 0
        game.player.second_wind_uses = 0
        game.player.hit_dice_remaining = 0
        game.handle_command('portal')
        self.assertEqual(game.player.hp, game.player.max_hp)
        self.assertEqual(game.player.second_wind_uses, 2)
        self.assertEqual(game.player.hit_dice_remaining, 1)
        self.assertEqual(game.player.potions, 0)

    def test_purchases_deduct_gold_and_equip_or_supply_items(self):
        game = self.shop_game()
        game.player.gold = 300
        for item in ('sword', 'armor', 'charm', 'ward', 'potion', 'ember'):
            game.perform(Action('buy', item))
        self.assertEqual(game.player.gold, 70)
        self.assertEqual(game.player.weapon_bonus, 1)
        self.assertEqual(game.player.equipped_weapon.id, 'longsword_1')
        self.assertEqual(game.player.equipped_armor.id, 'chain_mail_1')
        self.assertEqual(game.player.armor_class, 20)
        self.assertEqual(game.player.max_hp, 16)
        self.assertEqual(game.player.potions, 4)
        self.assertEqual(game.player.ember_stones, 1)

    def test_rejected_purchases_never_charge_or_downgrade(self):
        game = self.shop_game()
        original = game.get_state()
        game.handle_command('buy sword')
        game.handle_command('buy nonexistent')
        self.assertEqual(game.get_state(), original)
        game.player.gold = 1000
        for item in ('sword', 'armor', 'charm', 'ward'):
            game.handle_command('buy ' + item)
        original = game.get_state()
        for item in ('sword', 'armor', 'charm', 'ward'):
            game.handle_command('buy ' + item)
        self.assertEqual(game.get_state(), original)

    def test_descent_preserves_character_and_replaces_floor_state(self):
        game = self.shop_game()
        game.player.gold = 500
        game.handle_command('buy sword')
        player = deepcopy(game.player)
        dungeon = game.dungeon
        game.handle_command('descend')
        self.assertEqual(game.floor, 2)
        self.assertEqual(game.player, player)
        self.assertIsNot(game.dungeon, dungeon)
        self.assertEqual(game.position, game.dungeon.start)
        self.assertIsNone(game.previous_position)
        self.assertFalse(game.in_shop)
        self.assertFalse(game.floor_cleared)
        self.assertEqual(sum(r.visited for r in game.dungeon.rooms.values()), 1)
        game.handle_command('portal')
        self.assertFalse(game.in_shop)

    def test_final_portal_finishes_only_after_leaving_shop(self):
        game = self.shop_game()
        game.total_floors = 1
        self.assertFalse(game.over)
        game.handle_command('descend')
        self.assertTrue(game.won)
        state = game.get_state()
        game.perform(Action('buy', 'potion'))
        self.assertEqual(game.get_state(), state)

    def test_each_floor_has_strictly_tougher_guardian(self):
        previous = None
        for floor in range(1, 6):
            dungeon = Dungeon(random.Random(7), floor=floor)
            guardian = dungeon.get_room(dungeon.boss_position).enemy
            stats = (guardian.hp, guardian.armor_class, guardian.attack_bonus,
                     guardian.damage_bonus, guardian.xp_reward, guardian.gold_reward)
            if previous:
                self.assertTrue(all(a > b for a, b in zip(stats, previous)))
            previous = stats
            self.assertEqual(len(dungeon.rooms), 12)

    def test_invalid_campaign_lengths_are_rejected(self):
        for floors in (0, 6):
            with self.assertRaises(ValueError):
                Game(floors=floors)

    def test_ember_consumes_one_action_and_item_without_sap(self):
        game = Game(seed=7)
        game.position = game.dungeon.boss_position
        game.player.ember_stones = 1
        game.rng = ScriptedRandom([3, 4, 5])
        hp = game.enemy.hp
        game.handle_command('ember')
        self.assertEqual(game.enemy.hp, hp - 12)
        self.assertEqual(game.actions_remaining, 0)
        self.assertEqual(game.player.ember_stones, 0)
        self.assertFalse(game.enemy_sapped)
        state = game.get_state()
        game.handle_command('ember')
        self.assertEqual(game.get_state(), state)

    def test_extra_attack_shares_one_action_and_surges_allow_another_pair(self):
        game = Game(seed=7)
        game.position = game.dungeon.boss_position
        game.enemy.hp = game.enemy.max_hp = 200
        game.player.gain_xp(6500)
        game.rng = ScriptedRandom([15, 4] * 4)
        game.perform(Action('attack'))
        self.assertEqual(game.enemy.hp, 182)
        self.assertEqual(game.actions_remaining, 0)
        game.perform(Action('action surge'))
        game.perform(Action('attack'))
        self.assertEqual(game.enemy.hp, 164)
        self.assertEqual(game.actions_remaining, 0)

    def test_snapshots_are_detached_serializable_and_hide_unexplored_content(self):
        game = Game(seed=7)
        state = game.get_state()
        json.dumps(state)
        self.assertTrue(all(set(room) == {'position', 'visited'}
                            for room in state['rooms'] if not room['visited']))
        state['player']['gold'] = 1000000
        state['rooms'][0]['exits'].clear()
        self.assertEqual(game.player.gold, 0)
        self.assertTrue(game.room.exits)
        game.get_state()
        reference = Game(seed=7)
        self.assertEqual(game.rng.getstate(), reference.rng.getstate())

    def test_structured_actions_and_terminal_commands_have_identical_results(self):
        text_game, ui_game = Game(seed=7), Game(seed=7)
        for command, action in [('stats', Action('stats')), ('rest 0', Action('rest', '0')),
                                ('east', Action('east')), ('quit', Action('quit'))]:
            self.assertEqual(text_game.handle_command(command), ui_game.perform(action))
            self.assertEqual(text_game.get_state(), ui_game.get_state())

    def test_complete_five_floor_campaigns_use_real_combat_and_shopping(self):
        for seed in (0, 7, 42):
            with self.subTest(seed=seed):
                game, commands, transcript = complete_adventure(seed, floors=5)
                self.assertTrue(game.won, '\n'.join(transcript[-20:]))
                self.assertEqual(game.floor, 5)
                self.assertEqual(commands.count('portal'), 5)
                self.assertEqual(commands.count('descend'), 5)
                self.assertGreaterEqual(game.player.level, 5)
                self.assertEqual(game.player.weapon_bonus, 3)

    def test_real_cli_completes_default_campaign_from_another_directory(self):
        game, commands, _ = complete_adventure(7, floors=5)
        self.assertTrue(game.won)
        launcher = Path(__file__).resolve().parents[1] / 'Main.py'
        with TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, str(launcher), '--quick-start', '--name', 'Tarin', '--seed', '7'],
                                    cwd=directory, input='\n'.join(commands)+'\n', text=True,
                                    capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertIn('Your first dungeon is conquered', result.stdout)
        self.assertIn('Floor 5/5', result.stdout)


if __name__ == '__main__':
    unittest.main()
