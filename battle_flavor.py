"""Combat narration without random draws or mutations to combat state."""
from combat import AttackResult
from monster_catalog import FLOOR_MONSTERS, MONSTERS_BY_NAME


_ORIGINAL_MONSTERS = frozenset(spec.name for spec in FLOOR_MONSTERS[1])


def _enemy_traits(name: str) -> tuple[str, str]:
    """Return authored traits, with familiar fallbacks for guardians and fixtures."""
    spec = MONSTERS_BY_NAME.get(name)
    if spec is not None:
        return spec.strike, spec.surface
    lowered = name.lower()
    if "rat" in lowered or "stalker" in lowered:
        return "claw swipe", "tough hide"
    if "sentinel" in lowered:
        return "thorny root lash", "tangled bark and roots"
    if "colossus" in lowered:
        return "heated iron fist strike", "iron plating"
    if "hollow king" in lowered:
        return "surge of cold darkness", "shadow-wrapped form"
    if "warden" in lowered or "knight" in lowered:
        return "blade strike", "ancient armor"
    if "bone sentry" in lowered:
        return "rusted weapon strike", "bony frame"
    return "strike", "defenses"


def hit_description(attacker: str, defender: str, result: AttackResult) -> str:
    """Narrate a hit's rolled damage without changing rules or spending RNG.

    Damage bands stay the same as equipment and enemies improve: 1-5 is
    glancing, 6-10 solid, 11-15 heavy, and 16+ devastating. A high attack
    roll or a nearly defeated target does not make a low-damage hit heavy.
    Critical hits have extra precision narration within their damage band.
    """
    if not result.hit:
        return ""
    if result.damage == 0:
        if attacker == "You":
            story = f"Your sword connects with {defender}, but cannot bite through its defenses."
        else:
            story = f"{attacker}'s blow connects, but your armor absorbs the impact."
        if result.critical:
            story += " Even this perfectly placed strike causes no injury."
        return f"{story} No damage is dealt."

    if result.damage <= 5:
        band, label = 0, "Glancing blow!"
    elif result.damage <= 10:
        band, label = 1, "Solid blow!"
    elif result.damage <= 15:
        band, label = 2, "Heavy blow!"
    else:
        band, label = 3, "Devastating blow!"

    # Existing roll data chooses the prose; adding narration never changes
    # subsequent initiative, attack, damage, loot, or dungeon rolls.
    variant = (result.total + result.damage) % 2
    if attacker == "You":
        _, surface = _enemy_traits(defender)
        stories = (
            (
                f"Your sword just grazes {defender}'s {surface}, leaving a shallow mark.",
                f"Only the tip of your longsword catches {defender}'s {surface}; the cut is slight.",
            ),
            (
                f"Your longsword bites firmly into {defender}'s {surface} with a sharp crack.",
                f"You drive a clean sword stroke through {defender}'s guard, landing a telling cut.",
            ),
            (
                f"Your blade tears deep into {defender}'s {surface}; the impact rings through the chamber.",
                f"You put your weight behind the longsword, carving a deep gash through {defender}'s {surface}.",
            ),
            (
                f"Your longsword crashes through {defender}'s {surface} in a tremendous cleaving blow.",
                f"Your blade lands with crushing force against {defender}; the sound booms beneath the vaulted ceiling.",
            ),
        )
        critical_story = " Your blade finds a weak point with perfect timing."
    else:
        strike, _ = _enemy_traits(attacker)
        stories = (
            (
                f"{attacker}'s {strike} grazes you, sending a brief sting through your armor.",
                f"Only the edge of {attacker}'s {strike} connects, leaving a small but painful wound.",
            ),
            (
                f"A well-placed {strike} from {attacker} lands squarely, driving a sharp jolt through you.",
                f"{attacker} slips a {strike} past your defenses, landing a telling blow.",
            ),
            (
                f"{attacker} delivers a punishing {strike}; its force carries deep through your defenses.",
                f"A brutal {strike} from {attacker} slams into you with a sickening impact.",
            ),
            (
                f"{attacker} unleashes a thunderous {strike}; the impact echoes through the chamber.",
                f"{attacker}'s {strike} lands with overwhelming force, driving pain through your entire body.",
            ),
        )
        critical_story = " The strike catches you at an exposed angle."
    return f"{label} {stories[band][variant]}" + (critical_story if result.critical else "")


def miss_description(attacker: str, defender: str, result: AttackResult) -> str:
    attacker_spec = MONSTERS_BY_NAME.get(attacker)
    defender_spec = MONSTERS_BY_NAME.get(defender)
    if result.critical_fail:
        if attacker == "You":
            mishaps = (
                "You launch a heroic swing, trip over your own boot, and introduce your knee to the floor.",
                "Your sword whistles past its target; your shield rebounds into your nose. Very dignified.",
                "You attempt a magnificent lunge, skid on loose gravel, and land on your backside.",
            )
            # Attack bonuses change as equipment improves; prose never spends RNG.
            story = mishaps[result.total % len(mishaps)]
        elif attacker_spec is not None and attacker_spec.fumble:
            story = attacker_spec.fumble.format(attacker=attacker)
        elif "Rat" in attacker or "Stalker" in attacker:
            story = f"{attacker} lunges, tangles its feet, and lands nose-first on the stone. A fearsome entrance!"
        elif "Colossus" in attacker:
            story = f"{attacker} winds up a mighty blow, steps on a loose chain, and clangs into the wall like a dropped kettle."
        elif "Sentinel" in attacker:
            story = f"{attacker} lashes out, knots its own roots together, and topples with all the grace of a falling wardrobe."
        elif "King" in attacker or "Warden" in attacker or "Knight" in attacker:
            story = f"{attacker} attempts a regal swing, catches a foot on the flagstones, and takes an entirely unplanned bow."
        else:
            story = f"{attacker} makes a dramatic lunge, slips on rubble, and bumps into the wall. The wall wins this round."
        return f"Critical fail! {story} The attacker takes {result.fumble_damage} HP of self-damage."
    if result.near_miss:
        if attacker == "You":
            if defender_spec is not None and defender not in _ORIGINAL_MONSTERS:
                story = (f"Your blade brushes {defender}'s {defender_spec.surface}, "
                         "just short of a telling blow.")
            elif "Rat" in defender or "Stalker" in defender:
                story = f"Your sword scrapes along {defender}'s tough hide, failing to bite."
            elif "Sentinel" in defender:
                story = f"Your sword sparks against {defender}'s bark, barely missing a gap in the roots."
            elif "Colossus" in defender:
                story = f"Your blade skids across {defender}'s iron plating in a shower of sparks."
            else:
                story = f"Your sword sparks off {defender}'s defenses, just short of a telling blow."
        elif attacker_spec is not None and attacker not in _ORIGINAL_MONSTERS:
            story = (f"{attacker}'s {attacker_spec.strike} passes a hair's breadth "
                     "from you; a fraction closer would have hurt.")
        elif "Rat" in attacker or "Stalker" in attacker:
            story = f"{attacker}'s claws glance off your armor, inches from finding a gap."
        elif "Sentinel" in attacker:
            story = f"{attacker}'s thorny roots scrape your shield, just short of slipping past it."
        else:
            story = f"{attacker}'s strike glances off your armor; a fraction closer would have hurt."
        return f"Near miss! {story} No damage is dealt."
    return ""
