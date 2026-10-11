"""Command-level combat checks and complete adventures through the real engine."""

from collections import deque
from pathlib import Path
import subprocess
import sys
import unittest

from game import Game
from room import Enemy


ROOT = Path(__file__).resolve().parents[1]


class ScriptedRandom:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        value = next(self.values)
        assert low <= value <= high, (low, high, value)
        return value


def combat_game(values=()):
    game = Game(seed=7)
    game.room.enemy = Enemy("Practice guardian", 100, 100, 12, 3, (1, 6), 1, 50, 0)
    game.rng = ScriptedRandom(values)
    game.round_number = 1
    return game


def route_to(game, destination):
    """Find a route while excluding the final chamber until requested."""
    frontier = deque([(game.position, [])])
    seen = {game.position}
    while frontier:
        position, route = frontier.popleft()
        if position == destination:
            return route
        for direction, target in game.dungeon.get_room(position).exits.items():
            if target in seen:
                continue
            if target == game.dungeon.boss_position and target != destination:
                continue
            seen.add(target)
            frontier.append((target, [*route, direction]))
    raise AssertionError(f"No route to {destination}")


def complete_adventure(seed, floors=1):
    """Explore every room using actual combat rolls, healing, and actions."""
    game = Game(name="Tarin", seed=seed, floors=floors)
    transcript = []
    commands = []

    def act(command):
        commands.append(command)
        transcript.extend(game.handle_command(command))

    def clear_room():
        for _ in range(200):
            if game.over or game.enemy is None:
                break
            if not game.player.is_conscious:
                act("end")
                continue
            if game.free_examine_available:
                act("examine")
            if game.player.hp <= game.player.max_hp - 5 and game.bonus_action_available:
                if game.player.second_wind_uses:
                    act("wind")
                elif game.player.potions:
                    act("potion")
            if game.actions_remaining:
                act("attack")
            elif game.enemy.boss and game.player.level >= 2 and game.player.action_surge_available:
                act("surge")
            else:
                act("end")
        if game.enemy and not game.over:
            raise AssertionError("Combat never completed")
        if not game.over:
            act("loot")
            # Multiple real short rests are legal; they cost an hour each.
            for _ in range(4):
                if game.player.hp == game.player.max_hp and game.player.second_wind_uses == 2:
                    break
                act("rest")
                if game.player.hp < game.player.max_hp:
                    act("wind")

    while not game.over:
        targets = [position for position in game.dungeon.rooms
                   if position != game.dungeon.boss_position]
        # First floor has the guaranteed weapon; later floors have supplies.
        weapon_room = next((position for position, room in game.dungeon.rooms.items()
                            if position in targets and room.loot and room.loot.weapon_name
                            and room.enemy is None), None)
        if weapon_room is not None:
            targets.remove(weapon_room)
            targets.insert(0, weapon_room)
        targets.append(game.dungeon.boss_position)
        for target in targets:
            for direction in route_to(game, target):
                act(direction)
                clear_room()
                if game.over:
                    return game, commands, transcript
            clear_room()
            if game.over:
                return game, commands, transcript
        if not game.floor_cleared:
            raise AssertionError("Floor exploration did not defeat its guardian")
        act("portal")
        if game.floor < game.total_floors:
            for item in ("sword", "armor", "charm", "ward"):
                act("buy " + item)
        act("descend")
    return game, commands, transcript


class TurnTests(unittest.TestCase):
    def test_attack_spends_action_without_automatically_ending_turn(self):
        game = combat_game([15, 4, 19, 2])
        game.handle_command("attack")
        self.assertEqual(game.actions_remaining, 0)
        self.assertEqual(game.player.hp, 12)
        self.assertEqual(game.enemy.hp, 91)
        game.handle_command("attack")
        self.assertEqual(game.enemy.hp, 91)
        game.handle_command("end")
        self.assertEqual(game.player.hp, 12)  # Sap picked the lower enemy d20.
        self.assertEqual(game.actions_remaining, 1)
        self.assertTrue(game.bonus_action_available)
        self.assertFalse(game.enemy_sapped)

    def test_enemy_can_win_initiative_and_strike_before_player(self):
        game = Game(seed=7)
        direction, position = next(iter(game.room.exits.items()))
        game.dungeon.get_room(position).enemy = Enemy("Sentry", 10, 10, 12, 3, (1, 6), 1, 50, 0)
        # The successful Perception check avoids ambush Advantage.
        game.rng = ScriptedRandom([2, 20, 12, 15, 3])
        output = game.handle_command(direction)
        self.assertEqual(game.player.hp, 8)
        self.assertEqual(game.actions_remaining, 1)
        self.assertIn("Initiative", "\n".join(output))

    def test_initiative_tie_goes_to_adventurer(self):
        game = combat_game([10, 12])
        game.begin_encounter()
        self.assertEqual(game.player.hp, 12)
        self.assertEqual(game.round_number, 1)

    def test_dodge_uses_action_and_expires_at_next_turn(self):
        game = combat_game([19, 2])
        game.handle_command("dodge")
        self.assertTrue(game.dodging)
        self.assertEqual(game.actions_remaining, 0)
        game.handle_command("end")
        self.assertEqual(game.player.hp, 12)
        self.assertFalse(game.dodging)

    def test_potion_is_bonus_action_and_does_not_replace_attack(self):
        game = combat_game([1, 1, 15, 4])
        game.player.hp = 3
        game.handle_command("potion")
        self.assertEqual(game.player.hp, 7)
        self.assertEqual(game.player.potions, 2)
        self.assertEqual(game.actions_remaining, 1)
        self.assertFalse(game.bonus_action_available)
        game.handle_command("wind")
        self.assertEqual(game.player.second_wind_uses, 2)
        game.handle_command("attack")
        self.assertEqual(game.enemy.hp, 91)

    def test_full_health_potion_preserves_resource_and_bonus_action(self):
        game = combat_game()
        game.handle_command("potion")
        self.assertEqual(game.player.potions, 3)
        self.assertTrue(game.bonus_action_available)

    def test_second_wind_cannot_be_used_twice_in_one_turn(self):
        game = combat_game([1])
        game.player.hp = 2
        game.handle_command("wind")
        game.handle_command("wind")
        self.assertEqual(game.player.hp, 4)
        self.assertEqual(game.player.second_wind_uses, 1)

    def test_action_surge_gives_one_additional_action_once_per_rest(self):
        game = combat_game([15, 2, 15, 2])
        game.player.gain_xp(300)
        game.handle_command("attack")
        game.handle_command("surge")
        self.assertEqual(game.actions_remaining, 1)
        game.handle_command("attack")
        self.assertEqual(game.actions_remaining, 0)
        self.assertEqual(game.enemy.hp, 86)
        game.handle_command("surge")
        self.assertEqual(game.actions_remaining, 0)

    def test_first_level_fighter_cannot_action_surge(self):
        game = combat_game()
        game.handle_command("surge")
        self.assertEqual(game.actions_remaining, 1)
        self.assertTrue(game.player.action_surge_available)

    def test_informational_and_invalid_commands_do_not_advance_turn(self):
        game = combat_game()
        for command in ["help", "look", "map", "stats", "inventory", "nope", "north", "loot", "rest"]:
            with self.subTest(command=command):
                game.handle_command(command)
                self.assertEqual(game.player.hp, 12)
                self.assertEqual(game.actions_remaining, 1)
                self.assertEqual(game.round_number, 1)

    def test_disengage_retreats_without_roll_or_opportunity_attack(self):
        game = combat_game()
        previous = next(iter(game.room.exits.values()))
        game.dungeon.get_room(previous).enemy = None
        game.previous_position = previous
        enemy = game.enemy
        game.handle_command("flee")
        self.assertEqual(game.position, previous)
        self.assertEqual(game.player.hp, 12)
        self.assertEqual(enemy.hp, 100)

    def test_disengage_cannot_be_taken_after_action_spent(self):
        game = combat_game()
        game.previous_position = next(iter(game.room.exits.values()))
        game.actions_remaining = 0
        original = game.position
        game.handle_command("flee")
        self.assertEqual(game.position, original)

    def test_defeated_enemy_does_not_attack_or_award_rewards_twice(self):
        game = combat_game([15, 8])
        game.enemy.hp = 1
        game.handle_command("attack")
        self.assertIsNone(game.enemy)
        self.assertEqual(game.player.xp, 50)
        game.handle_command("attack")
        game.handle_command("end")
        self.assertEqual(game.player.hp, 12)
        self.assertEqual(game.player.xp, 50)

    def test_unconscious_player_cannot_drink_their_own_potion(self):
        game = combat_game()
        game.player.hp = 0
        game.handle_command("potion")
        self.assertEqual(game.player.hp, 0)
        self.assertEqual(game.player.potions, 3)

    def test_natural_twenty_death_save_restores_action_on_that_turn(self):
        game = combat_game([1, 1, 20])
        game.player.hp = 0
        game.handle_command("end")  # Enemy misses with Advantage; death save rolls 20.
        self.assertEqual(game.player.hp, 1)
        self.assertEqual(game.actions_remaining, 1)
        self.assertTrue(game.bonus_action_available)
        self.assertFalse(game.over)

    def test_melee_hit_on_unconscious_character_critically_fails_death_saves(self):
        game = combat_game([18, 19, 1, 1])
        game.player.hp = 0
        game.player.death_save_failures = 1
        output = game.handle_command("end")
        self.assertTrue(game.player.dead)
        self.assertTrue(game.over)
        self.assertIn("Critical hit", "\n".join(output))


class ExplorationTests(unittest.TestCase):
    def test_treasure_can_only_be_collected_once(self):
        game = Game(seed=7)
        target = next(position for position, room in game.dungeon.rooms.items()
                      if room.loot and room.loot.weapon_name)
        for direction in route_to(game, target):
            game.handle_command(direction)
        game.handle_command("loot")
        gold = game.player.gold
        game.handle_command("loot")
        self.assertEqual(game.player.gold, gold)
        self.assertEqual(game.player.weapon_bonus, 1)
        self.assertEqual(game.player.attack_bonus, 6)

    def test_short_rest_spends_hit_die_and_refreshes_only_one_wind_use(self):
        game = Game(seed=7)
        game.player.hp = 2
        game.player.second_wind_uses = 0
        game.player.action_surge_available = False
        game.rng = ScriptedRandom([3])
        game.handle_command("rest")
        self.assertEqual(game.player.hp, 7)
        self.assertEqual(game.player.hit_dice_remaining, 0)
        self.assertEqual(game.player.second_wind_uses, 1)
        self.assertTrue(game.player.action_surge_available)
        self.assertEqual(game.elapsed_minutes, 60)

    def test_long_rest_requires_entrance_and_sixteen_hour_gap(self):
        game = Game(seed=7)
        game.player.hp = 1
        game.handle_command("long rest")
        self.assertEqual(game.player.hp, 12)
        game.player.hp = 2
        game.handle_command("long rest")
        self.assertEqual(game.player.hp, 2)
        for _ in range(16):
            game.handle_command("rest")
        game.handle_command("long rest")
        self.assertEqual(game.player.hp, 12)
        self.assertEqual(game.player.hit_dice_remaining, 1)
        target = next(iter(game.room.exits.values()))
        game.position = target
        game.room.enemy = None
        game.player.hp = 2
        game.handle_command("long rest")
        self.assertEqual(game.player.hp, 2)

    def test_multiple_hit_dice_can_be_spent_in_one_short_rest(self):
        game = Game(seed=7)
        game.player.gain_xp(300)
        game.player.hp = 1
        game.player.second_wind_uses = 0
        game.rng = ScriptedRandom([1, 2])
        game.handle_command("rest 2")
        self.assertEqual(game.player.hp, 8)
        self.assertEqual(game.player.hit_dice_remaining, 0)
        self.assertEqual(game.player.second_wind_uses, 1)
        self.assertEqual(game.elapsed_minutes, 60)

    def test_short_rest_can_save_hit_dice_and_rejects_invalid_counts(self):
        game = Game(seed=7)
        game.player.hp = 1
        game.player.second_wind_uses = 0
        game.rng = ScriptedRandom([])
        game.handle_command("rest -1")
        game.handle_command("rest two")
        self.assertEqual(game.elapsed_minutes, 0)
        game.handle_command("rest 0")
        self.assertEqual(game.player.hp, 1)
        self.assertEqual(game.player.hit_dice_remaining, 1)
        self.assertEqual(game.player.second_wind_uses, 1)
        self.assertEqual(game.elapsed_minutes, 60)

    def test_ordinary_rooms_remain_reachable_without_entering_boss_room(self):
        for seed in range(30):
            game = Game(seed=seed)
            for position in game.dungeon.rooms:
                if position != game.dungeon.boss_position:
                    route_to(game, position)
            self.assertEqual(len(game.dungeon.get_room(game.dungeon.boss_position).exits), 1)

    def test_complete_seeded_adventures_reach_victory(self):
        for seed in (0, 7, 42):
            with self.subTest(seed=seed):
                game, _, transcript = complete_adventure(seed)
                self.assertTrue(game.won, "\n".join(transcript[-25:]))
                self.assertTrue(game.player.is_conscious)
                self.assertEqual(game.player.level, 2)
                self.assertTrue(all(room.visited for room in game.dungeon.rooms.values()))
                self.assertIn("Your first dungeon is conquered", "\n".join(transcript))

    def test_scripted_cli_can_complete_the_same_real_adventure(self):
        game, commands, _ = complete_adventure(7)
        self.assertTrue(game.won)
        result = subprocess.run(
            [sys.executable, "-B", "Main.py", "--quick-start", "--name", "Tarin", "--seed", "7", "--floors", "1"],
            cwd=ROOT, input="\n".join(commands) + "\n", text=True,
            capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Your first dungeon is conquered", result.stdout)
        self.assertIn("Warrior (Fighter) 2", result.stdout)

    def test_cli_handles_quit_and_closed_input(self):
        for commands in ("help\nstats\nquit\n", ""):
            with self.subTest(commands=commands):
                result = subprocess.run([sys.executable, "-B", "Main.py", "--quick-start", "--seed", "7", "--floors", "1"],
                                        cwd=ROOT, input=commands, text=True,
                                        capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("CATACOMBS OF THALINOR", result.stdout)
                self.assertIn("another day", result.stdout)


if __name__ == "__main__":
    unittest.main()
