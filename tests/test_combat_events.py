"""Presentation events describe resolved combat without another dice roll."""

from collections import deque
import json
import unittest

from combat_events import CombatEventLog
from game import Game
from room import Enemy


class ExactRandom:
    """Reject extra draws, including draws accidentally made by presentation."""

    def __init__(self, values=()):
        self.values = deque(values)
        self.calls = []

    def randint(self, low, high):
        if not self.values:
            raise AssertionError(f"Unexpected random roll: {low}..{high}")
        value = self.values.popleft()
        if not low <= value <= high:
            raise AssertionError((low, high, value))
        self.calls.append((low, high, value))
        return value


def combat_game(class_id="fighter", values=(), level=1):
    game = Game(seed=7, class_id=class_id)
    game.player.level = level
    if class_id == "wizard":
        game.player.spell_slots = dict(game.player.max_spell_slots)
    game.room.enemy = Enemy("Test sentinel", 100, 100, 12, 3, (1, 6), 1, 50, 7)
    game.rng = ExactRandom(values)
    game.begin_turn()
    return game


class CombatEventLogTests(unittest.TestCase):
    def test_bound_monotonic_cursor_and_detached_reads(self):
        log = CombatEventLog(limit=2)
        original = {"position": [1, 2], "enemy": {"name": "Sentinel"}}
        log.append(original)
        original["position"][0] = 90
        log.append({"position": [3, 4]})
        log.append({"position": [5, 6]})
        self.assertEqual(log.sequence, 3)
        self.assertEqual([event["id"] for event in log.events_since()], [2, 3])
        self.assertEqual(log.events_since(2), [{"id": 3, "position": [5, 6]}])
        snapshot = log.events_since()
        snapshot[0]["position"][0] = 99
        snapshot.clear()
        self.assertEqual(log.events_since(1)[0]["position"], [3, 4])
        self.assertEqual(log.events_since(3), [])
        self.assertEqual(log.sequence, 3)

    def test_appended_nested_data_is_detached(self):
        log = CombatEventLog()
        original = {"position": [1, 2], "enemy": {"name": "Sentinel"}}
        log.append(original)
        original["position"][0] = 90
        original["enemy"]["name"] = "Changed"
        result = log.events_since()[0]
        result["enemy"]["name"] = "Changed again"
        self.assertEqual(log.events_since(), [
            {"id": 1, "position": [1, 2], "enemy": {"name": "Sentinel"}}])


class ResolvedCombatEventTests(unittest.TestCase):
    def test_attack_boundaries_retain_selected_roll_and_resolved_damage(self):
        for roll, hit, near, values in ((4, False, False, [4]),
                                        (5, False, True, [5]),
                                        (6, False, True, [6]),
                                        (7, True, False, [7, 2])):
            with self.subTest(roll=roll):
                game = combat_game(values=values)
                game.attack()
                event, = game.visual_events_since()
                self.assertEqual((event["roll"], event["total"], event["ac"]),
                                 (roll, roll + game.player.attack_bonus, 12))
                self.assertEqual((event["hit"], event["near_miss"], event["critical"], event["fumble"]),
                                 (hit, near, False, False))
                self.assertEqual(event["damage"], 7 if hit else 0)
                self.assertEqual(event["enemy_hp_after"], game.enemy.hp)
                self.assertEqual(event["target_hp_after"], game.enemy.hp)
                self.assertEqual(game.rng.calls,
                                 [(1, 20, roll)] + ([(1, 8, 2)] if hit else []))

    def test_low_damage_natural_twenty_stays_critical(self):
        game = combat_game("wizard", [20, 1, 1])
        game.enemy.armor_class = 100
        game.attack()
        event, = game.visual_events_since()
        self.assertEqual((event["kind"], event["roll"], event["hit"], event["critical"], event["damage"]),
                         ("firebolt", 20, True, True, 2))
        self.assertEqual((event["target_hp_before"], event["target_hp_after"]), (100, 98))
        self.assertFalse(event["killed"])
        self.assertEqual(game.rng.calls, [(1, 20, 20), (1, 10, 1), (1, 10, 1)])

    def test_discarded_advantage_one_is_not_a_fumble(self):
        game = combat_game(values=[1, 15, 2])
        game.hidden = True
        game.attack()
        event, = game.visual_events_since()
        self.assertEqual(event["roll"], 15)
        self.assertFalse(event["fumble"])
        self.assertEqual(event["self_damage"], 0)
        self.assertEqual(game.rng.calls, [(1, 20, 1), (1, 20, 15), (1, 8, 2)])

    def test_fumble_is_logged_before_early_death_without_extra_attack(self):
        for class_id in ("fighter", "wizard"):
            with self.subTest(class_id=class_id):
                game = combat_game(class_id, [1], level=5)
                game.player.hp = 1
                game.attack()
                event, = game.visual_events_since()
                self.assertEqual((event["roll"], event["hit"], event["fumble"], event["self_damage"]),
                                 (1, False, True, 1))
                self.assertTrue(event["player_killed"])
                self.assertFalse(event["killed"])
                self.assertFalse(event["near_miss"])
                self.assertEqual(event["enemy_hp_after"], 100)
                self.assertEqual(game.player.hp, 0)
                self.assertEqual(game.rng.calls, [(1, 20, 1)])

    def test_killing_hit_preserves_enemy_snapshot_and_displayed_overkill(self):
        game = combat_game(values=[15, 8])
        enemy = game.enemy
        enemy.hp = 2
        enemy.boss = True
        game.attack()
        self.assertIsNone(game.enemy)
        event, = game.visual_events_since()
        self.assertEqual(event["enemy"], {"name": "Test sentinel", "boss": True})
        self.assertEqual((event["target_hp_before"], event["target_hp_after"],
                          event["target_max_hp"], event["damage"]), (2, 0, 100, 13))
        self.assertTrue(event["killed"])
        self.assertTrue(event["enemy_killed"])
        self.assertEqual(event["position"], list(game.position))
        self.assertEqual(event["floor"], game.floor)
        game.handle_command("look")
        self.assertEqual(game.visual_events_since(), [event])

    def test_extra_attack_produces_two_ordered_resolved_events(self):
        game = combat_game(values=[15, 2, 16, 3], level=5)
        game.attack()
        first, second = game.visual_events_since()
        self.assertEqual((first["id"], second["id"], game.visual_sequence), (1, 2, 2))
        self.assertEqual((first["damage"], second["damage"]), (7, 8))
        self.assertEqual((first["target_hp_before"], first["target_hp_after"],
                          second["target_hp_before"], second["target_hp_after"]),
                         (100, 93, 93, 85))
        self.assertEqual(game.rng.calls, [(1, 20, 15), (1, 8, 2), (1, 20, 16), (1, 8, 3)])

    def test_enemy_hit_uses_uncanny_dodge_final_damage(self):
        game = combat_game("rogue", [18, 6], level=5)
        hp = game.player.hp
        game.enemy_turn()
        event, = game.visual_events_since()
        self.assertEqual((event["source"], event["damage"]), ("enemy", 3))
        self.assertEqual((event["target_hp_before"], event["target_hp_after"]), (hp, hp - 3))
        self.assertEqual(event["target_hp_after"], game.player.hp)
        self.assertFalse(event["enemy_killed"])
        self.assertEqual(game.rng.calls, [(1, 20, 18), (1, 6, 6)])

    def test_enemy_fumble_self_death_retains_dead_enemy_for_animation(self):
        game = combat_game(values=[1])
        game.enemy.hp = 1
        hp = game.player.hp
        game.enemy_turn()
        event, = game.visual_events_since()
        self.assertEqual((event["source"], event["damage"], event["self_damage"]), ("enemy", 0, 1))
        self.assertEqual((event["enemy_hp_before"], event["enemy_hp_after"]), (1, 0))
        self.assertEqual((event["target_hp_before"], event["target_hp_after"]), (hp, hp))
        self.assertTrue(event["enemy_killed"])
        self.assertFalse(event["killed"])
        self.assertIsNone(game.enemy)
        self.assertEqual(game.rng.calls, [(1, 20, 1)])

    def test_fatal_enemy_critical_refers_to_player_death(self):
        game = combat_game(values=[20, 1, 1])
        game.player.hp = 2
        game.enemy_turn()
        event, = game.visual_events_since()
        self.assertEqual((event["source"], event["damage"], event["target_hp_after"]), ("enemy", 3, 0))
        self.assertTrue(event["critical"])
        self.assertTrue(event["killed"])
        self.assertTrue(event["player_killed"])
        self.assertFalse(event["enemy_killed"])
        self.assertEqual(game.player.hp, 0)
        game.enemy_turn()
        self.assertEqual(game.visual_events_since(), [event])

    def test_automatic_magic_missile_has_no_invented_attack_roll(self):
        game = combat_game("wizard", [1, 2, 4])
        game.enemy.armor_class = 100
        game.cast_spell("missile")
        event, = game.visual_events_since()
        self.assertEqual((event["kind"], event["hit"], event["damage"]), ("missile", True, 10))
        self.assertEqual((event["roll"], event["total"], event["ac"]), (None, None, None))
        self.assertFalse(event["critical"])
        self.assertEqual(game.rng.calls, [(1, 4, 1), (1, 4, 2), (1, 4, 4)])

    def test_fireball_uses_final_save_reduced_damage(self):
        for save, damage, saved in ((9, 24, False), (10, 12, True)):
            with self.subTest(saved=saved):
                game = combat_game("wizard", [*([3] * 8), save], level=5)
                game.enemy.initiative_bonus = 4
                game.cast_spell("fireball")
                event, = game.visual_events_since()
                self.assertEqual((event["kind"], event["damage"], event["saved"]),
                                 ("fireball", damage, saved))
                self.assertEqual(event["target_hp_after"], game.enemy.hp)
                self.assertIsNone(event["roll"])
                self.assertEqual(game.rng.calls, [(1, 6, 3)] * 8 + [(1, 20, save)])

    def test_frost_and_ember_use_their_resolved_damage(self):
        game = combat_game("wizard", [15, 2, 3, 4], level=3)
        game.cast_spell("frost")
        event, = game.visual_events_since()
        self.assertEqual((event["kind"], event["damage"], event["roll"]), ("frost", 9, 15))
        self.assertEqual(game.rng.calls, [(1, 20, 15), (1, 8, 2), (1, 8, 3), (1, 8, 4)])
        game = combat_game(values=[2, 3, 4])
        game.player.ember_stones = 1
        game.use_ember()
        event, = game.visual_events_since()
        self.assertEqual((event["kind"], event["damage"], event["roll"]), ("ember", 9, None))
        self.assertEqual(game.rng.calls, [(1, 6, 2), (1, 6, 3), (1, 6, 4)])

    def test_valid_buffs_emit_once_and_shield_attack_records_actual_ac(self):
        game = combat_game("wizard", [12])
        game.cast_spell("armor")
        armor, = game.visual_events_since()
        self.assertEqual((armor["kind"], armor["damage"], armor["target_hp_after"]),
                         ("armor", 0, game.player.hp))
        before = game.get_state()
        game.cast_spell("armor")
        self.assertEqual(game.get_state(), before)
        game.cast_spell("shield")
        shield, = game.visual_events_since(1)
        self.assertEqual((shield["kind"], shield["damage"]), ("shield", 0))
        before = game.get_state()
        game.cast_spell("shield")
        self.assertEqual(game.get_state(), before)
        protected_ac = game.player.armor_class + 5
        game.enemy_turn()
        incoming, = game.visual_events_since(2)
        self.assertEqual((incoming["ac"], incoming["hit"]), (protected_ac, False))
        self.assertEqual(game.rng.calls, [(1, 20, 12)])

    def test_safe_room_buff_can_have_no_enemy(self):
        game = combat_game("wizard")
        game.room.enemy = None
        game.cast_spell("armor")
        event, = game.visual_events_since()
        self.assertIsNone(event["enemy"])
        self.assertEqual(event["enemy_hp_before"], 0)
        self.assertEqual(event["target_hp_after"], game.player.hp)
        self.assertEqual(game.rng.calls, [])

    def test_invalid_actions_and_information_do_not_emit_or_clear_events(self):
        for reason in ("unknown spell", "no foe", "no slot", "spent action",
                       "no ember", "spent weapon action", "wrong class"):
            with self.subTest(reason=reason):
                game = combat_game("wizard", [15, 2])
                game.attack()
                game.actions_remaining = 1
                command = "cast missile"
                if reason == "unknown spell":
                    command = "cast teleport"
                elif reason == "no foe":
                    game.room.enemy = None
                elif reason == "no slot":
                    game.player.spell_slots[1] = 0
                elif reason == "spent action":
                    game.actions_remaining = 0
                elif reason == "no ember":
                    command = "ember"
                    game.player.ember_stones = 0
                elif reason == "spent weapon action":
                    command = "strike"
                    game.actions_remaining = 0
                else:
                    command = "hide"
                before = game.get_state()
                calls = list(game.rng.calls)
                game.handle_command(command)
                self.assertEqual(game.get_state(), before)
                self.assertEqual(game.rng.calls, calls)
                for info in ("look", "stats", "skills", "inventory", "help", "credits"):
                    game.handle_command(info)
                    self.assertEqual(game.visual_events_since(), before["visual_events"])
                    self.assertEqual(game.rng.calls, calls)

    def test_game_state_and_event_reads_are_detached_json_without_extra_draws(self):
        game = combat_game(values=[15, 2])
        game.attack()
        events = game.visual_events_since()
        state = game.get_state()
        self.assertEqual(state["visual_sequence"], 1)
        self.assertEqual(state["visual_events"], events)
        self.assertEqual(set(events[0]["enemy"]), {"name", "boss"})
        json.dumps(state)
        state["visual_events"][0]["enemy"]["name"] = "Changed"
        state["visual_events"][0]["position"][0] = 999
        events[0]["enemy"]["name"] = "Also changed"
        self.assertEqual(game.visual_events_since()[0]["enemy"]["name"], "Test sentinel")
        self.assertEqual(game.visual_events_since()[0]["position"], list(game.position))
        self.assertEqual(game.rng.calls, [(1, 20, 15), (1, 8, 2)])

    def test_game_keeps_last_64_events_with_monotonic_ids(self):
        game = combat_game(values=[2] * 70)
        for _ in range(70):
            game.actions_remaining = 1
            game.attack()
        events = game.visual_events_since()
        self.assertEqual(len(events), 64)
        self.assertEqual([event["id"] for event in events], list(range(7, 71)))
        self.assertEqual(game.visual_sequence, 70)
        self.assertEqual([event["id"] for event in game.visual_events_since(68)], [69, 70])
        self.assertEqual(game.rng.calls, [(1, 20, 2)] * 70)


if __name__ == "__main__":
    unittest.main()
