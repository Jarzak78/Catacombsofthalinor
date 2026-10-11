"""Foe descriptions and detached combat details, independent of presentation."""

from room import Enemy


# These descriptions add atmosphere to the existing single melee attack.
# Advice refers only to actions already supported by the combat engine.
_PROFILES = {
    "Crypt Rat": (
        "A swollen crypt rat crouches close to the stones, its scarred hide "
        "stretched over twitching shoulders. Sharp claws scrape as it lunges.",
        "A landed longsword hit applies Sap, giving its next attack "
        "Disadvantage before your next turn.",
    ),
    "Bone Sentry": (
        "A frame of yellowed bones stands between you and the passage. "
        "Its rusted weapon jerks upward with the scrape of old joints.",
        "Dodge spends your action to give its visible attacks Disadvantage "
        "until your next turn; a longsword hit can instead apply Sap.",
    ),
    "Grave Marauder": (
        "A ragged marauder hunches over the disturbed tombs. Dust falls "
        "from its wrappings as it squares its shoulders for a close strike.",
        "Compare its attack bonus with your Armor Class before choosing "
        "an attack or Dodge. A longsword hit applies Sap to its next attack.",
    ),
    "Hollow Acolyte": (
        "A hollow-eyed acolyte shuffles forward in a frayed burial robe. "
        "Its hands rise from empty sleeves to strike at close quarters.",
        "It makes a close-range attack, not a spell attack. Landing a "
        "longsword hit applies Sap; Dodge also helps against its visible attack.",
    ),
    "Restless Knight": (
        "A restless knight advances behind dented ancient armor. "
        "Its blade keeps a practiced guard despite its uneven, dragging steps.",
        "Its Armor Class determines how hard it is to hit. An Ember stone "
        "deals 3d6 damage without an attack roll, consuming a stone and an action.",
    ),
    "Catacomb Stalker": (
        "A lean stalker unfolds from the shadows, long claws brushing "
        "the floor. Its tough hide shifts as it gathers itself for a swipe.",
        "A longsword hit applies Sap to its next attack. Dodge spends "
        "your action if you need to protect yourself until your next turn.",
    ),
    "Warden of Thalinor": (
        "The towering Warden blocks the sealed arch in ancient armor. "
        "Blue fire catches along its raised blade as it settles into its guard.",
        "This guardian has more staying power than the upper tomb's ordinary "
        "foes. Longsword hits apply Sap; an Ember stone bypasses the attack roll.",
    ),
    "Thornbound Sentinel": (
        "The Sentinel pulls itself from a cage of living wood. Tangled "
        "bark shields its body while thorny roots coil into striking lashes.",
        "Its root lash is a melee attack: Sap and Dodge can hinder it. "
        "An Ember stone deals its normal 3d6 damage without an attack roll.",
    ),
    "Ember Colossus": (
        "Furnace light glows through the Colossus's chest. Iron plates grind "
        "as it draws back a massive heated fist above the forge bridge.",
        "Check its damage dice and bonus before trading blows. Dodge can "
        "hinder its visible fist strike, and longsword hits apply Sap.",
    ),
    "Void Knight": (
        "The Void Knight stands before the oathbound gate in ancient armor. "
        "Its drawn sword tracks you beneath the silver chains of the vault.",
        "Its armored guard can make sword hits harder to land. An Ember "
        "stone needs no attack roll; a successful longsword hit applies Sap.",
    ),
    "The Hollow King": (
        "A fractured crown hangs above the Hollow King's shadow-wrapped "
        "form. Darkness gathers where his heart should be, then surges toward you.",
        "Its surge resolves as a close-range attack. Sap and Dodge can "
        "hinder it; an Ember stone consumes an action for automatic 3d6 damage.",
    ),
}

_UNKNOWN_PROFILE = (
    "This foe watches your approach and braces for a close-range strike. "
    "Its stance offers no further clues about its nature.",
    "Review its Armor Class, attack bonus, and damage before committing. "
    "A longsword hit applies Sap; Dodge spends an action to hinder visible attacks.",
)


_CLASS_TACTICS = {
    "rogue": (
        "A successful Hide check gives your next rapier attack Advantage. "
        "A rapier hit applies Vex to your next attack against this foe. "
        "Advantage allows Sneak Attack once per turn; a critical hit "
        "doubles its extra damage dice."
    ),
    "wizard": (
        "Prepare Mage Armor in a safe room. Shield costs a level-1 slot "
        "and a bonus action for +5 AC against the next enemy strike. "
        "When available, a Frost Lance hit gives its next attack "
        "Disadvantage; Magic Missile spends a level-1 slot to bypass "
        "the attack roll."
    ),
}


def foe_details(enemy: Enemy, class_id: str = "fighter") -> dict:
    """Return authored flavor and the foe's current, possibly scaled stats.

    Every call creates a new JSON-compatible view. Reading these details
    neither changes the enemy nor consumes random numbers. The descriptions
    do not grant resistances, vulnerabilities, conditions, or extra attacks.
    Tactical advice uses the adventurer's supported abilities; the default
    preserves the original warrior advice for existing callers.
    """
    if class_id not in ("fighter", "rogue", "wizard"):
        raise ValueError("Choose fighter, rogue, or wizard for foe advice.")
    description, tactics = _PROFILES.get(enemy.name, _UNKNOWN_PROFILE)
    if class_id in _CLASS_TACTICS:
        tactics = _CLASS_TACTICS[class_id]
    return {
        "name": enemy.name,
        "description": description,
        "tactics": tactics,
        "hp": enemy.hp,
        "max_hp": enemy.max_hp,
        "armor_class": enemy.armor_class,
        "attack_bonus": enemy.attack_bonus,
        "damage_dice": list(enemy.damage_dice),
        "damage_bonus": enemy.damage_bonus,
        "boss": enemy.boss,
    }
