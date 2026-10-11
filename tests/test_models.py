"""World invariants and revised 2024 5e character-rule examples."""

import random
import unittest

from dungeon import Dungeon
from loot_library import Loot
from player import Player, ability_modifier
from room import Enemy


class FixedRolls:
    """Provide explicit legal die results and reject unexpected extra rolls."""

    def __init__(self, *rolls):
        self.rolls = iter(rolls)
        self.calls = []

    def randint(self, minimum, maximum):
        try:
            roll = next(self.rolls)
        except StopIteration as error:
            raise AssertionError("An unexpected extra die was rolled.") from error
        if not minimum <= roll <= maximum:
            raise AssertionError(f"Roll {roll} is invalid for {minimum}..{maximum}.")
        self.calls.append((minimum, maximum))
        return roll


class PlayerTests(unittest.TestCase):
    def test_novice_fighter_stats_apply_proficiency_armor_and_dueling(self):
        player = Player()
        self.assertEqual((player.max_hp, player.hp), (12, 12))
        self.assertEqual(player.armor_class, 18)
        self.assertEqual(player.proficiency_bonus, 2)
        self.assertEqual(player.strength_modifier, 3)
        self.assertEqual(player.constitution_modifier, 2)
        self.assertEqual(player.dexterity_modifier, 2)
        self.assertEqual(player.initiative_bonus, 2)
        self.assertEqual(player.attack_bonus, 5)
        self.assertEqual(player.damage_bonus, 5)
        self.assertTrue(player.is_alive)
        self.assertTrue(player.is_conscious)

    def test_ability_modifiers_round_down_for_odd_scores(self):
        for score, expected in [(7, -2), (9, -1), (10, 0), (11, 0), (16, 3)]:
            with self.subTest(score=score):
                self.assertEqual(ability_modifier(score), expected)

    def test_damage_cannot_reduce_health_below_zero(self):
        player = Player()
        self.assertEqual(player.take_damage(13), 12)
        self.assertEqual(player.hp, 0)
        self.assertTrue(player.is_alive)
        self.assertFalse(player.is_conscious)
        self.assertEqual(player.death_save_failures, 0)

    def test_massive_damage_kills_when_excess_reaches_maximum_health(self):
        for damage, dead in [(14, False), (15, True)]:
            with self.subTest(damage=damage):
                player = Player(hp=3)
                self.assertEqual(player.take_damage(damage), 3)
                self.assertEqual(player.hp, 0)
                self.assertEqual(player.dead, dead)
                self.assertEqual(player.is_alive, not dead)

    def test_damage_at_zero_health_counts_failed_saves_and_critical_counts_two(self):
        player = Player(hp=0)
        self.assertEqual(player.take_damage(1, critical=True), 0)
        self.assertEqual(player.death_save_failures, 2)
        self.assertTrue(player.is_alive)
        self.assertEqual(player.take_damage(1), 0)
        self.assertEqual(player.death_save_failures, 3)
        self.assertTrue(player.dead)

    def test_critical_that_knocks_out_conscious_player_adds_no_failed_saves(self):
        player = Player(hp=5)
        player.take_damage(5, critical=True)
        self.assertEqual(player.hp, 0)
        self.assertEqual(player.death_save_failures, 0)

    def test_massive_damage_at_zero_health_kills_instantly(self):
        player = Player(hp=0)
        player.take_damage(player.max_hp)
        self.assertTrue(player.dead)

    def test_damage_breaks_stability_but_zero_damage_does_not(self):
        player = Player(hp=0, stable=True)
        player.take_damage(0)
        self.assertTrue(player.stable)
        self.assertEqual(player.death_save_failures, 0)
        player.take_damage(1)
        self.assertFalse(player.stable)
        self.assertEqual(player.death_save_failures, 1)

    def test_negative_damage_is_rejected_without_changing_health(self):
        player = Player()
        with self.assertRaises(ValueError):
            player.take_damage(-1)
        self.assertEqual(player.hp, player.max_hp)

    def test_healing_stops_at_maximum_health(self):
        player = Player()
        player.take_damage(4)
        self.assertEqual(player.heal(100), 4)
        self.assertEqual(player.hp, player.max_hp)
        self.assertEqual(player.heal(1), 0)

    def test_healing_restores_consciousness_and_clears_death_saves(self):
        player = Player(hp=0, death_save_successes=1, death_save_failures=2)
        self.assertEqual(player.heal(4), 4)
        self.assertTrue(player.is_conscious)
        self.assertEqual((player.death_save_successes, player.death_save_failures), (0, 0))
        self.assertFalse(player.stable)

    def test_healing_cannot_revive_a_dead_adventurer(self):
        player = Player()
        player.take_damage(player.hp + player.max_hp)
        self.assertEqual(player.heal(100), 0)
        self.assertEqual(player.hp, 0)
        self.assertFalse(player.is_alive)

    def test_negative_healing_is_rejected(self):
        player = Player()
        with self.assertRaises(ValueError):
            player.heal(-1)
        self.assertEqual(player.hp, player.max_hp)

    def test_potion_consumes_one_charge_only_for_useful_healing(self):
        player = Player()
        player.take_damage(5)
        potions_before = player.potions

        self.assertEqual(player.use_potion(FixedRolls(4, 4)), 5)
        self.assertEqual(player.hp, player.max_hp)
        self.assertEqual(player.potions, potions_before - 1)
        self.assertEqual(player.use_potion(FixedRolls()), 0)
        self.assertEqual(player.potions, potions_before - 1)

    def test_potions_do_not_revive_dead_characters_or_heal_without_supplies(self):
        for health, potions, dead in [(0, 2, True), (5, 0, False)]:
            with self.subTest(health=health, potions=potions):
                player = Player(hp=health, potions=potions, dead=dead)
                self.assertEqual(player.use_potion(FixedRolls()), 0)
                self.assertEqual(player.hp, health)
                self.assertEqual(player.potions, potions)

    def test_healing_potion_rolls_two_d4_and_adds_two(self):
        for rolls, expected in [((1, 1), 4), ((2, 4), 8), ((4, 4), 10)]:
            with self.subTest(rolls=rolls):
                player = Player(hp=1)
                rng = FixedRolls(*rolls)
                self.assertEqual(player.use_potion(rng), expected)
                self.assertEqual(player.hp, 1 + expected)
                self.assertEqual(rng.calls, [(1, 4), (1, 4)])

    def test_administered_potion_can_restore_an_unconscious_adventurer(self):
        player = Player(hp=0, death_save_failures=2)
        self.assertEqual(player.use_potion(FixedRolls(1, 1)), 4)
        self.assertTrue(player.is_conscious)
        self.assertEqual(player.death_save_failures, 0)

    def test_level_thresholds_use_cumulative_experience(self):
        player = Player(hp=4)
        self.assertEqual(player.gain_xp(299), 0)
        self.assertEqual((player.level, player.xp), (1, 299))
        self.assertEqual(player.gain_xp(1), 1)
        self.assertEqual((player.level, player.xp), (2, 300))
        self.assertEqual(player.xp_to_next_level, 900)
        self.assertEqual((player.max_hp, player.hp), (20, 12))
        self.assertEqual(player.gain_xp(599), 0)
        self.assertEqual(player.gain_xp(1), 1)
        self.assertEqual((player.level, player.xp), (3, 900))

    def test_large_reward_levels_up_without_full_healing_or_restoring_resources(self):
        player = Player(hp=4, second_wind_uses=0, hit_dice_remaining=0, action_surge_available=False)
        self.assertEqual(player.gain_xp(901), 2)
        self.assertEqual((player.level, player.xp), (3, 901))
        self.assertEqual((player.max_hp, player.hp), (28, 20))
        self.assertEqual(player.hit_dice_remaining, 2)
        self.assertEqual(player.second_wind_uses, 0)
        self.assertFalse(player.action_surge_available)
        self.assertEqual(player.xp_to_next_level, 2700)

    def test_leveling_does_not_revive_an_unconscious_character(self):
        player = Player(hp=0)
        player.gain_xp(300)
        self.assertEqual(player.level, 2)
        self.assertEqual(player.max_hp, 20)
        self.assertEqual(player.hp, 0)
        self.assertFalse(player.is_conscious)

    def test_proficiency_bonus_progresses_at_level_five(self):
        player = Player()
        player.gain_xp(6500)
        self.assertEqual(player.level, 5)
        self.assertEqual(player.proficiency_bonus, 3)
        self.assertEqual(player.attack_bonus, 6)
        self.assertEqual(player.damage_bonus, 5)

    def test_negative_experience_is_rejected_without_progress(self):
        player = Player()
        with self.assertRaises(ValueError):
            player.gain_xp(-1)
        self.assertEqual((player.level, player.xp), (1, 0))

    def test_only_stronger_equipment_replaces_a_weapon(self):
        player = Player()
        self.assertTrue(player.equip_weapon("Longsword +1", 1))
        self.assertEqual(player.attack_bonus, 6)
        self.assertEqual(player.damage_bonus, 6)

        for name, bonus in [("Rusty sword", 0), ("Another longsword +1", 1)]:
            with self.subTest(name=name):
                self.assertFalse(player.equip_weapon(name, bonus))
                self.assertEqual(player.weapon_name, "Longsword +1")
                self.assertEqual(player.attack_bonus, 6)
                self.assertEqual(player.damage_bonus, 6)

    def test_second_wind_rolls_d10_plus_fighter_level_and_spends_a_use(self):
        player = Player(hp=1)
        self.assertEqual(player.second_wind_uses, 2)
        rng = FixedRolls(4)
        self.assertEqual(player.second_wind(rng), 5)
        self.assertEqual(player.hp, 6)
        self.assertEqual(player.second_wind_uses, 1)
        self.assertEqual(rng.calls, [(1, 10)])

    def test_second_wind_requires_consciousness_and_an_available_use(self):
        for health, uses in [(0, 2), (4, 0)]:
            with self.subTest(health=health, uses=uses):
                player = Player(hp=health, second_wind_uses=uses)
                self.assertEqual(player.second_wind(FixedRolls()), 0)
                self.assertEqual((player.hp, player.second_wind_uses), (health, uses))

    def test_short_rest_recovers_one_second_wind_and_action_surge_only(self):
        player = Player(hp=4, second_wind_uses=0, hit_dice_remaining=0, action_surge_available=False)
        player.gain_xp(300)
        health_before = player.hp
        dice_before = player.hit_dice_remaining
        player.refresh_short_rest()
        self.assertEqual(player.second_wind_uses, 1)
        self.assertTrue(player.action_surge_available)
        self.assertEqual(player.hp, health_before)
        self.assertEqual(player.hit_dice_remaining, dice_before)
        player.refresh_short_rest()
        player.refresh_short_rest()
        self.assertEqual(player.second_wind_uses, 2)

    def test_spending_fighter_hit_die_heals_d10_plus_constitution(self):
        player = Player(hp=1)
        rng = FixedRolls(4)
        self.assertEqual(player.spend_hit_die(rng), 6)
        self.assertEqual(player.hp, 7)
        self.assertEqual(player.hit_dice_remaining, 0)
        self.assertEqual(rng.calls, [(1, 10)])
        self.assertEqual(player.spend_hit_die(FixedRolls()), 0)

    def test_hit_die_cannot_be_spent_at_full_health_or_while_unconscious(self):
        for health in (0, 12):
            with self.subTest(health=health):
                player = Player(hp=health)
                self.assertEqual(player.spend_hit_die(FixedRolls()), 0)
                self.assertEqual(player.hit_dice_remaining, 1)

    def test_hit_die_with_negative_constitution_never_causes_damage(self):
        player = Player(hp=5, constitution=6)
        self.assertEqual(player.spend_hit_die(FixedRolls(1)), 0)
        self.assertEqual(player.hp, 5)
        self.assertEqual(player.hit_dice_remaining, 0)

    def test_long_rest_recovers_all_hit_dice_and_fighter_resources(self):
        player = Player()
        player.gain_xp(900)
        player.hp = 1
        player.hit_dice_remaining = 0
        player.second_wind_uses = 0
        player.action_surge_available = False
        player.long_rest()
        self.assertEqual(player.hp, 28)
        self.assertEqual(player.hit_dice_remaining, 3)
        self.assertEqual(player.second_wind_uses, 2)
        self.assertTrue(player.action_surge_available)

    def test_long_rest_requires_at_least_one_hit_point(self):
        for stable in (False, True):
            with self.subTest(stable=stable):
                player = Player(hp=0, stable=stable, second_wind_uses=0, hit_dice_remaining=0)
                player.long_rest()
                self.assertEqual(player.hp, 0)
                self.assertEqual(player.stable, stable)
                self.assertEqual(player.second_wind_uses, 0)
                self.assertEqual(player.hit_dice_remaining, 0)

    def test_fourth_level_fighter_can_recover_three_second_wind_uses(self):
        player = Player()
        player.gain_xp(2700)
        self.assertEqual(player.level, 4)
        self.assertEqual(player.max_second_wind_uses, 3)
        player.long_rest()
        self.assertEqual(player.second_wind_uses, 3)

    def test_resting_does_not_restore_a_dead_character(self):
        player = Player(hp=0, dead=True, second_wind_uses=0, hit_dice_remaining=0, action_surge_available=False)
        player.refresh_short_rest()
        player.long_rest()
        self.assertEqual((player.hp, player.second_wind_uses, player.hit_dice_remaining), (0, 0, 0))
        self.assertFalse(player.action_surge_available)
        self.assertTrue(player.dead)


class DeathSaveTests(unittest.TestCase):
    def test_ten_is_a_success_and_nine_is_a_failure(self):
        player = Player(hp=0)
        self.assertEqual(player.death_save(FixedRolls(10)), "success")
        self.assertEqual(player.death_save(FixedRolls(9)), "failure")
        self.assertEqual((player.death_save_successes, player.death_save_failures), (1, 1))
        self.assertTrue(player.is_alive)

    def test_natural_one_counts_two_failures(self):
        player = Player(hp=0)
        self.assertEqual(player.death_save(FixedRolls(1)), "failure")
        self.assertEqual(player.death_save_failures, 2)
        self.assertEqual(player.death_save(FixedRolls(9)), "dead")
        self.assertTrue(player.dead)

    def test_natural_twenty_restores_one_hp_and_clears_all_saves(self):
        player = Player(hp=0, death_save_successes=2, death_save_failures=2)
        self.assertEqual(player.death_save(FixedRolls(20)), "natural20")
        self.assertEqual(player.hp, 1)
        self.assertTrue(player.is_conscious)
        self.assertEqual((player.death_save_successes, player.death_save_failures), (0, 0))
        self.assertFalse(player.stable)

    def test_three_successes_stabilize_without_restoring_hp(self):
        player = Player(hp=0, death_save_failures=1)
        rng = FixedRolls(10, 12, 19)
        self.assertEqual(player.death_save(rng), "success")
        self.assertEqual(player.death_save(rng), "success")
        self.assertEqual(player.death_save(rng), "stable")
        self.assertTrue(player.stable)
        self.assertTrue(player.is_alive)
        self.assertFalse(player.is_conscious)
        self.assertEqual(player.hp, 0)
        self.assertEqual((player.death_save_successes, player.death_save_failures), (0, 0))
        self.assertEqual(player.death_save(FixedRolls()), "stable")

    def test_three_ordinary_failures_kill_even_with_two_successes(self):
        player = Player(hp=0, death_save_successes=2)
        rng = FixedRolls(2, 5, 9)
        self.assertEqual(player.death_save(rng), "failure")
        self.assertEqual(player.death_save(rng), "failure")
        self.assertEqual(player.death_save(rng), "dead")
        self.assertFalse(player.is_alive)

    def test_conscious_and_dead_characters_do_not_roll_death_saves(self):
        self.assertEqual(Player().death_save(FixedRolls()), "conscious")
        self.assertEqual(Player(hp=0, dead=True).death_save(FixedRolls()), "dead")


class EnemyTests(unittest.TestCase):
    def test_damage_clamps_at_zero_and_records_actual_loss(self):
        enemy = Enemy("Rat", 10, 10, 12, 2, (1, 4), 1, 50, 4)
        self.assertTrue(enemy.is_alive)
        self.assertEqual(enemy.take_damage(3), 3)
        self.assertEqual(enemy.hp, 7)
        self.assertEqual(enemy.take_damage(100), 7)
        self.assertEqual(enemy.hp, 0)
        self.assertFalse(enemy.is_alive)
        self.assertEqual(enemy.take_damage(1), 0)

    def test_negative_damage_is_rejected(self):
        enemy = Enemy("Rat", 10, 10, 12, 2, (1, 4), 1, 50, 4)
        with self.assertRaises(ValueError):
            enemy.take_damage(-1)
        self.assertEqual(enemy.hp, 10)


class DungeonTests(unittest.TestCase):
    def test_all_rooms_are_reachable_through_reciprocal_exits(self):
        offsets = {
            "north": (0, -1), "east": (1, 0),
            "south": (0, 1), "west": (-1, 0),
        }
        opposite = {
            "north": "south", "south": "north",
            "east": "west", "west": "east",
        }
        for seed in range(50):
            with self.subTest(seed=seed):
                dungeon = Dungeon(random.Random(seed))
                self.assertEqual(len(dungeon.rooms), 12)
                reached = set()
                frontier = [dungeon.start]
                while frontier:
                    position = frontier.pop()
                    if position in reached:
                        continue
                    reached.add(position)
                    room = dungeon.get_room(position)
                    self.assertEqual(room.position, position)
                    for direction, destination in room.exits.items():
                        self.assertIn(direction, offsets)
                        dx, dy = offsets[direction]
                        self.assertEqual(destination, (position[0] + dx, position[1] + dy))
                        neighbor = dungeon.get_room(destination)
                        self.assertEqual(neighbor.exits.get(opposite[direction]), position)
                        frontier.append(destination)
                self.assertEqual(reached, set(dungeon.rooms))

    def test_seed_reproduces_layout_and_encounters(self):
        first = Dungeon(random.Random(8675309))
        second = Dungeon(random.Random(8675309))
        self.assertEqual(first.rooms, second.rooms)

    def test_encounters_have_independent_mutable_health(self):
        first = Dungeon(random.Random(42))
        second = Dungeon(random.Random(42))
        enemies = [room.enemy for room in first.rooms.values() if room.enemy]
        self.assertEqual(len({id(enemy) for enemy in enemies}), len(enemies))
        first.get_room(first.boss_position).enemy.take_damage(1)
        other_boss = second.get_room(second.boss_position).enemy
        self.assertEqual(other_boss.hp, other_boss.max_hp)

    def test_safe_entrance_unique_boss_and_balanced_room_contents(self):
        for seed in range(50):
            with self.subTest(seed=seed):
                dungeon = Dungeon(random.Random(seed))
                self.assertEqual(dungeon.start, (0, 0))
                self.assertEqual(dungeon.boss_position, (3, 2))
                entrance = dungeon.get_room(dungeon.start)
                self.assertIsNone(entrance.enemy)
                self.assertIsNone(entrance.loot)
                boss_rooms = [room for room in dungeon.rooms.values() if room.enemy and room.enemy.boss]
                ordinary = [room for room in dungeon.rooms.values() if room.enemy and not room.enemy.boss]
                treasures = [room for room in dungeon.rooms.values() if room.loot and not room.enemy]
                self.assertEqual(len(boss_rooms), 1)
                self.assertEqual(boss_rooms[0].position, dungeon.boss_position)
                self.assertEqual(len(ordinary), 6)
                self.assertGreaterEqual(sum(room.enemy.xp_reward for room in ordinary), 300)
                self.assertEqual(len(treasures), 4)
                for room in dungeon.rooms.values():
                    if room.loot:
                        self.assertTrue(room.loot.has_treasure)

    def test_monsters_begin_alive_with_valid_combat_and_reward_stats(self):
        for seed in range(20):
            dungeon = Dungeon(random.Random(seed))
            for room in dungeon.rooms.values():
                if room.enemy:
                    with self.subTest(seed=seed, enemy=room.enemy.name):
                        enemy = room.enemy
                        self.assertTrue(enemy.name)
                        self.assertGreater(enemy.max_hp, 0)
                        self.assertEqual(enemy.hp, enemy.max_hp)
                        self.assertGreater(enemy.armor_class, 0)
                        self.assertGreater(enemy.attack_bonus, 0)
                        number, sides = enemy.damage_dice
                        self.assertGreater(number, 0)
                        self.assertGreater(sides, 1)
                        self.assertGreaterEqual(enemy.damage_bonus, 0)
                        self.assertGreater(enemy.xp_reward, 0)
                        self.assertGreaterEqual(enemy.gold_reward, 0)
                        self.assertTrue(enemy.is_alive)

    def test_every_dungeon_provides_potions_and_an_early_weapon_upgrade(self):
        for seed in range(50):
            with self.subTest(seed=seed):
                dungeon = Dungeon(random.Random(seed))
                loot_rooms = [room for room in dungeon.rooms.values() if room.loot]
                self.assertGreater(sum(room.loot.potions for room in loot_rooms), 0)
                upgrades = [room for room in loot_rooms if room.loot.weapon_bonus > Player().weapon_bonus]
                self.assertTrue(upgrades)
                adjacent = set(dungeon.get_room(dungeon.start).exits.values())
                self.assertTrue(any(room.position in adjacent for room in upgrades))
                for room in loot_rooms:
                    loot = room.loot
                    self.assertTrue(loot.has_treasure)
                    if loot.weapon_bonus:
                        self.assertTrue(loot.weapon_name)

    def test_map_hides_unvisited_contents_and_marks_current_room(self):
        dungeon = Dungeon(random.Random(9))
        rendered = "\n".join(dungeon.map_lines(dungeon.start))
        self.assertEqual(rendered.count("@"), 1)
        self.assertEqual(rendered.count("?"), 11)
        for marker in ("E", "B", "$"):
            self.assertNotIn(marker, rendered)

    def test_map_reveals_encounters_and_updates_cleared_rooms(self):
        dungeon = Dungeon(random.Random(9))
        enemy_room = next(room for room in dungeon.rooms.values() if room.enemy and not room.enemy.boss)
        treasure_room = next(room for room in dungeon.rooms.values() if room.loot and not room.enemy)
        boss_room = dungeon.get_room(dungeon.boss_position)
        for room in (enemy_room, treasure_room, boss_room):
            room.visited = True

        rendered = "\n".join(dungeon.map_lines(dungeon.start))
        self.assertEqual(rendered.count("E"), 1)
        self.assertEqual(rendered.count("B"), 1)
        self.assertEqual(rendered.count("$"), 1)
        self.assertEqual(rendered.count("?"), 8)

        enemy_room.enemy.take_damage(enemy_room.enemy.hp)
        treasure_room.looted = True
        rendered = "\n".join(dungeon.map_lines(enemy_room.position))
        self.assertEqual(rendered.count("@"), 1)
        self.assertNotIn("E", rendered)
        self.assertNotIn("$", rendered)
        self.assertIn(".", rendered)


class LootTests(unittest.TestCase):
    def test_negative_loot_amounts_are_rejected(self):
        for field in ("gold", "potions", "weapon_bonus"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    Loot(**{field: -1})


if __name__ == "__main__":
    unittest.main()
