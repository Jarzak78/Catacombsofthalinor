"""Class abilities through the engine, including costs and invalid inputs."""

from collections import deque
import json
import unittest

from actions import Action
from equipment import make_equipment
from game import Game
from player import Player
from room import Enemy


class ClassRandom:
    """Assert the exact dice pools and reject accidental extra random draws."""

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


def class_game(class_id, values=(), level=1):
    game = Game(seed=7, class_id=class_id)
    game.player.level = level
    if class_id == "wizard":
        game.player.spell_slots = dict(game.player.max_spell_slots)
    game.room.enemy = Enemy("Test sentinel", 100, 100, 12, 3, (1, 6), 1, 50, 7)
    game.rng = ClassRandom(values)
    game.begin_turn()
    return game


class ActionAssertions:
    def assert_unchanged(self, game, command):
        before = game.get_state()
        clock, rolls = game.elapsed_minutes, list(game.rng.calls)
        game.handle_command(command)
        self.assertEqual(game.get_state(), before)
        self.assertEqual(game.elapsed_minutes, clock)
        self.assertEqual(game.rng.calls, rolls)


class ClassActionTests(ActionAssertions, unittest.TestCase):
    def test_constructor_uses_supplied_character_and_keeps_default_warrior(self):
        default = Game(seed=7)
        self.assertEqual(default.player.class_id, "fighter")
        self.assertEqual((default.player.hp, default.player.armor_class,
                          default.player.attack_bonus, default.player.damage_bonus),
                         (12, 18, 5, 5))
        player = Player.create("Tamsin", "rogue")
        game = Game(seed=7, player=player)
        self.assertIs(game.player, player)
        self.assertEqual(game.player.name, "Tamsin")

    def test_skills_is_informational_even_during_opening_examination(self):
        for class_id in ("fighter", "rogue", "wizard"):
            with self.subTest(class_id=class_id):
                game = class_game(class_id)
                game.free_examine_available = True
                self.assert_unchanged(game, "skills")
                self.assertTrue(game.handle_command("skills"))

    def test_wrong_class_abilities_are_rejected_without_spending_resources(self):
        forbidden = {
            "fighter": ("hide", "cast missile", "cast armor", "cast shield"),
            "rogue": ("wind", "surge", "cast firebolt", "cast shield"),
            "wizard": ("hide", "wind", "surge"),
        }
        for class_id, commands in forbidden.items():
            for command in commands:
                with self.subTest(class_id=class_id, command=command):
                    game = class_game(class_id, level=5)
                    game.player.hp -= 1
                    self.assert_unchanged(game, command)


class WizardActionTests(ActionAssertions, unittest.TestCase):
    def test_default_attack_is_fire_bolt_and_spends_no_slot(self):
        game = class_game("wizard", [15, 7])
        slots = dict(game.player.spell_slots)
        game.free_examine_available = True
        game.handle_command("attack")
        self.assertEqual(game.enemy.hp, 93)
        self.assertEqual(game.player.spell_slots, slots)
        self.assertEqual(game.actions_remaining, 0)
        self.assertTrue(game.bonus_action_available)
        self.assertFalse(game.free_examine_available)
        self.assertFalse(game.enemy_sapped)
        self.assertEqual(game.rng.calls, [(1, 20, 15), (1, 10, 7)])

    def test_fire_bolt_scales_at_fifth_level_without_extra_attack(self):
        game = class_game("wizard", [15, 3, 7], level=5)
        game.handle_command("attack")
        self.assertEqual(game.enemy.hp, 90)
        self.assertEqual(game.actions_remaining, 0)
        self.assertEqual(game.rng.calls, [(1, 20, 15), (1, 10, 3), (1, 10, 7)])

    def test_fire_bolt_critical_doubles_dice_but_not_focus_bonus(self):
        game = class_game("wizard", [20, 1, 1])
        game.player.collect_equipment(make_equipment("arcane_staff", 2))
        output = game.handle_command("cast firebolt")
        self.assertEqual(game.enemy.hp, 98)
        self.assertIn("Critical", "\n".join(output))
        self.assertEqual(game.rng.calls, [(1, 20, 20), (1, 10, 1), (1, 10, 1)])

    def test_fire_bolt_natural_one_fumbles_without_damage_roll(self):
        game = class_game("wizard", [1])
        hp = game.player.hp
        game.handle_command("cast firebolt")
        self.assertEqual(game.player.hp, hp - 1)
        self.assertEqual(game.enemy.hp, 100)
        self.assertEqual(game.rng.calls, [(1, 20, 1)])

    def test_strike_uses_quarterstaff_and_strength_instead_of_spell_damage(self):
        game = class_game("wizard", [15, 4])
        game.handle_command("strike")
        self.assertEqual(game.enemy.hp, 97)  # 1d6 (4) - 1 Strength.
        self.assertEqual(game.rng.calls, [(1, 20, 15), (1, 6, 4)])
        self.assertFalse(game.enemy_sapped)

    def test_spell_alias_and_structured_action_match_cast_command(self):
        reference = class_game("wizard", [15, 5])
        output = reference.handle_command("cast firebolt")
        alias = class_game("wizard", [15, 5])
        self.assertEqual(alias.handle_command("cast fire bolt"), output)
        self.assertEqual(alias.get_state(), reference.get_state())
        structured = class_game("wizard", [15, 5])
        self.assertEqual(structured.perform(Action("cast", "firebolt")), output)
        self.assertEqual(structured.get_state(), reference.get_state())

    def test_magic_missile_spends_one_slot_and_one_action_without_attack_roll(self):
        game = class_game("wizard", [1, 2, 4])
        game.enemy.armor_class = 100
        game.handle_command("cast missile")
        self.assertEqual(game.enemy.hp, 90)  # 3d4 + 3.
        self.assertEqual(game.player.spell_slots[1], 1)
        self.assertEqual(game.actions_remaining, 0)
        self.assertTrue(game.bonus_action_available)
        self.assertEqual(game.rng.calls, [(1, 4, 1), (1, 4, 2), (1, 4, 4)])

    def test_invalid_spell_and_missing_target_slot_or_action_are_pure(self):
        for reason in ("unknown", "no target", "no slot", "no action", "dead"):
            with self.subTest(reason=reason):
                game = class_game("wizard")
                command = "cast missile"
                if reason == "unknown":
                    command = "cast teleport"
                elif reason == "no target":
                    game.room.enemy = None
                elif reason == "no slot":
                    game.player.spell_slots[1] = 0
                elif reason == "no action":
                    game.actions_remaining = 0
                else:
                    game.player.take_damage(game.player.hp)
                self.assert_unchanged(game, command)

    def test_mage_armor_costs_action_in_combat_and_repeated_cast_is_pure(self):
        game = class_game("wizard")
        game.free_examine_available = True
        base_ac = game.player.armor_class
        game.handle_command("cast armor")
        self.assertTrue(game.player.mage_armor_active)
        self.assertEqual(game.player.armor_class, base_ac + 3)
        self.assertEqual(game.player.spell_slots[1], 1)
        self.assertEqual(game.actions_remaining, 0)
        self.assertFalse(game.free_examine_available)
        self.assert_unchanged(game, "cast armor")

    def test_mage_armor_outside_combat_spends_slot_without_turn_action(self):
        game = class_game("wizard")
        game.room.enemy = None
        game.actions_remaining = 0
        game.handle_command("cast armor")
        self.assertTrue(game.player.mage_armor_active)
        self.assertEqual(game.player.spell_slots[1], 1)
        self.assertEqual(game.actions_remaining, 0)
        self.assertEqual(game.rng.calls, [])

    def test_shield_preserves_action_and_free_examination_then_expires_on_miss(self):
        game = class_game("wizard", [12])
        game.free_examine_available = True
        game.handle_command("cast shield")
        self.assertTrue(game.shield_active)
        self.assertEqual(game.get_state()["armor_class"], game.player.armor_class + 5)
        self.assertTrue(game.free_examine_available)
        self.assertEqual(game.actions_remaining, 1)
        self.assertFalse(game.bonus_action_available)
        self.assertEqual(game.player.spell_slots[1], 1)
        self.assert_unchanged(game, "cast shield")
        hp = game.player.hp
        game.enemy_turn()  # Total 15 misses the shielded AC 17.
        self.assertEqual(game.player.hp, hp)
        self.assertFalse(game.shield_active)
        self.assertEqual(game.rng.calls, [(1, 20, 12)])

    def test_shield_does_not_remove_ambush_advantage_or_duplicate_attack_dice(self):
        game = class_game("wizard", [10, 15, 2])
        game.handle_command("cast shield")
        game.ambush_advantage = True
        hp = game.player.hp
        game.enemy_turn()
        self.assertEqual(game.player.hp, hp - 3)
        self.assertFalse(game.shield_active)
        self.assertFalse(game.ambush_advantage)
        self.assertEqual(game.rng.calls, [(1, 20, 10), (1, 20, 15), (1, 6, 2)])

    def test_frost_spends_second_level_slot_and_saps_only_on_hit(self):
        for hit, values in ((True, [15, 2, 3, 4]), (False, [2])):
            with self.subTest(hit=hit):
                game = class_game("wizard", values, level=3)
                game.handle_command("cast frost")
                self.assertEqual(game.player.spell_slots[2], 1)
                self.assertEqual(game.enemy.hp, 91 if hit else 100)
                self.assertEqual(game.enemy_sapped, hit)
                self.assertEqual(game.actions_remaining, 0)

    def test_frost_and_fireball_before_unlock_do_not_spend_lower_slots(self):
        for level, command in ((1, "cast frost"), (3, "cast fireball")):
            with self.subTest(level=level, command=command):
                self.assert_unchanged(class_game("wizard", level=level), command)

    def test_fireball_failed_and_successful_saves_use_enemy_dexterity(self):
        for save, expected in ((9, 24), (10, 12)):
            with self.subTest(save=save):
                game = class_game("wizard", [*([3] * 8), save], level=5)
                game.enemy.initiative_bonus = 4
                game.handle_command("cast fireball")
                self.assertEqual(game.enemy.hp, 100 - expected)
                self.assertEqual(game.player.spell_slots[3], 1)
                self.assertEqual(game.actions_remaining, 0)
                self.assertEqual(len(game.rng.calls), 9)
                self.assertEqual(sorted((a, b) for a, b, _ in game.rng.calls),
                                 [(1, 6)] * 8 + [(1, 20)])

    def test_spell_narration_describes_magic_instead_of_a_longsword(self):
        for spell, level, values in (("firebolt", 1, [15, 4]),
                                      ("frost", 3, [15, 2, 3, 4])):
            with self.subTest(spell=spell):
                game = class_game("wizard", values, level=level)
                output = "\n".join(game.handle_command("cast " + spell)).lower()
                self.assertNotIn("longsword", output)
                self.assertNotIn("your blade", output)

    def test_spell_defeat_grants_rewards_once_and_clears_encounter(self):
        game = class_game("wizard", [1, 1, 1])
        game.enemy.hp = 1
        game.free_examine_available = True
        game.handle_command("cast missile")
        self.assertIsNone(game.enemy)
        self.assertEqual((game.player.xp, game.player.gold), (50, 7))
        self.assertFalse(game.free_examine_available)
        self.assert_unchanged(game, "cast missile")

    def test_wizard_short_and_long_rests_restore_the_right_resources(self):
        game = class_game("wizard")
        game.room.enemy = None
        game.player.spell_slots[1] = 0
        game.handle_command("rest 0")
        self.assertEqual(game.player.spell_slots[1], 1)
        self.assertFalse(game.player.arcane_recovery_available)
        game.handle_command("rest 0")
        self.assertEqual(game.player.spell_slots[1], 1)
        game.player.mage_armor_active = True
        game.handle_command("long rest")
        self.assertFalse(game.player.mage_armor_active)
        self.assertEqual(game.player.spell_slots, game.player.max_spell_slots)
        self.assertTrue(game.player.arcane_recovery_available)


class RogueActionTests(ActionAssertions, unittest.TestCase):
    def test_first_level_hide_spends_action_and_second_level_spends_bonus(self):
        for level in (1, 2):
            with self.subTest(level=level):
                game = class_game("rogue", [10], level=level)
                game.free_examine_available = True
                game.handle_command("hide")
                self.assertTrue(game.hidden)
                self.assertEqual(game.actions_remaining, 0 if level == 1 else 1)
                self.assertEqual(game.bonus_action_available, level == 1)
                self.assertEqual(game.free_examine_available, level >= 2)
                self.assertEqual(game.rng.calls, [(1, 20, 10)])

    def test_hide_failure_spends_correct_resource_without_damage(self):
        for level in (1, 2):
            with self.subTest(level=level):
                game = class_game("rogue", [1], level=level)
                hp = game.player.hp
                game.handle_command("hide")
                self.assertFalse(game.hidden)
                self.assertEqual(game.player.hp, hp)
                self.assertEqual(game.actions_remaining, 0 if level == 1 else 1)
                self.assertEqual(game.bonus_action_available, level == 1)

    def test_hide_uses_expertise_and_a_deeper_floor_is_harder(self):
        game = class_game("rogue", [6])
        game.floor = 3
        game.handle_command("hide")  # 6 + Dex 3 + expertise 4 = 13 vs DC 15.
        self.assertFalse(game.hidden)

    def test_invalid_hide_does_not_roll_or_spend(self):
        for reason in ("no enemy", "spent action", "spent bonus", "already hidden"):
            with self.subTest(reason=reason):
                game = class_game("rogue", level=2 if reason == "spent bonus" else 1)
                if reason == "no enemy":
                    game.room.enemy = None
                elif reason == "spent action":
                    game.actions_remaining = 0
                elif reason == "spent bonus":
                    game.bonus_action_available = False
                else:
                    game.hidden = True
                self.assert_unchanged(game, "hide")

    def test_hidden_rogue_gets_advantage_and_sneak_attack_on_next_hit(self):
        game = class_game("rogue", [10, 3, 15, 4, 5], level=2)
        game.handle_command("hide")
        game.handle_command("attack")
        self.assertEqual(game.enemy.hp, 88)  # Rapier 4 + Dex 3 + Sneak 5.
        self.assertFalse(game.hidden)
        self.assertTrue(game.rogue_vex)
        self.assertTrue(game.sneak_attack_used)
        self.assertFalse(game.enemy_sapped)
        self.assertEqual(game.rng.calls, [(1, 20, 10), (1, 20, 3), (1, 20, 15),
                                          (1, 8, 4), (1, 6, 5)])

    def test_rapier_vex_carries_to_next_turn_and_enables_sneak_attack(self):
        game = class_game("rogue", [15, 4, 3, 15, 4, 5])
        game.handle_command("attack")
        self.assertEqual(game.enemy.hp, 93)
        self.assertTrue(game.rogue_vex)
        self.assertFalse(game.sneak_attack_used)
        game.begin_turn()
        game.handle_command("attack")
        self.assertEqual(game.enemy.hp, 81)
        self.assertTrue(game.sneak_attack_used)
        self.assertFalse(game.enemy_sapped)

    def test_sneak_attack_is_once_per_turn_even_if_additional_action_is_granted(self):
        game = class_game("rogue", [15, 14, 2, 4, 15, 14, 2], level=2)
        game.hidden = True
        game.actions_remaining = 2
        game.handle_command("attack")
        game.handle_command("attack")
        self.assertEqual(game.enemy.hp, 86)  # (2+3+4) then (2+3).
        self.assertTrue(game.sneak_attack_used)
        self.assertEqual(game.actions_remaining, 0)
        self.assertEqual(sum(high == 6 for _, high, _ in game.rng.calls), 1)

    def test_critical_rapier_doubles_weapon_and_sneak_dice_but_adds_dex_once(self):
        game = class_game("rogue", [20, 14, 1, 1, 1, 1, 1, 1, 1, 1], level=5)
        game.hidden = True
        output = game.handle_command("attack")
        self.assertEqual(game.enemy.hp, 89)  # 2d8 + 6d6, all ones, +3 Dex.
        self.assertEqual(game.actions_remaining, 0)
        self.assertEqual(sum(high == 8 for _, high, _ in game.rng.calls), 2)
        self.assertEqual(sum(high == 6 for _, high, _ in game.rng.calls), 6)
        self.assertIn("Critical", "\n".join(output))

    def test_low_rolled_dexterity_applies_penalty_once_to_combined_sneak_damage(self):
        game = class_game("rogue", [15, 10, 1, 6])
        game.player.strength = 3  # Both finesse choices must have the -4 penalty.
        game.player.dexterity = 3
        game.hidden = True
        output = "\n".join(game.handle_command("attack"))
        # 1 weapon + 6 Sneak Attack - 4 Dexterity = 3; do not clamp the
        # weapon component before adding Sneak Attack.
        self.assertEqual(game.enemy.hp, 97)
        self.assertIn("for 3 damage", output)
        self.assertTrue(game.sneak_attack_used)
        self.assertEqual(game.rng.calls, [(1, 20, 15), (1, 20, 10),
                                          (1, 8, 1), (1, 6, 6)])

    def test_low_dexterity_critical_clamps_after_combining_all_doubled_dice(self):
        game = class_game("rogue", [20, 10, 1, 1, 1, 1])
        game.player.strength = 3  # Finesse cannot substitute a stronger ability.
        game.player.dexterity = 3
        game.hidden = True
        output = "\n".join(game.handle_command("attack"))
        # Two weapon ones + two Sneak Attack ones - 4 Dexterity = 0.
        self.assertEqual(game.enemy.hp, 100)
        self.assertIn("for 0 damage", output)
        self.assertIn("Critical", output)
        self.assertTrue(game.sneak_attack_used)
        self.assertEqual(game.rng.calls, [(1, 20, 20), (1, 20, 10),
                                          (1, 8, 1), (1, 8, 1),
                                          (1, 6, 1), (1, 6, 1)])

    def test_low_dexterity_sneak_eligible_miss_does_not_roll_any_damage(self):
        game = class_game("rogue", [2, 3])
        game.player.dexterity = 3
        game.hidden = True
        hp = game.player.hp
        game.handle_command("attack")
        self.assertEqual(game.enemy.hp, 100)
        self.assertEqual(game.player.hp, hp)
        self.assertFalse(game.sneak_attack_used)
        self.assertFalse(game.hidden)
        self.assertFalse(game.rogue_vex)
        self.assertEqual(game.rng.calls, [(1, 20, 2), (1, 20, 3)])

    def test_miss_consumes_hide_and_vex_without_sneak_damage_rolls(self):
        game = class_game("rogue", [2, 3])
        game.hidden = True
        game.rogue_vex = True
        game.handle_command("attack")
        self.assertFalse(game.hidden)
        self.assertFalse(game.rogue_vex)
        self.assertFalse(game.sneak_attack_used)
        self.assertEqual(game.enemy.hp, 100)
        self.assertEqual(game.rng.calls, [(1, 20, 2), (1, 20, 3)])

    def test_selected_natural_one_self_damages_but_discarded_one_does_not(self):
        for rolls, fumble in (([1, 1], True), ([1, 15, 2, 3], False)):
            with self.subTest(fumble=fumble):
                game = class_game("rogue", rolls)
                game.hidden = True
                hp = game.player.hp
                game.handle_command("attack")
                self.assertEqual(game.player.hp, hp - int(fumble))
                self.assertEqual(game.enemy.hp, 100 if fumble else 92)
                self.assertEqual(game.sneak_attack_used, not fumble)

    def test_hidden_rogue_causes_enemy_disadvantage_until_attacking(self):
        game = class_game("rogue", [19, 2])
        game.hidden = True
        hp = game.player.hp
        game.enemy_turn()
        self.assertEqual(game.player.hp, hp)
        self.assertTrue(game.hidden)
        self.assertEqual(game.rng.calls, [(1, 20, 19), (1, 20, 2)])

    def test_second_level_flee_uses_bonus_and_leaves_without_opportunity_attack(self):
        for level in (1, 2):
            with self.subTest(level=level):
                game = class_game("rogue", level=level)
                retreat = next(iter(game.room.exits.values()))
                game.dungeon.get_room(retreat).enemy = None
                game.previous_position = retreat
                game.hidden = True
                game.rogue_vex = True
                game.handle_command("flee")
                self.assertEqual(game.position, retreat)
                self.assertEqual(game.actions_remaining, 0 if level == 1 else 1)
                self.assertEqual(game.bonus_action_available, level == 1)
                self.assertFalse(game.hidden)
                self.assertFalse(game.rogue_vex)
                self.assertEqual(game.rng.calls, [])

    def test_second_level_flee_does_not_spend_an_action_if_bonus_is_unavailable(self):
        game = class_game("rogue", level=2)
        game.previous_position = next(iter(game.room.exits.values()))
        game.bonus_action_available = False
        self.assert_unchanged(game, "flee")

    def test_uncanny_dodge_halves_only_first_hit_and_refreshes_next_turn(self):
        game = class_game("rogue", [15, 6, 15, 6, 15, 6], level=5)
        game.player.max_hp = game.player.hp = 30
        self.assertTrue(game.uncanny_dodge_available)
        game.enemy_turn()
        self.assertEqual(game.player.hp, 27)  # floor((6+1)/2) = 3.
        self.assertFalse(game.uncanny_dodge_available)
        game.enemy_turn()
        self.assertEqual(game.player.hp, 20)
        game.begin_turn()
        self.assertTrue(game.uncanny_dodge_available)
        game.enemy_turn()
        self.assertEqual(game.player.hp, 17)

    def test_uncanny_dodge_is_not_spent_on_a_miss_or_used_after_death(self):
        game = class_game("rogue", [2], level=5)
        game.enemy_turn()
        self.assertTrue(game.uncanny_dodge_available)
        game.player.take_damage(game.player.hp)
        before = game.get_state()
        self.assertEqual(game.enemy_turn(), [])
        self.assertEqual(game.player.hp, 0)
        self.assertTrue(game.over)
        self.assertTrue(game.uncanny_dodge_available)
        self.assertEqual(game.get_state(), before)
        self.assertEqual(game.rng.calls, [(1, 20, 2)])

    def test_class_state_snapshot_is_detached_and_json_serializable(self):
        game = class_game("rogue", level=5)
        game.hidden = True
        game.rogue_vex = True
        game.sneak_attack_used = True
        snapshot = game.get_state()
        json.dumps(snapshot)
        snapshot["player"]["dexterity"] = 3
        self.assertEqual(game.player.dexterity, 16)
        self.assertTrue(game.hidden)
        self.assertTrue(game.rogue_vex)


if __name__ == "__main__":
    unittest.main()
