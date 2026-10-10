"""Combat narration without random draws or mutations to combat state."""
from combat import AttackResult


def miss_description(attacker: str, defender: str, result: AttackResult) -> str:
    if result.critical_fail:
        if attacker == "You":
            mishaps = (
                "You launch a heroic swing, trip over your own boot, and introduce your knee to the floor.",
                "Your sword whistles past its target; your shield rebounds into your nose. Very dignified.",
                "You attempt a magnificent lunge, skid on loose gravel, and land on your backside.",
            )
            # Attack bonuses change as equipment improves; prose never spends RNG.
            story = mishaps[result.total % len(mishaps)]
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
            if "Rat" in defender or "Stalker" in defender:
                story = f"Your sword scrapes along {defender}'s tough hide, failing to bite."
            elif "Sentinel" in defender:
                story = f"Your sword sparks against {defender}'s bark, barely missing a gap in the roots."
            elif "Colossus" in defender:
                story = f"Your blade skids across {defender}'s iron plating in a shower of sparks."
            else:
                story = f"Your sword sparks off {defender}'s defenses, just short of a telling blow."
        elif "Rat" in attacker or "Stalker" in attacker:
            story = f"{attacker}'s claws glance off your armor, inches from finding a gap."
        elif "Sentinel" in attacker:
            story = f"{attacker}'s thorny roots scrape your shield, just short of slipping past it."
        else:
            story = f"{attacker}'s strike glances off your armor; a fraction closer would have hurt."
        return f"Near miss! {story} No damage is dealt."
    return ""
