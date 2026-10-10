"""Floor descriptions and chapter reveals follow campaign progression."""
import random
import unittest
from dungeon import Dungeon
from floor_lore import LORE
from game import Game

class FloorLoreTests(unittest.TestCase):
    def test_every_floor_has_distinct_complete_room_content(self):
        names, descriptions = set(), set()
        for floor in range(1, 6):
            dungeon = Dungeon(random.Random(7), floor=floor)
            self.assertEqual(len(LORE[floor - 1].rooms), 10)
            self.assertEqual(len(dungeon.rooms), 12)
            for room in dungeon.rooms.values():
                self.assertNotIn(room.name, names)
                self.assertNotIn(room.description, descriptions)
                names.add(room.name)
                descriptions.add(room.description)
                self.assertTrue(room.name.strip())
                self.assertTrue(room.description.strip())

    def test_descent_announces_next_chapter_and_hides_its_revelation(self):
        game = Game(seed=7)
        for floor in range(1, 5):
            game.position = game.dungeon.boss_position
            enemy = game.enemy
            enemy.hp = 0
            text = game.defeat_enemy(enemy)
            self.assertIn(LORE[floor - 1].revelation, text)
            self.assertEqual(game.get_state()['story']['revelation'], LORE[floor - 1].revelation)
            game.handle_command('portal')
            text = game.handle_command('descend')
            self.assertIn(LORE[floor].arrival, text)
            self.assertIn(LORE[floor].entrance[1], text)
            self.assertEqual(game.get_state()['story']['arrival'], LORE[floor].arrival)
            self.assertIsNone(game.get_state()['story']['revelation'])

if __name__ == '__main__':
    unittest.main()
