"""Deterministic reaction poses and original Canvas effects for resolved attacks.

The engine supplies the outcome.  These helpers only turn that public result
and a normalized display progress into a pose; they never roll dice, schedule a
callback, change HP, or inspect a live game.  Coordinates use a 1000x400 stage.
"""

from math import cos, isfinite, pi, sin


FX_TAG = "combat-fx"
ANIMATION_MS = 640
_SPELLS = {"firebolt", "frost", "missile", "fireball", "ember"}
_COLORS = {"firebolt": "#f3a14a", "frost": "#a6e5f4",
           "missile": "#c0abff", "fireball": "#ffb364",
           "ember": "#ed9852", "armor": "#91c8ed", "shield": "#a6d9ef"}


def _number(value, default=0):
    if isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value):
        return value
    return default


def _clamp(value, low=0.0, high=1.0):
    return min(high, max(low, value))


def _pulse(progress, start, end):
    if progress <= start or progress >= end:
        return 0.0
    return sin(pi * (progress - start) / (end - start))


def _ease(value):
    value = _clamp(value)
    return value * value * (3 - 2 * value)


def _level(value):
    """Four strengths keep raster pose caches small; position can stay smooth."""
    return round(_clamp(value) * 3) / 3


def _accuracy(event):
    if event.get("critical") and event.get("hit"):
        return "critical"
    total, ac = event.get("total"), event.get("ac")
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool)
               and isfinite(value) for value in (total, ac)):
        return "automatic"
    margin = total - ac
    if not event.get("hit"):
        return "near" if 1 <= -margin <= 2 else "wide"
    if margin <= 1:
        return "edge"
    return "precise" if margin >= 5 else "normal"


def classify_reaction(event):
    """Choose a pose from the actual result, not from attack prose.

    A small critical hit remains a shallow brace, accompanied by a critical
    effect.  Damage, including save/mitigation reductions, controls severity.
    """
    if event.get("kind") in ("armor", "shield"):
        return "buff"
    enemy_died = bool(event.get("enemy_killed")) or (
        event.get("source", "player") == "player" and bool(event.get("killed")))
    if enemy_died:
        return "collapse"
    if event.get("source", "player") == "enemy":
        if event.get("fumble"):
            return "enemy_fumble"
        return "incoming" if event.get("hit") else "parry"
    if event.get("fumble"):
        return "fumble"
    if not event.get("hit"):
        return "block" if event.get("near_miss") or _accuracy(event) == "near" else "dodge"
    damage = max(0, _number(event.get("damage")))
    if damage <= 5:
        return "brace"
    if damage <= 10:
        return "flinch"
    if damage <= 15:
        return "stagger"
    return "reel"


def animation_frame(event, progress):
    """Return display-only transforms for one point in a 640 ms attack.

    ``enemy_*``, ``hands_*`` (weapon arm), and ``offhand_*`` translations are
    in 1000x400 stage pixels; angles are degrees and scales/opacity are unit
    factors.  The weapon and offhand use their own forearm pivots.  Ordinary
    attacks start/end neutral.  A defeated enemy finishes collapsed and
    transparent.  Raster envelopes have four key strengths to avoid resampling
    every tick.
    """
    p = _clamp(_number(progress))
    reaction = classify_reaction(event)
    source = event.get("source", "player")
    kind = event.get("kind", "weapon")
    accuracy = _accuracy(event)
    damage = max(0, int(_number(event.get("damage"))))
    frame = {
        "enemy_dx": 0.0, "enemy_dy": 0.0,
        "enemy_scale_x": 1.0, "enemy_scale_y": 1.0,
        "enemy_angle": 0.0, "enemy_opacity": 1.0,
        "hands_dx": 0.0, "hands_dy": 0.0,
        "hands_angle": 0.0, "hands_scale": 1.0,
        "offhand_dx": 0.0, "offhand_dy": 0.0,
        "offhand_angle": 0.0, "offhand_scale": 1.0,
        "pose": reaction, "reaction": reaction, "progress": p,
        "kind": kind, "source": source, "damage": damage,
        "critical": bool(event.get("critical") and event.get("hit")),
        "hit": bool(event.get("hit")), "accuracy": accuracy,
        "enemy_dying": reaction == "collapse",
        "impact": _pulse(p, .36, .94),
        "travel": _clamp((p - .16) / .32),
        "effect_color": _COLORS.get(kind, "#f1cf8b"),
    }
    if p == 0:
        return frame
    if p == 1 and reaction != "collapse":
        return frame

    wave = _pulse(p, .34, 1.0)
    strength = _level(wave)
    frame["pose_strength"] = strength
    sign = -1 if int(_number(event.get("roll"), 2)) % 2 else 1
    if source == "player" and kind == "weapon":
        # The right forearm advances toward the foe while the shield pulls
        # down/back.  A negative angle sweeps the left-pointing blade inward;
        # rotating both arms together instead makes the shield lead the blow.
        guard = _pulse(p, .12, .94)
        guard_strength = _level(guard)
        frame.update(offhand_dx=-18 * guard, offhand_dy=24 * guard,
                     offhand_angle=-6 * guard_strength,
                     offhand_scale=1 - .1 * guard_strength)
        if p < .22:
            frame.update(hands_dx=11 * _pulse(p, 0, .22), hands_dy=8 * _pulse(p, 0, .22),
                         hands_angle=12 if p >= .06 else 0)
        elif p < .56:
            swing = _ease((p - .22) / .34)
            frame.update(hands_dx=-34 * swing, hands_dy=-70 * swing,
                         hands_angle=-24 if p >= .36 else -12)
        else:
            recovery = 1 - _ease((p - .56) / .44)
            frame.update(hands_dx=-34 * recovery, hands_dy=-70 * recovery,
                         hands_angle=-12 if p < .82 else 0)
    elif source == "player" and kind in _SPELLS:
        thrust = _pulse(p, .08, .84)
        frame.update(hands_dx=-9 * thrust, hands_dy=-15 * thrust,
                     hands_angle=0, hands_scale=1.0)
    if reaction == "fumble":
        frame.update(hands_dx=13 * wave, hands_dy=26 * wave,
                     hands_angle=-12 * strength)
    elif reaction in ("brace", "flinch", "stagger", "reel"):
        amplitude, tilt = {"brace": (4, 0), "flinch": (10, 6),
                           "stagger": (22, 12), "reel": (35, 18)}[reaction]
        precision = 1.10 if accuracy == "precise" else .85 if accuracy == "edge" else 1
        if frame["critical"]:
            precision *= 1.12
        frame.update(enemy_dx=sign * amplitude * precision * wave,
                     enemy_dy=(2 if reaction == "brace" else 5) * wave,
                     enemy_angle=sign * tilt * strength)
        if reaction in ("stagger", "reel"):
            frame["enemy_scale_y"] = 1 - .1 * strength
    elif reaction == "block":
        frame.update(enemy_dx=-sign * 8 * wave, enemy_angle=-sign * 6 * strength)
    elif reaction == "dodge":
        frame.update(enemy_dx=sign * 43 * wave, enemy_angle=sign * 12 * strength)
    elif reaction == "enemy_fumble":
        frame.update(enemy_dx=-12 * wave, enemy_dy=9 * wave, enemy_angle=-12 * strength)
    elif reaction in ("incoming", "parry"):
        lunge = _pulse(p, .10, .68)
        frame.update(enemy_dy=18 * lunge, enemy_scale_x=1 + .1 * _level(lunge),
                     enemy_scale_y=1 + .1 * _level(lunge))
        if reaction == "incoming":
            frame.update(hands_dy=12 * wave, hands_angle=-12 * strength)
    elif reaction == "buff":
        frame["hands_dy"] = -8 * _pulse(p, .05, .95)

    if reaction == "collapse":
        fall = _ease((p - .43) / .57)
        level = _level(fall)
        frame.update(enemy_dx=sign * 14 * fall, enemy_dy=64 * fall,
                     enemy_angle=sign * 72 * level,
                     enemy_scale_x=1 + .1 * level,
                     enemy_scale_y=1 - .6 * level,
                     enemy_opacity=1 - level)
    return frame


def draw_combat_effects(canvas, width, height, frame):
    """Paint a brief localized swing, projectile, impact, or protective ward."""
    canvas.delete(FX_TAG)
    if not frame or width <= 0 or height <= 0:
        return
    p = frame.get("progress", 0)
    if not 0 < p < 1:
        return
    sx, sy = width / 1000, height / 400
    kind, source = frame.get("kind", "weapon"), frame.get("source", "player")
    reaction, color = frame.get("reaction", ""), frame.get("effect_color", "#f1cf8b")
    travel, impact = frame.get("travel", 0), frame.get("impact", 0)

    def line(coords, fill, weight=2, tag="fx-impact"):
        values = [value * (sx if i % 2 == 0 else sy) for i, value in enumerate(coords)]
        canvas.create_line(*values, fill=fill, width=max(1, weight * min(sx, sy)),
                           capstyle="round", joinstyle="round", tags=(FX_TAG, tag))

    def oval(x, y, rx, ry, fill="", outline="", weight=2, tag="fx-projectile"):
        canvas.create_oval((x - rx) * sx, (y - ry) * sy, (x + rx) * sx, (y + ry) * sy,
                           fill=fill, outline=outline, width=max(1, weight * min(sx, sy)),
                           tags=(FX_TAG, tag))

    if source == "player" and kind == "weapon" and .16 < p < .69:
        # Only a few points trace the visible part of the blade's sweep.
        positions = []
        start, end = max(0, travel - .42), min(1, travel + .03)
        for i in range(7):
            t = start + (end - start) * i / 6
            positions.extend((650 - 215 * t, 155 + 57 * t - 25 * sin(pi * t)))
        line(positions, "#a98e61", 7, "fx-weapon")
        line(positions, "#f2e2bb", 2, "fx-weapon")
    elif source == "player" and kind in ("firebolt", "frost", "missile") and .13 < p < .56:
        count = 3 if kind == "missile" else 1
        for i in range(count):
            t = _clamp(travel - i * .11)
            bend = (i - 1) * 30 * sin(pi * t) if count == 3 else 0
            x, y = 748 - 248 * t + bend, 303 - 108 * t
            line((x + 25, y + 10, x, y), color, 4, "fx-spell")
            if kind == "frost":
                line((x - 11, y, x + 11, y), "#e3faff", 3, "fx-spell")
                line((x, y - 10, x, y + 10), color, 2, "fx-spell")
            else:
                oval(x, y, 10, 7, color, "#fff0ce", 1, "fx-spell")
    elif source == "player" and kind in ("fireball", "ember"):
        if .12 < p < .47:
            x, y = 747 - 247 * travel, 303 - 108 * travel
            oval(x, y, 10 + travel * 8, 9 + travel * 7, color, "#ffe8b4", 2, "fx-spell")
        if .42 < p < .9:
            radius = 14 + 90 * _clamp((p - .42) / .48)
            oval(500, 196, radius, radius * .65, "", color, 4, "fx-spell")
            oval(500, 196, radius * .72, radius * .45, "", "#ffe5a8", 2, "fx-spell")
    elif kind in ("armor", "shield"):
        radius = 58 + 36 * sin(pi * p)
        oval(625, 286, radius, radius * .9, "", color, 3, "fx-ward")
        for i in range(6):
            a = i * pi / 3
            x, y = 625 + radius * cos(a), 286 + radius * .9 * sin(a)
            line((x - 4, y, x + 4, y), "#e0f5ff", 2, "fx-ward")

    if source == "enemy" and reaction == "incoming" and .42 < p < .82:
        # Small edge marks convey impact without a full-screen flash.
        for x in (85, 915):
            line((x, 223, x + (20 if x < 500 else -20), 243, x, 263), "#b5645d", 4)
    elif reaction == "fumble" and .35 < p < .8:
        line((765, 301, 777, 289, 786, 307, 799, 298), "#d5bb89", 2, "fx-fumble")

    if source == "player" and reaction not in ("fumble", "buff") and impact > .15:
        landed = frame.get("hit", False)
        if landed or reaction == "block":
            hit_color = "#ffe09a" if frame.get("critical") else color if kind in _SPELLS else "#e5ccb0"
            radius = (11 if landed else 7) + impact * (15 if frame.get("critical") else 9)
            for i in range(6 if landed else 4):
                a = i * pi / (3 if landed else 2) + .2
                x1, y1 = 500 + 5 * cos(a), 195 + 5 * sin(a)
                line((x1, y1, 500 + radius * cos(a), 195 + radius * sin(a)), hit_color, 2)
            if frame.get("critical"):
                oval(500, 195, radius * 1.3, radius, "", "#f9d57b", 2, "fx-critical")
        if landed and frame.get("damage", 0) > 0 and .46 < p < .94:
            canvas.create_text(500 * sx, (112 - 30 * (p - .46)) * sy,
                               text=str(frame["damage"]), fill="#ffe19b" if frame.get("critical") else "#f1ddd1",
                               font=("Segoe UI", max(9, round(16 * min(sx, sy))), "bold"),
                               tags=(FX_TAG, "fx-damage"))
