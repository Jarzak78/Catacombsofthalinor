"""Display-only attack animations must reflect the engine's resolved outcome."""

import copy
import math
import random
import unittest

from combat_animation import FX_TAG, animation_frame, classify_reaction, draw_combat_effects


def attack(**changes):
    event = {
        "id": 1, "source": "player", "kind": "weapon", "floor": 1,
        "position": [1, 2], "enemy": {"name": "Bone Sentry", "boss": False},
        "roll": 12, "total": 16, "ac": 14, "hit": True,
        "critical": False, "fumble": False, "near_miss": False,
        "damage": 8, "target_hp_before": 20, "target_hp_after": 12,
        "target_max_hp": 20, "killed": False, "self_damage": 0,
        "enemy_hp_before": 20, "enemy_hp_after": 12, "enemy_max_hp": 20,
        "enemy_killed": False, "player_killed": False,
    }
    event.update(changes)
    return event


class RecordingCanvas:
    def __init__(self):
        self.items = []
        self.deletions = []

    def delete(self, tag):
        self.deletions.append(tag)
        self.items = [item for item in self.items if tag not in item[2].get("tags", ())]

    def _create(self, name, coords, options):
        self.items.append((name, coords, options))
        return len(self.items)

    def create_line(self, *coords, **options):
        return self._create("line", coords, options)

    def create_oval(self, *coords, **options):
        return self._create("oval", coords, options)

    def create_text(self, *coords, **options):
        return self._create("text", coords, options)


class ReactionTests(unittest.TestCase):
    def test_damage_severity_matches_each_flavor_band_boundary(self):
        for damage, expected in ((0, "brace"), (1, "brace"), (5, "brace"),
                                 (6, "flinch"), (10, "flinch"), (11, "stagger"),
                                 (15, "stagger"), (16, "reel"), (80, "reel")):
            with self.subTest(damage=damage):
                self.assertEqual(classify_reaction(attack(damage=damage)), expected)

    def test_near_miss_blocks_and_wide_miss_dodges(self):
        for total, expected in ((13, "block"), (12, "block"), (11, "dodge"), (3, "dodge")):
            with self.subTest(total=total):
                self.assertEqual(classify_reaction(attack(hit=False, total=total, damage=0)), expected)
        self.assertEqual(classify_reaction(attack(hit=False, total=None, near_miss=True)), "block")
        self.assertEqual(classify_reaction(attack(hit=False, total=None)), "dodge")

    def test_selected_natural_one_stumbles_without_moving_foe(self):
        event = attack(roll=1, total=5, hit=False, fumble=True, damage=0, self_damage=1)
        frame = animation_frame(event, .65)
        self.assertEqual(frame["pose"], "fumble")
        self.assertGreater(frame["hands_dy"], 0)
        self.assertLess(frame["hands_angle"], 0)
        self.assertEqual(frame["enemy_dx"], 0)
        self.assertEqual(frame["enemy_dy"], 0)
        self.assertFalse(frame["critical"])

    def test_small_critical_has_small_reaction_and_distinct_critical_effect(self):
        normal = animation_frame(attack(damage=3), .65)
        critical = animation_frame(attack(damage=3, roll=20, critical=True), .65)
        heavy = animation_frame(attack(damage=18), .65)
        self.assertEqual(critical["pose"], "brace")
        self.assertTrue(critical["critical"])
        self.assertGreater(abs(critical["enemy_dx"]), abs(normal["enemy_dx"]))
        self.assertLess(abs(critical["enemy_dx"]), abs(heavy["enemy_dx"]) / 3)
        canvas = RecordingCanvas()
        draw_combat_effects(canvas, 1000, 400, critical)
        self.assertTrue(any("fx-critical" in options["tags"] for _, _, options in canvas.items))

    def test_accuracy_changes_motion_without_overriding_damage(self):
        edge = animation_frame(attack(total=14, damage=10), .65)
        precise = animation_frame(attack(total=19, damage=10), .65)
        self.assertEqual(edge["pose"], precise["pose"])
        self.assertEqual(edge["accuracy"], "edge")
        self.assertEqual(precise["accuracy"], "precise")
        self.assertGreater(abs(precise["enemy_dx"]), abs(edge["enemy_dx"]))

    def test_enemy_attack_lunges_without_claiming_foe_was_hit(self):
        event = attack(source="enemy", damage=12)
        frame = animation_frame(event, .42)
        self.assertEqual(frame["pose"], "incoming")
        self.assertGreater(frame["enemy_dy"], 0)
        self.assertGreater(frame["enemy_scale_x"], 1)
        self.assertEqual(classify_reaction(attack(source="enemy", hit=False)), "parry")
        self.assertEqual(classify_reaction(attack(source="enemy", hit=False, fumble=True)),
                         "enemy_fumble")

    def test_only_enemy_death_collapses_the_enemy(self):
        player_kill = attack(killed=True, enemy_killed=True, target_hp_after=0)
        enemy_fumble = attack(source="enemy", hit=False, fumble=True,
                              damage=0, self_damage=1, enemy_killed=True)
        for event in (player_kill, enemy_fumble):
            with self.subTest(source=event["source"]):
                start = animation_frame(event, 0)
                end = animation_frame(event, 1)
                self.assertEqual(start["enemy_opacity"], 1)
                self.assertEqual(end["pose"], "collapse")
                self.assertEqual(end["enemy_opacity"], 0)
                self.assertGreater(end["enemy_dy"], start["enemy_dy"])
                self.assertLess(end["enemy_scale_y"], start["enemy_scale_y"])
        lethal_enemy = attack(source="enemy", killed=True, player_killed=True)
        self.assertEqual(classify_reaction(lethal_enemy), "incoming")
        self.assertEqual(animation_frame(lethal_enemy, 1)["enemy_opacity"], 1)

    def test_defensive_spells_do_not_make_foe_react(self):
        for kind in ("armor", "shield"):
            frame = animation_frame(attack(kind=kind, hit=False, damage=0), .5)
            with self.subTest(kind=kind):
                self.assertEqual(frame["pose"], "buff")
                self.assertEqual(frame["enemy_dx"], 0)
                self.assertEqual(frame["enemy_angle"], 0)
                self.assertEqual(frame["enemy_opacity"], 1)


class TimelineTests(unittest.TestCase):
    def test_endpoints_reset_all_living_transforms(self):
        events = [attack(), attack(damage=20), attack(hit=False, total=2),
                  attack(hit=False, fumble=True), attack(source="enemy"),
                  attack(kind="firebolt"), attack(kind="shield", hit=False)]
        neutral = {"enemy_dx": 0, "enemy_dy": 0, "enemy_angle": 0,
                   "enemy_scale_x": 1, "enemy_scale_y": 1, "enemy_opacity": 1,
                   "hands_dx": 0, "hands_dy": 0, "hands_angle": 0, "hands_scale": 1,
                   "offhand_dx": 0, "offhand_dy": 0,
                   "offhand_angle": 0, "offhand_scale": 1}
        for event in events:
            for progress in (0, 1):
                with self.subTest(kind=event["kind"], pose=classify_reaction(event), p=progress):
                    frame = animation_frame(event, progress)
                    self.assertEqual({key: frame[key] for key in neutral}, neutral)

    def test_progress_is_clamped_and_nonfinite_values_are_neutral(self):
        for value, expected in ((-3, 0), (3, 1), (float("nan"), 0),
                                (float("inf"), 0), (None, 0), ("half", 0)):
            with self.subTest(value=value):
                frame = animation_frame(attack(), value)
                self.assertEqual(frame["progress"], expected)
                self.assertTrue(all(math.isfinite(value) for value in frame.values()
                                    if isinstance(value, (int, float))))

    def test_display_is_deterministic_without_consuming_rng_or_mutating_event(self):
        event = attack(damage=12, roll=17)
        before = copy.deepcopy(event)
        rng_before = random.getstate()
        frames = [animation_frame(event, i / 20) for i in range(21)]
        canvas = RecordingCanvas()
        for frame in frames:
            draw_combat_effects(canvas, 900, 360, frame)
        self.assertEqual(event, before)
        self.assertEqual(random.getstate(), rng_before)
        self.assertEqual(frames, [animation_frame(event, i / 20) for i in range(21)])
        frames[0]["enemy_angle"] = 123
        self.assertEqual(animation_frame(event, 0)["enemy_angle"], 0)

    def test_raster_pose_keys_are_bounded_but_translation_moves_smoothly(self):
        for event in (attack(damage=18), attack(killed=True), attack(source="enemy")):
            frames = [animation_frame(event, i / 100) for i in range(101)]
            enemy_keys = {(f["enemy_angle"], f["enemy_scale_x"], f["enemy_scale_y"],
                           f["enemy_opacity"]) for f in frames}
            hand_keys = {(f["hands_angle"], f["hands_scale"]) for f in frames}
            offhand_keys = {(f["offhand_angle"], f["offhand_scale"]) for f in frames}
            with self.subTest(pose=classify_reaction(event)):
                self.assertLessEqual(len(enemy_keys), 4)
                self.assertLessEqual(len(hand_keys), 4)
                self.assertLessEqual(len(offhand_keys), 4)
                self.assertGreater(len({f["enemy_dy"] for f in frames}), 5)


class EffectGeometryTests(unittest.TestCase):
    def render(self, event, progress=.4):
        canvas = RecordingCanvas()
        draw_combat_effects(canvas, 1000, 400, animation_frame(event, progress))
        return canvas

    def test_weapon_has_a_sweep_and_moving_hands(self):
        canvas = self.render(attack())
        sweeps = [coords for _, coords, options in canvas.items if "fx-weapon" in options["tags"]]
        self.assertEqual(len(sweeps), 2)
        self.assertGreater(max(sweeps[0][::2]) - min(sweeps[0][::2]), 80)
        early = animation_frame(attack(), .3)
        late = animation_frame(attack(), .5)
        self.assertNotEqual(early["hands_dx"], late["hands_dx"])
        self.assertNotEqual(early["hands_angle"], late["hands_angle"])

    def test_sword_crosses_foe_torso_while_shield_retracts_independently(self):
        frame = animation_frame(attack(), .5)
        # Reference points from the current sword art, on the 1000x400 stage:
        # the blade begins on the right and rotates around its lower forearm.
        # Project its visible segment, rather than merely asserting an angle.
        pivot = (695, 403)

        def transformed(x, y):
            angle = math.radians(frame["hands_angle"])
            x, y = x - pivot[0], y - pivot[1]
            return (pivot[0] + x * math.cos(angle) - y * math.sin(angle) + frame["hands_dx"],
                    pivot[1] + x * math.sin(angle) + y * math.cos(angle) + frame["hands_dy"])

        tip, hilt = transformed(553, 188), transformed(632, 314)
        self.assertLess(tip[0], 500)
        self.assertGreater(hilt[0], 500)
        crossing_y = tip[1] + (500 - tip[0]) / (hilt[0] - tip[0]) * (hilt[1] - tip[1])
        self.assertGreater(crossing_y, 180)
        self.assertLess(crossing_y, 270)
        self.assertLess(hilt[1], 314)
        self.assertLess(frame["hands_dy"], 0)
        self.assertGreater(frame["offhand_dy"], 0)
        self.assertLess(frame["offhand_scale"], 1)
        self.assertNotEqual(frame["hands_angle"], frame["offhand_angle"])

    def test_wizard_projectiles_are_distinct_and_missile_has_three_orbs(self):
        fire = self.render(attack(kind="firebolt"))
        frost = self.render(attack(kind="frost"))
        missile = self.render(attack(kind="missile"))
        count_orbs = lambda c: sum(name == "oval" and "fx-spell" in opts["tags"]
                                   for name, _, opts in c.items)
        self.assertEqual(count_orbs(fire), 1)
        self.assertEqual(count_orbs(frost), 0)
        self.assertEqual(count_orbs(missile), 3)
        colors = [{opts["fill"] for _, _, opts in c.items if "fx-spell" in opts["tags"]}
                  for c in (fire, frost, missile)]
        self.assertNotEqual(colors[0], colors[1])
        self.assertNotEqual(colors[1], colors[2])
        self.assertFalse(any("fx-weapon" in opts["tags"] for _, _, opts in fire.items))

    def test_fireball_expands_around_foe_and_buffs_stay_near_hands(self):
        early = self.render(attack(kind="fireball"), .5)
        late = self.render(attack(kind="fireball"), .8)
        rings = lambda c: [coords for name, coords, opts in c.items
                           if name == "oval" and "fx-spell" in opts["tags"]]
        self.assertEqual(len(rings(early)), 2)
        self.assertGreater(rings(late)[0][2] - rings(late)[0][0],
                           rings(early)[0][2] - rings(early)[0][0])
        ward = self.render(attack(kind="shield", hit=False, damage=0), .5)
        self.assertTrue(all("fx-ward" in opts["tags"] for _, _, opts in ward.items))

    def test_damage_numbers_use_resolved_damage_and_never_appear_on_misses(self):
        hit = self.render(attack(damage=3), .65)
        numbers = [opts["text"] for name, _, opts in hit.items if name == "text"]
        self.assertEqual(numbers, ["3"])
        for event in (attack(hit=False, damage=0), attack(hit=False, fumble=True, damage=0),
                      attack(source="enemy", damage=7)):
            self.assertFalse(any(name == "text" for name, _, _ in self.render(event, .65).items))

    def test_effects_do_not_accumulate_or_delete_background(self):
        canvas = RecordingCanvas()
        canvas.items.append(("background", (), {"tags": ("dungeon-view",)}))
        frame = animation_frame(attack(kind="missile", critical=True), .5)
        draw_combat_effects(canvas, 1000, 400, frame)
        count = len(canvas.items)
        draw_combat_effects(canvas, 1000, 400, frame)
        self.assertEqual(len(canvas.items), count)
        draw_combat_effects(canvas, 1000, 400, None)
        self.assertEqual(canvas.items, [("background", (), {"tags": ("dungeon-view",)})])
        self.assertEqual(canvas.deletions, [FX_TAG, FX_TAG, FX_TAG])

    def test_all_effect_geometry_stays_local_finite_and_bounded(self):
        events = [attack(kind=kind, critical=True) for kind in
                  ("weapon", "firebolt", "frost", "missile", "fireball", "ember", "armor", "shield")]
        events += [attack(source="enemy"), attack(hit=False, fumble=True, damage=0),
                   attack(hit=False, total=13, damage=0)]
        for event in events:
            for i in range(21):
                canvas = self.render(event, i / 20)
                with self.subTest(kind=event["kind"], source=event["source"], p=i / 20):
                    self.assertLessEqual(len(canvas.items), 20)
                    if i in (0, 20):
                        self.assertEqual(canvas.items, [])
                    for _, coords, options in canvas.items:
                        self.assertIn(FX_TAG, options["tags"])
                        for n, value in enumerate(coords):
                            self.assertTrue(math.isfinite(value))
                            self.assertGreaterEqual(value, 0)
                            self.assertLessEqual(value, 1000 if n % 2 == 0 else 400)


if __name__ == "__main__":
    unittest.main()
