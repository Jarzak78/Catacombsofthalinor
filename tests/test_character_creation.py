"""Rolled characters use visible dice and never affect the dungeon RNG."""

from dataclasses import FrozenInstanceError
import io
import random
import unittest
from unittest.mock import Mock, patch

import Main
from character_creation import (
    ABILITY_NAMES, AbilityRoll, canonical_class, roll_ability_scores, select_character,
)


class ScriptedDice:
    def __init__(self, values):
        self.values = iter(values)
        self.calls = []

    def randint(self, low, high):
        self.calls.append((low, high))
        value = next(self.values)
        if not low <= value <= high:
            raise AssertionError(f"Scripted die {value} is outside {low}..{high}")
        return value


class AbilityRollTests(unittest.TestCase):
    def test_lowest_die_is_discarded_exactly_once_even_when_tied(self):
        dice = ScriptedDice([1, 1, 5, 6] * 6)
        rolls = roll_ability_scores(dice)
        for roll in rolls:
            self.assertEqual(roll.dice, (1, 1, 5, 6))
            self.assertEqual(roll.dropped, 1)
            self.assertEqual(roll.total, 12)
        self.assertEqual(dice.calls, [(1, 6)] * 24)

    def test_ones_and_sixes_are_kept_without_score_floors_or_bonuses(self):
        for face, expected in ((1, 3), (6, 18)):
            with self.subTest(face=face):
                rolls = roll_ability_scores(ScriptedDice([face] * 24))
                self.assertEqual([roll.total for roll in rolls], [expected] * 6)

    def test_scores_keep_the_announced_stat_order(self):
        dice = ScriptedDice([face for face in range(1, 7) for _ in range(4)])
        rolls = roll_ability_scores(dice)
        self.assertEqual(tuple(roll.stat for roll in rolls), (
            "strength", "dexterity", "intelligence", "constitution", "wisdom", "charisma",
        ))
        self.assertEqual(tuple(roll.stat for roll in rolls), ABILITY_NAMES)
        self.assertEqual(tuple(roll.total for roll in rolls), (3, 6, 9, 12, 15, 18))

    def test_roll_records_are_immutable(self):
        roll = AbilityRoll("strength", (4, 5, 6, 1), 1, 15)
        with self.assertRaises(FrozenInstanceError):
            roll.total = 18
        self.assertIsInstance(roll.dice, tuple)

    def test_same_seed_repeats_the_recorded_dice(self):
        self.assertEqual(roll_ability_scores(random.Random(7)),
                         roll_ability_scores(random.Random(7)))


class CharacterSelectionTests(unittest.TestCase):
    def run_selection(self, responses, values=None, **kwargs):
        responses = iter(responses)
        dice = ScriptedDice(values if values is not None else [6, 5, 4, 1] * 6)
        output = []
        player = select_character(
            dice,
            input_fn=lambda _prompt: next(responses),
            output_fn=output.append,
            **kwargs,
        )
        return player, dice, "\n".join(output)

    def test_accepting_each_class_uses_rolled_stats_and_class_hit_points(self):
        for class_id, expected_hp in (("fighter", 12), ("rogue", 10), ("wizard", 8)):
            with self.subTest(class_id=class_id):
                player, dice, output = self.run_selection(
                    ["accept"], name="Tarin", class_id=class_id,
                )
                self.assertEqual(player.name, "Tarin")
                self.assertEqual(player.class_id, class_id)
                self.assertEqual({stat: getattr(player, stat) for stat in ABILITY_NAMES},
                                 dict.fromkeys(ABILITY_NAMES, 15))
                self.assertEqual((player.hp, player.max_hp), (expected_hp, expected_hp))
                self.assertEqual(len(dice.calls), 24)
                self.assertIn("[6, 5, 4, 1]  drop 1  = 15", output)

    def test_all_named_and_numbered_class_choices_are_accepted(self):
        choices = {
            "1": "fighter", "warrior": "fighter", "fighter": "fighter",
            "2": "rogue", "rogue": "rogue", "rouge": "rogue",
            "3": "wizard", "wizard": "wizard",
        }
        for choice, expected in choices.items():
            with self.subTest(choice=choice):
                player, dice, _ = self.run_selection([f" {choice.upper()} ", "accept"])
                self.assertEqual(player.class_id, expected)
                self.assertEqual(len(dice.calls), 24)

    def test_invalid_class_choice_waits_without_rolling_a_score_block(self):
        player, dice, output = self.run_selection(["archer", "Wizard", "accept"])
        self.assertEqual(player.class_id, "wizard")
        self.assertEqual(len(dice.calls), 24)
        self.assertIn("Choose 1 (Warrior), 2 (Rogue), or 3 (Wizard).", output)

    def test_one_reroll_replaces_all_six_scores_and_further_rerolls_preserve_them(self):
        player, dice, output = self.run_selection(
            ["reroll", "r", "reroll", "accept"], class_id="rogue",
            values=[1] * 24 + [6] * 24,
        )
        self.assertEqual(len(dice.calls), 48)
        self.assertEqual([getattr(player, stat) for stat in ABILITY_NAMES], [18] * 6)
        self.assertEqual(output.count("Your starting ability scores:"), 2)
        self.assertEqual(output.count("already used your one reroll"), 2)
        for expected in ("drop 1  = 3", "drop 6  = 18"):
            self.assertIn(expected, output)

    def test_player_can_quit_after_using_the_one_reroll(self):
        player, dice, _ = self.run_selection(
            ["reroll", "quit"], class_id="wizard", values=[1] * 24 + [6] * 24,
        )
        self.assertIsNone(player)
        self.assertEqual(len(dice.calls), 48)

    def test_invalid_acceptance_response_preserves_the_current_rolls(self):
        player, dice, output = self.run_selection(
            ["another", "42", "accept"], class_id="warrior",
        )
        self.assertEqual(player.strength, 15)
        self.assertEqual(len(dice.calls), 24)
        self.assertEqual(output.count("Your starting ability scores:"), 1)
        self.assertEqual(output.count("Your current scores are unchanged."), 2)

    def test_enter_accepts_the_visible_scores(self):
        player, dice, _ = self.run_selection([""], class_id="wizard")
        self.assertEqual(player.intelligence, 15)
        self.assertEqual(len(dice.calls), 24)

    def test_quitting_class_selection_rolls_nothing(self):
        player, dice, _ = self.run_selection(["quit"])
        self.assertIsNone(player)
        self.assertEqual(dice.calls, [])

    def test_quitting_after_rolling_creates_no_character(self):
        with patch("character_creation.Player.create") as create:
            player, dice, _ = self.run_selection(["quit"], class_id="rogue")
        self.assertIsNone(player)
        self.assertEqual(len(dice.calls), 24)
        create.assert_not_called()

    def test_invalid_preselected_class_fails_before_rolling(self):
        dice = ScriptedDice([])
        with self.assertRaises(ValueError):
            select_character(dice, class_id="druid", input_fn=Mock(), output_fn=Mock())
        self.assertEqual(dice.calls, [])

    def test_eof_and_interruption_are_left_for_the_launcher_to_handle(self):
        for interruption in (EOFError, KeyboardInterrupt):
            with self.subTest(interruption=interruption):
                with self.assertRaises(interruption):
                    select_character(ScriptedDice([]), input_fn=Mock(side_effect=interruption),
                                     output_fn=Mock())


class CharacterLauncherTests(unittest.TestCase):
    def test_quick_start_bypasses_creation_and_preserves_explicit_preset_choice(self):
        for supplied, expected in (([], "fighter"), (["--class", "rouge"], "rogue"),
                                   (["--class", "wizard"], "wizard")):
            with self.subTest(supplied=supplied):
                game = Mock(over=True)
                game.introduction.return_value = ["Title", "Dungeon story"]
                with patch.object(Main.sys, "argv", ["Main.py", "--quick-start", "--seed", "7", *supplied]), \
                     patch.object(Main, "select_character") as select, \
                     patch.object(Main, "Game", return_value=game) as constructor, \
                     patch("builtins.input") as read, patch("sys.stdout", new_callable=io.StringIO) as output:
                    Main.main()
                select.assert_not_called()
                read.assert_not_called()
                constructor.assert_called_once_with(name="Adventurer", seed=7, floors=5,
                                                    class_id=expected)
                self.assertIn("Dungeon story", output.getvalue())

    def test_preselected_class_still_rolls_and_seed_is_passed_separately_to_game(self):
        game = Mock(over=True)
        game.introduction.return_value = ["Title", "Dungeon story"]
        accepted = Mock()
        with patch.object(Main.sys, "argv", ["Main.py", "--class", "wizard", "--name", " Tessa ",
                                             "--seed", "13"]), \
             patch.object(Main, "select_character", return_value=accepted) as select, \
             patch.object(Main, "Game", return_value=game) as constructor, \
             patch("sys.stdout", new_callable=io.StringIO):
            Main.main()
        args, kwargs = select.call_args
        self.assertIsInstance(args[0], random.Random)
        self.assertEqual(args[0].getstate(), random.Random(13).getstate())
        self.assertEqual(kwargs, {"name": "Tessa", "class_id": "wizard"})
        constructor.assert_called_once_with(name="Tessa", seed=13, floors=5, player=accepted)

    def test_quitting_before_acceptance_does_not_initialize_a_dungeon(self):
        with patch.object(Main.sys, "argv", ["Main.py"]), \
             patch.object(Main, "select_character", return_value=None), \
             patch.object(Main, "Game") as constructor, \
             patch("sys.stdout", new_callable=io.StringIO) as output:
            Main.main()
        constructor.assert_not_called()
        self.assertIn("You leave the trial for another day.", output.getvalue())

    def test_closing_creation_exits_without_a_traceback_or_dungeon(self):
        for interruption in (EOFError, KeyboardInterrupt):
            with self.subTest(interruption=interruption):
                with patch.object(Main.sys, "argv", ["Main.py"]), \
                     patch.object(Main, "select_character", side_effect=interruption), \
                     patch.object(Main, "Game") as constructor, \
                     patch("sys.stdout", new_callable=io.StringIO) as output:
                    Main.main()
                constructor.assert_not_called()
                self.assertIn("You leave the trial for another day.", output.getvalue())


if __name__ == "__main__":
    unittest.main()
