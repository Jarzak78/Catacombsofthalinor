"""Discoverable story notes, persistent journals, and renderer-safe snapshots."""

from dataclasses import asdict
import json
from pathlib import Path
import random
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from actions import Action
from dungeon import Dungeon
from floor_lore import LORE
from game import Game
from lore_notes import NOTES
from loot_library import Loot
from room import Enemy
from tests.test_game import complete_adventure


ROOT = Path(__file__).resolve().parents[1]


def room_with_note(game, ordinary=False):
    """Find a placed note without depending on its randomized coordinates."""
    return next(room for room in game.dungeon.rooms.values()
                if room.note and (not ordinary or room.position not in
                                  (game.dungeon.start, game.dungeon.boss_position)))


def collect_safely(game, room):
    game.position = room.position
    room.visited = True
    if room.enemy:
        room.enemy.hp = 0
    return game.handle_command('loot')


class NotePlacementTests(unittest.TestCase):
    def test_twenty_unique_notes_are_placed_in_their_story_rooms_on_every_seed(self):
        self.assertEqual(set(NOTES), set(range(1, 6)))
        ids = set()
        for floor, notes in NOTES.items():
            self.assertEqual(len(notes), 4)
            lore = LORE[floor - 1]
            valid_names = {lore.entrance[0], lore.sanctum[0],
                           *(name for name, _ in lore.rooms)}
            self.assertIn(lore.entrance[0], {note.room_name for note in notes})
            self.assertIn(lore.sanctum[0], {note.room_name for note in notes})
            self.assertEqual(len({note.room_name for note in notes}), 4)
            for note in notes:
                self.assertEqual(note.floor, floor)
                self.assertIn(note.room_name, valid_names)
                self.assertRegex(note.id, r'^[a-z0-9_-]+$')
                self.assertNotIn(note.id, ids)
                ids.add(note.id)
                for value in (note.title, note.text, note.hint):
                    self.assertTrue(value.strip())
            for seed in (0, 7, 42):
                with self.subTest(floor=floor, seed=seed):
                    dungeon = Dungeon(random.Random(seed), floor=floor)
                    placed = {room.note.id: room for room in dungeon.rooms.values()
                              if room.note}
                    self.assertEqual(set(placed), {note.id for note in notes})
                    for note in notes:
                        self.assertEqual(placed[note.id].name, note.room_name)
                        self.assertEqual(placed[note.id].note, note)
                        self.assertFalse(placed[note.id].note_collected)
        self.assertEqual(len(ids), 20)

    def test_note_placement_preserves_existing_dungeon_random_sequence(self):
        # Captured from the existing seed-7 generator before adding story notes.
        for floor in range(1, 6):
            rng = random.Random(7)
            Dungeon(rng, floor=floor)
            self.assertEqual([rng.randrange(1_000_000) for _ in range(3)],
                             [669949, 196997, 390487])

    def test_map_note_marker_preserves_unknown_enemy_and_treasure_priority(self):
        game = Game(seed=7)
        room = room_with_note(game, ordinary=True)
        room.enemy = None
        room.loot = None

        def marker():
            x, y = room.position
            return game.dungeon.map_lines(game.position)[y * 2][x * 4]

        self.assertEqual(marker(), '?')
        room.visited = True
        self.assertEqual(marker(), 'N')
        room.enemy = Enemy('Note guard', 2, 2, 10, 0, (1, 4), 0, 0, 0)
        self.assertEqual(marker(), 'E')
        room.enemy.hp = 0
        room.loot = Loot(gold=3)
        self.assertEqual(marker(), '$')
        room.looted = True
        self.assertEqual(marker(), 'N')
        room.note_collected = True
        self.assertEqual(marker(), '.')
        game.position = room.position
        self.assertEqual(marker(), '@')


class NoteLootTests(unittest.TestCase):
    def test_entrance_note_is_hintable_collectible_and_can_be_read_without_gold(self):
        game = Game(seed=7)
        note = game.room.note
        self.assertIsNotNone(note)
        self.assertIsNone(game.room.loot)
        description = '\n'.join(game.describe_room())
        self.assertIn(note.title, description)
        self.assertIn('loot', description)
        self.assertNotIn(note.text, description)
        self.assertNotIn(note.hint, description)
        output = '\n'.join(game.handle_command('loot'))
        self.assertIn(note.title, output)
        self.assertTrue(game.room.note_collected)
        self.assertEqual(game.journal, [note])
        self.assertEqual(game.player.gold, 0)
        reading = '\n'.join(game.handle_command('read'))
        self.assertIn(note.text, reading)
        self.assertIn(note.hint, reading)
        self.assertNotIn(note.title, '\n'.join(game.describe_room()))

    def test_repeated_loot_does_not_duplicate_journal_entries(self):
        game = Game(seed=7)
        game.handle_command('loot')
        state = game.get_state()
        game.handle_command('loot')
        self.assertEqual(game.get_state(), state)
        self.assertEqual(len(game.journal), 1)

    def test_notes_and_gold_are_collected_independently_once(self):
        for gold_already_claimed in (False, True):
            with self.subTest(gold_already_claimed=gold_already_claimed):
                game = Game(seed=7)
                room = room_with_note(game, ordinary=True)
                room.loot = Loot(gold=17, potions=2)
                room.looted = gold_already_claimed
                old_potions = game.player.potions
                collect_safely(game, room)
                self.assertEqual(game.journal, [room.note])
                self.assertTrue(room.note_collected)
                self.assertTrue(room.looted)
                self.assertEqual(game.player.gold, 0 if gold_already_claimed else 17)
                self.assertEqual(game.player.potions,
                                 old_potions + (0 if gold_already_claimed else 2))
                state = game.get_state()
                game.handle_command('loot')
                self.assertEqual(game.get_state(), state)

    def test_enemy_unconsciousness_and_vendor_prevent_note_collection(self):
        for situation in ('enemy', 'unconscious', 'shop'):
            with self.subTest(situation=situation):
                game = Game(seed=7)
                if situation == 'enemy':
                    game.room.enemy = Enemy('Note guard', 2, 2, 10, 0, (1, 4), 0, 0, 0)
                elif situation == 'unconscious':
                    game.player.hp = 0
                else:
                    game.in_shop = True
                state = game.get_state()
                game.perform(Action('loot'))
                self.assertEqual(game.get_state(), state)
                self.assertFalse(game.room.note_collected)
                self.assertEqual(game.journal, [])

    def test_collecting_a_note_does_not_spend_time_actions_or_random_rolls(self):
        game = Game(seed=7)
        game.actions_remaining = 0
        game.bonus_action_available = False
        clock, rng = game.elapsed_minutes, game.rng.getstate()
        game.handle_command('loot')
        self.assertEqual(len(game.journal), 1)
        self.assertEqual(game.elapsed_minutes, clock)
        self.assertEqual(game.rng.getstate(), rng)
        self.assertEqual(game.actions_remaining, 0)
        self.assertFalse(game.bonus_action_available)


class JournalReadingTests(unittest.TestCase):
    def two_notes(self):
        game = Game(seed=7)
        collect_safely(game, game.room)
        collect_safely(game, room_with_note(game, ordinary=True))
        return game

    def test_empty_journal_never_reveals_uncollected_note_text(self):
        game = Game(seed=7)
        for command in ('journal', 'read', 'read 1', 'read ' + game.room.note.id):
            output = '\n'.join(game.handle_command(command))
            self.assertTrue(output)
            self.assertNotIn(game.room.note.text, output)
        self.assertEqual(game.journal, [])

    def test_read_selects_latest_numbered_or_stable_id_entry(self):
        game = self.two_notes()
        first, latest = game.journal
        self.assertIn(latest.text, '\n'.join(game.handle_command('read')))
        for argument in ('1', first.id):
            self.assertIn(first.text, '\n'.join(game.handle_command('read ' + argument)))
        for argument in ('2', latest.id):
            self.assertIn(latest.text, '\n'.join(game.read_note(argument)))
        listing = '\n'.join(game.journal_lines())
        for index, note in enumerate(game.journal, 1):
            self.assertIn(note.title, listing)
            self.assertIn(f'floor {note.floor}', listing.lower())
            self.assertRegex(listing, rf'(?m)^\s*{index}[.):\s]')
            self.assertNotIn(note.text, listing)

    def test_invalid_numbers_ids_and_uncollected_notes_are_not_readable(self):
        game = self.two_notes()
        uncollected = next(note for note in NOTES[1] if note not in game.journal)
        state = game.get_state()
        for argument in ('0', '-1', '3', '999999', '1.0', '1 extra',
                         'not-a-note', uncollected.id, NOTES[5][0].id):
            with self.subTest(argument=argument):
                output = '\n'.join(game.handle_command('read ' + argument))
                self.assertTrue(output)
                for notes in NOTES.values():
                    for note in notes:
                        self.assertNotIn(note.text, output)
                self.assertEqual(game.get_state(), state)

    def test_terminal_and_structured_read_actions_have_identical_results(self):
        terminal, structured = Game(seed=7), Game(seed=7)
        for game in (terminal, structured):
            game.handle_command('loot')
        pairs = [('journal', Action('journal')), ('read', Action('read')),
                 ('read 1', Action('read', '1')),
                 ('read ' + terminal.journal[0].id, Action('read', terminal.journal[0].id))]
        for command, action in pairs:
            self.assertEqual(terminal.handle_command(command), structured.perform(action))
            self.assertEqual(terminal.get_state(), structured.get_state())


class JournalStateTests(unittest.TestCase):
    def test_journal_survives_portal_and_descent_while_new_floor_notes_reset(self):
        game = Game(seed=7)
        for room in game.dungeon.rooms.values():
            if room.note:
                collect_safely(game, room)
        collected = list(game.journal)
        game.position = game.dungeon.boss_position
        game.room.enemy.hp = 0
        game.floor_cleared = True
        game.handle_command('portal')
        self.assertEqual(game.journal, collected)
        self.assertIn(collected[0].text, '\n'.join(game.handle_command('read 1')))
        game.handle_command('descend')
        self.assertEqual(game.floor, 2)
        self.assertEqual(game.journal, collected)
        self.assertTrue(all(not room.note_collected for room in game.dungeon.rooms.values()))
        game.handle_command('loot')
        self.assertEqual(len(game.journal), 5)
        self.assertEqual(game.journal[-1].floor, 2)
        self.assertIn(collected[0].text, '\n'.join(game.handle_command('read 1')))

    def test_snapshot_hides_uncollected_text_and_detaches_collected_records(self):
        game = Game(seed=7)
        state = game.get_state()
        json.dumps(state)
        self.assertEqual(state['journal'], [])
        for room in state['rooms']:
            if not room['visited']:
                self.assertEqual(set(room), {'position', 'visited'})
        entrance = next(room for room in state['rooms'] if room['visited'])
        self.assertEqual(entrance['note'], {'id': game.room.note.id,
                                           'title': game.room.note.title})
        self.assertFalse(entrance['note_collected'])
        self.assertNotIn(game.room.note.text, json.dumps(state, ensure_ascii=False))
        note = game.room.note
        game.handle_command('loot')
        state = game.get_state()
        self.assertEqual(state['journal'], [asdict(note)])
        entrance = next(room for room in state['rooms'] if room['visited'])
        self.assertTrue(entrance['note_collected'])
        state['journal'][0]['text'] = 'tampered'
        entrance['note']['title'] = 'tampered'
        state['journal'].clear()
        self.assertEqual(game.journal, [note])
        self.assertNotEqual(game.room.note.title, 'tampered')
        self.assertIn(note.text, '\n'.join(game.handle_command('read 1')))

    def test_journal_and_read_are_informational_in_every_game_context(self):
        for situation in ('exploration', 'combat', 'unconscious', 'shop', 'won', 'quit', 'dead'):
            with self.subTest(situation=situation):
                game = Game(seed=7)
                game.handle_command('loot')
                note = game.journal[0]
                if situation in ('combat', 'unconscious'):
                    game.room.enemy = Enemy('Note guard', 2, 2, 10, 0, (1, 4), 0, 0, 0)
                if situation == 'unconscious':
                    game.player.hp = 0
                elif situation == 'shop':
                    game.in_shop = True
                elif situation == 'won':
                    game.won = True
                elif situation == 'quit':
                    game.quit_requested = True
                elif situation == 'dead':
                    game.player.dead = True
                game.actions_remaining = 0
                game.bonus_action_available = False
                game.round_number = 17
                state, clock, rng = game.get_state(), game.elapsed_minutes, game.rng.getstate()
                self.assertIn(note.title, '\n'.join(game.perform(Action('journal'))))
                for action in (Action('read'), Action('read', '1'), Action('read', note.id)):
                    self.assertIn(note.text, '\n'.join(game.perform(action)))
                self.assertEqual(game.get_state(), state)
                self.assertEqual(game.elapsed_minutes, clock)
                self.assertEqual(game.rng.getstate(), rng)


class JournalCampaignTests(unittest.TestCase):
    def test_real_five_floor_adventure_collects_and_reads_all_twenty_notes(self):
        game, _, transcript = complete_adventure(7, floors=5)
        self.assertTrue(game.won, '\n'.join(transcript[-20:]))
        self.assertEqual(len(game.journal), 20)
        self.assertEqual({note.id for note in game.journal},
                         {note.id for notes in NOTES.values() for note in notes})
        for index, note in enumerate(game.journal, 1):
            self.assertIn(note.text, '\n'.join(game.read_note(str(index))))

    def test_real_cli_reads_notes_during_a_complete_campaign(self):
        game, commands, _ = complete_adventure(7, floors=5)
        self.assertTrue(game.won)
        script = []
        for command in commands:
            script.append(command)
            if command == 'loot':
                script.extend(('journal', 'read'))
        with TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'Main.py'),
                                     '--name', 'Tarin', '--seed', '7'],
                                    cwd=directory, input='\n'.join(script) + '\n',
                                    text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertIn('Your first dungeon is conquered', result.stdout)
        for notes in NOTES.values():
            for note in notes:
                self.assertIn(note.title, result.stdout)
                self.assertIn(note.text, result.stdout)


if __name__ == '__main__':
    unittest.main()
