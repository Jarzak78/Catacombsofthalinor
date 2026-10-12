"""Zero HP ends every class's adventure without another turn or recovery roll."""

import unittest

from game import Game
from loot_library import Loot, valuable
from room import Enemy
from tests.test_class_actions import ClassRandom, class_game
from ui_controller import DesktopSession


CLASSES = ("fighter", "rogue", "wizard")


class InstantDeathTests(unittest.TestCase):
    def assert_dead(self, game, output):
        self.assertEqual(game.player.hp, 0)
        self.assertTrue(game.player.dead)
        self.assertFalse(game.player.is_alive)
        self.assertFalse(game.player.is_conscious)
        self.assertTrue(game.over)
        text = "\n".join(output)
        self.assertIn("You die", text)
        self.assertNotIn("Death save", text)
        self.assertNotIn("unconscious", text.lower())
        self.assertNotIn("Actions left", text)

    def test_exact_lethal_normal_and_critical_hits_end_each_class_immediately(self):
        for class_id in CLASSES:
            for critical, dice in ((False, [19, 2]), (True, [20, 1, 1])):
                with self.subTest(class_id=class_id, critical=critical):
                    game = class_game(class_id, dice)
                    game.player.hp = 3
                    game.actions_remaining = 0
                    game.bonus_action_available = False
                    before_round = game.round_number
                    output = game.handle_command("end")
                    self.assert_dead(game, output)
                    self.assertEqual(game.round_number, before_round)
                    self.assertEqual(game.actions_remaining, 0)
                    self.assertFalse(game.bonus_action_available)
                    self.assertEqual(game.enemy.hp, 100)
                    self.assertEqual((game.player.xp, game.player.gold), (0, 0))
                    self.assertEqual(len(game.rng.calls), len(dice))
                    self.assertFalse(game.rng.values)
                    self.assertEqual("Critical hit!" in "\n".join(output), critical)

    def test_lethal_opening_ambush_does_not_begin_a_hero_turn_for_any_class(self):
        for class_id in CLASSES:
            with self.subTest(class_id=class_id):
                game = Game(seed=7, class_id=class_id)
                direction, destination = next(iter(game.room.exits.items()))
                game.dungeon.get_room(destination).enemy = Enemy(
                    "Ambush sentry", 100, 100, 12, 3, (1, 6), 1, 50, 7)
                game.player.hp = 3
                # Enemy wins initiative; failed Perception grants two attack d20s.
                game.rng = ClassRandom([2, 20, 1, 19, 18, 2])
                output = game.handle_command(direction)
                self.assert_dead(game, output)
                self.assertEqual(game.position, destination)
                self.assertEqual(game.round_number, 0)
                self.assertEqual(game.elapsed_minutes, 1)
                self.assertEqual(game.rng.calls,
                                 [(1, 20, 2), (1, 20, 20), (1, 20, 1),
                                  (1, 20, 19), (1, 20, 18), (1, 6, 2)])
                self.assertFalse(game.free_examine_available)
                self.assertNotIn("Combat:", "\n".join(output))

    def test_lethal_weapon_and_spell_fumbles_end_each_class_on_the_same_action(self):
        cases = (("fighter", "attack", 5), ("rogue", "attack", 1),
                 ("wizard", "cast firebolt", 1), ("wizard", "strike", 1),
                 ("wizard", "cast frost", 3))
        for class_id, command, level in cases:
            with self.subTest(class_id=class_id, command=command):
                game = class_game(class_id, [1], level=level)
                game.player.hp = 1
                output = game.handle_command(command)
                self.assert_dead(game, output)
                self.assertEqual(game.enemy.hp, 100)
                self.assertEqual(game.actions_remaining, 0)
                self.assertEqual(game.rng.calls, [(1, 20, 1)])
                self.assertNotIn("Extra Attack", "\n".join(output))

    def test_death_blocks_healing_rest_actions_and_time_without_spending_resources(self):
        commands = ("end", "potion", "wind", "rest", "rest 0", "long rest",
                    "surge", "attack", "strike", "dodge", "flee", "hide",
                    "cast firebolt", "cast missile", "cast armor", "cast shield",
                    "mana", "ember", "loot", "portal", "buy potion", "descend")
        for class_id in CLASSES:
            with self.subTest(class_id=class_id):
                game = class_game(class_id)
                game.player.ember_stones = 2
                game.player.mana_draughts = 2
                game.player.take_damage(game.player.hp)
                before = game.get_state()
                clock = game.elapsed_minutes
                for command in commands:
                    with self.subTest(command=command):
                        output = game.handle_command(command)
                        self.assertIn("over", "\n".join(output).lower())
                        self.assertEqual(game.get_state(), before)
                        self.assertEqual(game.elapsed_minutes, clock)
                        self.assertEqual(game.rng.calls, [])

    def test_beginning_turn_after_death_does_not_refresh_any_turn_state(self):
        game = class_game("rogue", level=5)
        game.player.take_damage(game.player.hp)
        game.actions_remaining = 0
        game.bonus_action_available = False
        game.free_examine_available = True
        game.dodging = True
        game.enemy_sapped = True
        game.sneak_attack_used = True
        game.uncanny_dodge_available = False
        before = game.get_state()
        for _ in range(3):
            self.assertEqual(game.begin_turn(), [])
            self.assertEqual(game.get_state(), before)
        self.assertEqual(game.rng.calls, [])

    def test_rogue_uncanny_dodge_mitigates_before_deciding_if_damage_is_lethal(self):
        for hp, expected_hp in ((4, 1), (3, 0)):
            with self.subTest(hp=hp):
                game = class_game("rogue", [19, 6], level=5)
                game.player.hp = hp
                output = game.enemy_turn()  # Seven damage is halved to three.
                self.assertIn("Uncanny Dodge", "\n".join(output))
                self.assertEqual(game.player.hp, expected_hp)
                self.assertEqual(game.over, expected_hp == 0)
                self.assertFalse(game.uncanny_dodge_available)
                if expected_hp == 0:
                    self.assert_dead(game, output)
                else:
                    self.assertNotIn("You die", "\n".join(output))
                self.assertEqual(game.rng.calls, [(1, 20, 19), (1, 6, 6)])

    def test_snapshot_and_status_report_death_without_removed_save_fields(self):
        game = class_game("fighter")
        game.player.take_damage(game.player.hp)
        state = game.get_state()
        self.assertTrue(state["over"])
        self.assertTrue(state["player"]["dead"])
        self.assertEqual(state["player"]["hp"], 0)
        for field in ("death_save_successes", "death_save_failures", "stable"):
            self.assertNotIn(field, state["player"])
        text = "\n".join(game.status()).lower()
        self.assertIn("dead", text)
        self.assertNotIn("death save", text)
        self.assertNotIn("unconscious", text)
        self.assertEqual(game.rng.calls, [])

    def test_collected_journal_remains_readable_after_death_without_recovery(self):
        game = Game(seed=7)
        note = game.room.note
        self.assertIsNotNone(note)
        game.journal.append(note)
        game.player.take_damage(game.player.hp)
        game.rng = ClassRandom()
        before = game.get_state()
        self.assertIn(note.title, "\n".join(game.handle_command("journal")))
        self.assertIn(note.text, "\n".join(game.handle_command("read 1")))
        self.assertEqual(game.get_state(), before)
        self.assertEqual(game.rng.calls, [])

    def test_desktop_session_observes_instant_death_and_blocks_further_play(self):
        session = DesktopSession(seed=7)
        session.begin_creation()
        session.roll_stats()
        session.accept_character()
        session.enter_dungeon()
        game = session.game
        game.room.enemy = Enemy("Test sentry", 100, 100, 12, 3, (1, 6), 1, 50, 7)
        game.player.hp = 3
        game.rng = ClassRandom([19, 2])
        output = session.submit_command("end")
        self.assert_dead(game, output)
        state = session.snapshot()
        self.assertEqual(state["scene"], "dungeon")
        self.assertTrue(state["over"])
        self.assertTrue(state["player"]["dead"])
        self.assertEqual(state["player"]["hp"], 0)
        session.submit_command("potion")
        session.submit_command("end")
        self.assertEqual(session.snapshot(), state)
        self.assertEqual(game.rng.calls, [(1, 20, 19), (1, 6, 2)])

    def test_direct_vendor_charm_purchase_cannot_revive_zero_hp_characters(self):
        for class_id in CLASSES:
            for death_fixture in ("lethal damage", "zero HP without dead flag"):
                with self.subTest(class_id=class_id, death_fixture=death_fixture):
                    game = class_game(class_id)
                    game.room.enemy = None
                    game.in_shop = True
                    game.player.gold = 10000
                    if death_fixture == "lethal damage":
                        game.player.take_damage(game.player.hp)
                    else:
                        game.player.hp = 0
                        game.player.dead = False
                    before = game.get_state()
                    clock = game.elapsed_minutes
                    game.buy("charm")
                    self.assertEqual(game.get_state(), before)
                    self.assertEqual(game.player.hp, 0)
                    self.assertEqual(game.player.gold, 10000)
                    self.assertFalse(game.player.vitality_charm)
                    self.assertTrue(game.over)
                    self.assertEqual(game.elapsed_minutes, clock)
                    self.assertEqual(game.rng.calls, [])

    def test_direct_mutating_engine_entrypoints_preserve_dead_adventures(self):
        defeated_guardian = Enemy("Defeated guardian", 100, 0, 12, 3,
                                  (1, 6), 1, 10000, 999, boss=True)
        operations = (
            ("defeat_enemy", (defeated_guardian,)),
            ("dodge", ()), ("disengage", ()), ("action_surge", ()),
            ("hide", ()), ("drink_mana", ()), ("sell", ("all",)),
            ("enter_portal", ()), ("buy", ("potion",)), ("descend", ()),
            ("use_ember", ()), ("attack", ()), ("attack_once", ()),
            ("end_turn", ()), ("short_rest", ()), ("long_rest", ()),
            ("cast_spell", ("missile",)), ("cast_spell", ("armor",)),
            ("cast_spell", ("shield",)), ("drink_potion", ()),
            ("second_wind", ()), ("examine_foe", ()), ("collect_loot", ()),
            ("begin_encounter", ()), ("begin_turn", ()), ("enemy_turn", ()),
        )
        for class_id in CLASSES:
            for scene in ("combat", "safe room", "entrance", "shop"):
                with self.subTest(class_id=class_id, scene=scene):
                    game = class_game(class_id, level=5)
                    game.position = (game.dungeon.start if scene == "entrance"
                                     else game.dungeon.boss_position)
                    game.room.enemy = (Enemy("Waiting sentry", 100, 100, 12, 3,
                                             (1, 6), 1, 50, 7)
                                       if scene == "combat" else None)
                    game.room.visited = True
                    game.room.loot = Loot(gold=33, potions=2, items=(valuable(1),))
                    game.room.looted = False
                    game.in_shop = scene == "shop"
                    game.floor_cleared = True
                    game.previous_position = game.dungeon.start
                    game.player.gold = 10000
                    game.player.treasure_inventory.append(valuable(1))
                    game.player.ember_stones = 2
                    game.player.mana_draughts = 2
                    if class_id == "wizard":
                        game.player.spell_slots[1] = 1
                    game.free_examine_available = True
                    game.ambush_advantage = True
                    game.sneak_attack_used = True
                    game.uncanny_dodge_available = False
                    game.player.take_damage(game.player.hp)
                    before = game.get_state()
                    clock = game.elapsed_minutes
                    valid_move = ("move", (next(iter(game.room.exits)),))
                    for method, arguments in (valid_move, *operations):
                        with self.subTest(method=method, arguments=arguments):
                            getattr(game, method)(*arguments)
                            self.assertEqual(game.get_state(), before)
                            self.assertEqual(game.elapsed_minutes, clock)
                            self.assertEqual(game.rng.calls, [])


if __name__ == "__main__":
    unittest.main()
