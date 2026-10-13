"""Each dungeon depth has a complete, independent roster of themed foes."""

from dataclasses import FrozenInstanceError, asdict
import random
import unittest

from campaign import FLOORS
from dungeon import Dungeon
from monster_catalog import FLOOR_MONSTERS, MONSTERS_BY_NAME, floor_roster
from room_library import ENEMY_TEMPLATES, make_enemy, make_floor_enemies


class FloorMonsterCatalogTests(unittest.TestCase):
    def test_each_floor_has_six_species_without_reusing_other_floors(self):
        self.assertEqual(set(FLOOR_MONSTERS), set(range(1, len(FLOORS) + 1)))
        all_names = []
        for floor in range(1, len(FLOORS) + 1):
            with self.subTest(floor=floor):
                roster = floor_roster(floor)
                self.assertEqual(len(roster), 6)
                self.assertEqual(len({spec.name for spec in roster}), 6)
                all_names.extend(spec.name for spec in roster)
        self.assertEqual(len(all_names), 30)
        self.assertEqual(len(set(all_names)), 30)
        self.assertEqual(set(MONSTERS_BY_NAME), set(all_names))
        self.assertTrue(set(all_names).isdisjoint(theme.guardian for theme in FLOORS))
        for roster in FLOOR_MONSTERS.values():
            for spec in roster:
                self.assertEqual(MONSTERS_BY_NAME[spec.name], spec)

    def test_first_floor_keeps_the_original_species_and_combat_balance(self):
        original_templates = (
            ("Crypt Rat", 5, 11, 2, (1, 4), 1, 50, 4),
            ("Bone Sentry", 8, 13, 3, (1, 6), 1, 50, 6),
            ("Grave Marauder", 9, 12, 3, (1, 6), 1, 50, 7),
            ("Hollow Acolyte", 7, 11, 2, (1, 4), 1, 50, 8),
            ("Restless Knight", 10, 13, 3, (1, 6), 1, 100, 9),
            ("Catacomb Stalker", 11, 12, 3, (1, 6), 1, 100, 10),
        )
        self.assertEqual(ENEMY_TEMPLATES, original_templates)
        catalog_templates = tuple(
            (spec.name, spec.hp, spec.armor_class, spec.attack_bonus,
             spec.damage_dice, spec.damage_bonus, spec.xp_reward, spec.gold_reward)
            for spec in floor_roster(1)
        )
        self.assertEqual(catalog_templates, original_templates)
        self.assertTrue(all(spec.initiative_bonus == 0 for spec in floor_roster(1)))

    def test_species_have_authored_profiles_and_different_combat_statistics(self):
        descriptions = set()
        for floor, roster in FLOOR_MONSTERS.items():
            with self.subTest(floor=floor):
                combat_profiles = {
                    (spec.hp, spec.armor_class, spec.attack_bonus,
                     spec.damage_dice, spec.damage_bonus, spec.initiative_bonus)
                    for spec in roster
                }
                self.assertGreaterEqual(len(combat_profiles), 4)
                self.assertGreaterEqual(len({spec.hp for spec in roster}), 3)
                self.assertGreaterEqual(len({spec.armor_class for spec in roster}), 2)
                for spec in roster:
                    with self.subTest(species=spec.name):
                        self.assertGreater(len(spec.description.split()), 8)
                        self.assertTrue(spec.tactics.strip())
                        self.assertTrue(spec.strike.strip())
                        self.assertTrue(spec.surface.strip())
                        self.assertNotIn(spec.description, descriptions)
                        descriptions.add(spec.description)
                        if floor > 1:
                            self.assertTrue(spec.fumble.strip())

    def test_rosters_preserve_the_campaign_experience_curve(self):
        for floor, roster in FLOOR_MONSTERS.items():
            with self.subTest(floor=floor):
                self.assertEqual(sum(spec.xp_reward for spec in roster), 400)

    def test_catalog_is_immutable_and_rejects_invalid_floor_numbers(self):
        spec = floor_roster(1)[0]
        with self.assertRaises(FrozenInstanceError):
            spec.hp = 0
        for floor in (0, -1, 6, 100, True, False, 1.0, "1", None):
            with self.subTest(floor=floor):
                with self.assertRaises((TypeError, ValueError)):
                    floor_roster(floor)


class FloorMonsterFactoryTests(unittest.TestCase):
    def test_single_foe_factory_chooses_only_from_the_requested_floor(self):
        for floor in range(1, len(FLOORS) + 1):
            expected_names = {spec.name for spec in floor_roster(floor)}
            for seed in range(12):
                with self.subTest(floor=floor, seed=seed):
                    enemy = make_enemy(random.Random(seed), floor)
                    self.assertIn(enemy.name, expected_names)
                    spec = MONSTERS_BY_NAME[enemy.name]
                    self.assertEqual((enemy.hp, enemy.max_hp), (spec.hp, spec.hp))
                    self.assertEqual(enemy.initiative_bonus, spec.initiative_bonus)
                    self.assertFalse(enemy.boss)
        self.assertEqual(make_enemy(random.Random(42)),
                         make_enemy(random.Random(42), 1))

    def test_full_floor_factory_is_seeded_but_varies_encounter_order(self):
        for floor in range(1, len(FLOORS) + 1):
            with self.subTest(floor=floor):
                first = make_floor_enemies(random.Random(42), floor)
                second = make_floor_enemies(random.Random(42), floor)
                self.assertEqual(first, second)
                self.assertEqual(len(first), 6)
                self.assertEqual({enemy.name for enemy in first},
                                 {spec.name for spec in floor_roster(floor)})
                self.assertTrue(all(a is not b for a, b in zip(first, second)))
                orders = {
                    tuple(enemy.name for enemy in make_floor_enemies(random.Random(seed), floor))
                    for seed in range(8)
                }
                self.assertGreater(len(orders), 1)

    def test_foe_damage_cannot_change_other_instances_or_future_generations(self):
        for floor in range(1, len(FLOORS) + 1):
            with self.subTest(floor=floor):
                first = make_floor_enemies(random.Random(7), floor)
                pristine = make_floor_enemies(random.Random(7), floor)
                first[0].take_damage(first[0].hp)
                first[0].armor_class = 99
                first[0].damage_bonus = 99
                first[0].initiative_bonus = 99
                self.assertEqual(first[1:], pristine[1:])
                self.assertEqual(make_floor_enemies(random.Random(7), floor), pristine)
                spec = MONSTERS_BY_NAME[first[0].name]
                self.assertEqual(pristine[0].hp, spec.hp)
                self.assertEqual(pristine[0].armor_class, spec.armor_class)
                self.assertEqual(pristine[0].damage_bonus, spec.damage_bonus)
                self.assertEqual(pristine[0].initiative_bonus, spec.initiative_bonus)

    def test_factories_reject_unknown_floor_numbers(self):
        for factory in (make_enemy, make_floor_enemies):
            for floor in (0, 6, True, "2"):
                with self.subTest(factory=factory.__name__, floor=floor):
                    with self.assertRaises((TypeError, ValueError)):
                        factory(random.Random(0), floor)


class DungeonFloorMonsterTests(unittest.TestCase):
    def test_every_layout_contains_all_six_floor_species_and_its_own_guardian(self):
        for floor, theme in enumerate(FLOORS, start=1):
            expected_names = {spec.name for spec in floor_roster(floor)}
            for seed in range(12):
                for class_id in ("fighter", "rogue", "wizard"):
                    with self.subTest(floor=floor, seed=seed, class_id=class_id):
                        dungeon = Dungeon(random.Random(seed), floor, class_id)
                        enemies = [room.enemy for room in dungeon.rooms.values() if room.enemy]
                        ordinary = [enemy for enemy in enemies if not enemy.boss]
                        guardians = [enemy for enemy in enemies if enemy.boss]
                        self.assertEqual(len(ordinary), 6)
                        self.assertEqual({enemy.name for enemy in ordinary}, expected_names)
                        self.assertEqual([enemy.name for enemy in guardians], [theme.guardian])
                        self.assertEqual(len({id(enemy) for enemy in enemies}), 7)
                        self.assertIsNone(dungeon.get_room(dungeon.start).enemy)
                        self.assertIs(dungeon.get_room(dungeon.boss_position).enemy, guardians[0])

    def test_species_base_statistics_are_scaled_once_at_their_actual_depth(self):
        for floor in range(1, len(FLOORS) + 1):
            dungeon = Dungeon(random.Random(42), floor)
            depth = floor - 1
            for room in dungeon.rooms.values():
                enemy = room.enemy
                if enemy is None or enemy.boss:
                    continue
                with self.subTest(floor=floor, species=enemy.name):
                    spec = MONSTERS_BY_NAME[enemy.name]
                    self.assertEqual(enemy.max_hp, spec.hp + 5 * depth)
                    self.assertEqual(enemy.hp, enemy.max_hp)
                    self.assertEqual(enemy.armor_class, spec.armor_class + depth)
                    self.assertEqual(enemy.attack_bonus, spec.attack_bonus + depth)
                    self.assertEqual(enemy.damage_dice, spec.damage_dice)
                    self.assertEqual(enemy.damage_bonus, spec.damage_bonus + depth)
                    self.assertEqual(enemy.initiative_bonus, spec.initiative_bonus)
                    self.assertEqual(enemy.xp_reward, spec.xp_reward * floor)
                    self.assertEqual(enemy.gold_reward, spec.gold_reward * floor)

    def test_depth_rosters_and_layouts_are_repeatable_without_shared_combat_state(self):
        for floor in range(1, len(FLOORS) + 1):
            with self.subTest(floor=floor):
                first = Dungeon(random.Random(8675309), floor)
                second = Dungeon(random.Random(8675309), floor)
                self.assertEqual(first.rooms, second.rooms)
                ordinary = next(room.enemy for room in first.rooms.values()
                                if room.enemy and not room.enemy.boss)
                untouched = {room.enemy.name: asdict(room.enemy)
                             for room in second.rooms.values() if room.enemy}
                ordinary.take_damage(ordinary.hp)
                self.assertEqual({room.enemy.name: asdict(room.enemy)
                                  for room in second.rooms.values() if room.enemy}, untouched)
                fresh = Dungeon(random.Random(8675309), floor)
                self.assertEqual(fresh.rooms, second.rooms)

    def test_floor_rewards_keep_all_classes_on_the_existing_level_curve(self):
        total_xp = 0
        for floor in range(1, len(FLOORS) + 1):
            dungeon = Dungeon(random.Random(0), floor)
            floor_xp = sum(room.enemy.xp_reward for room in dungeon.rooms.values() if room.enemy)
            self.assertEqual(floor_xp, 600 * floor)
            total_xp += floor_xp
        self.assertEqual(total_xp, 9000)


if __name__ == "__main__":
    unittest.main()
