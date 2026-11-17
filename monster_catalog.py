"""Floor-specific ordinary foes and their authored, rules-neutral narration.

Statistics are unscaled templates. Dungeon generation adds the existing
depth bonuses when it creates a fresh enemy; this module draws no randomness.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MonsterSpec:
    """An immutable ordinary-foe template, separate from mutable combat state."""

    name: str
    hp: int
    armor_class: int
    attack_bonus: int
    damage_dice: tuple[int, int]
    damage_bonus: int
    xp_reward: int
    gold_reward: int
    initiative_bonus: int = 0
    description: str = ""
    tactics: str = ""
    strike: str = ""
    surface: str = ""
    fumble: str = ""


FLOOR_MONSTERS: dict[int, tuple[MonsterSpec, ...]] = {
    1: (
        MonsterSpec(
            "Crypt Rat", 5, 11, 2, (1, 4), 1, 50, 4,
            description=(
                "A swollen crypt rat crouches close to the stones, its scarred hide "
                "stretched over twitching shoulders. Sharp claws scrape as it lunges."
            ),
            tactics=(
                "A landed longsword hit applies Sap, giving its next attack "
                "Disadvantage before your next turn."
            ),
            strike="claw swipe", surface="tough hide",
        ),
        MonsterSpec(
            "Bone Sentry", 8, 13, 3, (1, 6), 1, 50, 6,
            description=(
                "A frame of yellowed bones stands between you and the passage. "
                "Its rusted weapon jerks upward with the scrape of old joints."
            ),
            tactics=(
                "Dodge spends your action to give its visible attacks Disadvantage "
                "until your next turn; a longsword hit can instead apply Sap."
            ),
            strike="rusted weapon strike", surface="bony frame",
        ),
        MonsterSpec(
            "Grave Marauder", 9, 12, 3, (1, 6), 1, 50, 7,
            description=(
                "A ragged marauder hunches over the disturbed tombs. Dust falls "
                "from its wrappings as it squares its shoulders for a close strike."
            ),
            tactics=(
                "Compare its attack bonus with your Armor Class before choosing "
                "an attack or Dodge. A longsword hit applies Sap to its next attack."
            ),
            strike="strike", surface="defenses",
        ),
        MonsterSpec(
            "Hollow Acolyte", 7, 11, 2, (1, 4), 1, 50, 8,
            description=(
                "A hollow-eyed acolyte shuffles forward in a frayed burial robe. "
                "Its hands rise from empty sleeves to strike at close quarters."
            ),
            tactics=(
                "It makes a close-range attack, not a spell attack. Landing a "
                "longsword hit applies Sap; Dodge also helps against its visible attack."
            ),
            strike="strike", surface="defenses",
        ),
        MonsterSpec(
            "Restless Knight", 10, 13, 3, (1, 6), 1, 100, 9,
            description=(
                "A restless knight advances behind dented ancient armor. "
                "Its blade keeps a practiced guard despite its uneven, dragging steps."
            ),
            tactics=(
                "Its Armor Class determines how hard it is to hit. An Ember stone "
                "deals 3d6 damage without an attack roll, consuming a stone and an action."
            ),
            strike="blade strike", surface="ancient armor",
        ),
        MonsterSpec(
            "Catacomb Stalker", 11, 12, 3, (1, 6), 1, 100, 10,
            description=(
                "A lean stalker unfolds from the shadows, long claws brushing "
                "the floor. Its tough hide shifts as it gathers itself for a swipe."
            ),
            tactics=(
                "A longsword hit applies Sap to its next attack. Dodge spends "
                "your action if you need to protect yourself until your next turn."
            ),
            strike="claw swipe", surface="tough hide",
        ),
    ),
    2: (
        MonsterSpec(
            "Sapglass Beetle", 6, 12, 2, (1, 4), 1, 50, 5,
            description=(
                "An oversized beetle squeezes between the binding roots. Amber sap "
                "coats its translucent shell, and its jagged mandibles click beneath the grove's warm glow."
            ),
            tactics=(
                "Its shell gives it a modest guard, but it has fewer hit points "
                "than the grove's larger inhabitants. Its mandibles make one close-range attack."
            ),
            strike="mandible snap", surface="glass-bright shell",
            fumble=(
                "{attacker} catches its mandibles on a root and rolls onto its back "
                "like a dropped helmet."
            ),
        ),
        MonsterSpec(
            "Thorn Creeper", 8, 12, 3, (1, 6), 1, 50, 6,
            description=(
                "A tangle of pruning scars and thorny vines pulls itself across "
                "the floor. Broken silver binding wire trails from its wooden core like forgotten reins."
            ),
            tactics=(
                "Its barbed lash makes one close-range attack each turn. Its "
                "guard is lighter than the Keeper's bark, leaving a more accessible target."
            ),
            strike="barbed vine lash", surface="knotted vines",
            fumble=(
                "{attacker} throws out a vine, tangles it around its own core, "
                "and lands in an undignified leafy heap."
            ),
        ),
        MonsterSpec(
            "Spore Husk", 7, 11, 2, (1, 4), 1, 50, 7,
            description=(
                "Pale mushrooms lift a hollow gardener's robe into a shambling shape. "
                "The ruined chapel's spores cling to its swollen fists, drifting loose with every step."
            ),
            tactics=(
                "Soft fungal growth gives it one of the grove's weakest guards. "
                "Its lower hit points and light fist strike make it less durable than the rooted defenders."
            ),
            strike="fungal fist strike", surface="pale fungal growth",
            fumble=(
                "{attacker} swings so enthusiastically that a mushroom cap flops "
                "over its face, sending it headfirst into a root."
            ),
        ),
        MonsterSpec(
            "Amber Mantis", 8, 13, 3, (1, 6), 1, 50, 8,
            initiative_bonus=2,
            description=(
                "A mantis taller than a child unfolds from an amber-lit branch. "
                "Its hooked forelegs bear pruning marks from keepers who once tended the binding grove."
            ),
            tactics=(
                "Its quick movements improve its initiative, and its chitin guards "
                "it better than softer grove creatures. Each enemy turn still contains only one attack."
            ),
            strike="hooked foreleg slash", surface="amber chitin",
            fumble=(
                "{attacker} snaps both forelegs into a branch and topples off it "
                "while looking deeply offended by gardening."
            ),
        ),
        MonsterSpec(
            "Rootcoil Viper", 10, 12, 3, (1, 6), 1, 100, 9,
            initiative_bonus=1,
            description=(
                "A long root peels away from the nursery wall, revealing a wooden "
                "serpent. Warm sap gathers beneath its carved fangs as its coils tighten around broken seed jars."
            ),
            tactics=(
                "Its small initiative bonus makes it quicker than the grove's "
                "shambling foes. The long wooden body has more hit points than the smaller insects and fungi."
            ),
            strike="woody fang strike", surface="flexible root scales",
            fumble=(
                "{attacker} lunges through its own coil and bites its tail, "
                "briefly becoming a very cross wreath."
            ),
        ),
        MonsterSpec(
            "Moldbound Keeper", 12, 14, 3, (1, 6), 2, 100, 11,
            description=(
                "The grove's dead keeper rises beneath layers of hardened moss. "
                "A pruning hook remains clenched in roots grown through its hands, still defending a long-forgotten duty."
            ),
            tactics=(
                "Its hardened covering and higher hit points make it a durable "
                "foe. Compare its current damage bonus before trading blows with the pruning hook."
            ),
            strike="pruning-hook swing", surface="moss-covered bark armor",
            fumble=(
                "{attacker} hooks its own mossy sleeve and spins into a watering "
                "bowl with the dignity of a startled scarecrow."
            ),
        ),
    ),
    3: (
        MonsterSpec(
            "Bellows Automaton", 8, 13, 3, (1, 6), 1, 50, 6,
            description=(
                "An iron workshop servant marches on piston legs, a torn bellows "
                "wheezing inside its chest. Its hammer arm rises to continue an order centuries old."
            ),
            tactics=(
                "Iron casing gives this servant a steady guard. Its hammer makes "
                "one close-range attack each turn, with less force than the smith's casting hammer."
            ),
            strike="piston-hammer blow", surface="riveted iron casing",
            fumble=(
                "{attacker} pumps its bellows too hard, rocks backward, and bonks "
                "its own head with the hammer arm."
            ),
        ),
        MonsterSpec(
            "Slag Crawler", 9, 12, 3, (1, 6), 1, 50, 7,
            description=(
                "Cooling waste metal gathers into a squat creature beside the "
                "slag canal. It drags mismatched limbs over the iron floor, leaving flakes of brittle casting behind."
            ),
            tactics=(
                "Its crusted shell offers a less secure guard than the plated "
                "constructs. Its jagged limb strikes once per turn, backed by a steady attack bonus."
            ),
            strike="jagged slag-limb swing", surface="crusted slag shell",
            fumble=(
                "{attacker} plants a lumpy foot on a loose casting and skids "
                "into the wall like a badly parked wheelbarrow."
            ),
        ),
        MonsterSpec(
            "Cinder Imp", 6, 11, 2, (1, 4), 1, 50, 5,
            initiative_bonus=1,
            description=(
                "A small shape of soot and live embers scrambles from a furnace "
                "vent. It clutches a discarded poker, grinning through the ash of the forge's endless fire."
            ),
            tactics=(
                "This small foe has fewer hit points and a small initiative "
                "bonus. Its light poker is weaker than the forge's heavy hammers, and its guard is poor."
            ),
            strike="sooty poker jab", surface="ember-speckled body",
            fumble=(
                "{attacker} flourishes its poker, catches the handle under its "
                "own foot, and smacks itself in the forehead."
            ),
        ),
        MonsterSpec(
            "Hollow Smith", 11, 13, 3, (1, 8), 1, 100, 10,
            description=(
                "A dead smith in a scorched apron hauls a casting hammer from "
                "the anvil. Royal restraint markings cover the metal, but its maker no longer remembers the prisoner."
            ),
            tactics=(
                "Its heavy hammer uses a larger damage die than most forge "
                "foes. Review its current damage before trading blows; it still makes one attack per turn."
            ),
            strike="casting-hammer swing", surface="scorched work armor",
            fumble=(
                "{attacker} misses the rhythm of its swing and drops the hammer "
                "on its own foot, producing a very unprofessional clang."
            ),
        ),
        MonsterSpec(
            "Chainwork Harrier", 8, 14, 3, (1, 6), 1, 50, 8,
            initiative_bonus=2,
            description=(
                "A jointed machine scuttles between hanging chain molds. Silver "
                "links form its narrow body, and a hooked fastening arm reaches to seize another unfinished task."
            ),
            tactics=(
                "Its quick joints improve initiative, while linked plating gives "
                "it a stronger guard. It has less staying power than the forge's larger constructs."
            ),
            strike="fastening-hook slash", surface="interlocking chain plates",
            fumble=(
                "{attacker} hooks a hanging chain instead of you and swings "
                "straight into an anvil with a surprised metallic rattle."
            ),
        ),
        MonsterSpec(
            "Crucible Scuttler", 12, 13, 3, (1, 6), 2, 100, 12,
            description=(
                "A walking crucible hauls itself over the forge bridge on iron "
                "legs. Its cooled rim snaps like a jaw beneath the makers' faded royal chain insignia."
            ),
            tactics=(
                "Its thick vessel holds more hit points than smaller machines, "
                "and its rim strike has a higher damage bonus. It makes one close-range attack."
            ),
            strike="iron rim snap", surface="blackened crucible walls",
            fumble=(
                "{attacker} overbalances during a snap and rocks onto its rim, "
                "clanging back and forth like an enormous dropped saucepan."
            ),
        ),
    ),
    4: (
        MonsterSpec(
            "Oathbound Echo", 7, 12, 2, (1, 6), 1, 50, 6,
            description=(
                "A pale outline repeats the vault guards' last sworn words. "
                "An unfinished face forms above its raised blade, held together by an oath whose speaker is forgotten."
            ),
            tactics=(
                "Its wavering outline has fewer hit points than the vault's "
                "heavily bound guardians. Its blade strikes once per turn with a lower attack bonus than the jailer's."
            ),
            strike="echoing blade sweep", surface="pale oathwoven outline",
            fumble=(
                "{attacker} begins a solemn swing, repeats its own last step, "
                "and walks face-first into a pillar."
            ),
        ),
        MonsterSpec(
            "Silverchain Watcher", 12, 14, 3, (1, 6), 2, 100, 11,
            description=(
                "Silver restraints coil around an empty guard's helm and rise "
                "into a watchful figure. Broken oath seals hang from the heavy link gathered in its fist."
            ),
            tactics=(
                "Layers of silver chain give it a stronger guard and more hit "
                "points. Its heavy link strikes once per turn with a higher damage bonus."
            ),
            strike="heavy chain-link blow", surface="layered silver restraints",
            fumble=(
                "{attacker} winds up a chain, wraps it around its own helm, "
                "and gives itself an extremely thorough ringing."
            ),
        ),
        MonsterSpec(
            "Shadow Jailer", 9, 13, 3, (1, 6), 1, 50, 8,
            description=(
                "A dark stain steps away from a vacant sentry wall. Keys "
                "rattle inside its featureless shape, and a black baton rises beneath the scraped names of prisoners."
            ),
            tactics=(
                "Its dense mantle guards it better than the vault's lighter "
                "echoes. The baton makes one close-range attack with a stronger attack bonus than the Witness's."
            ),
            strike="black baton strike", surface="dense shadow mantle",
            fumble=(
                "{attacker} tries to twirl its baton, drops it through a "
                "loop of keys, and trips over the entire arrangement."
            ),
        ),
        MonsterSpec(
            "Mirror Shardling", 6, 11, 3, (1, 4), 1, 50, 5,
            initiative_bonus=2,
            description=(
                "Splinters of a prison mirror skitter into a narrow figure. "
                "Each fragment reflects a different crowned face while its sharp glass arm hunts for your lantern light."
            ),
            tactics=(
                "Its shifting fragments give it a higher initiative bonus but "
                "little protection. Its glass arm strikes accurately for lighter damage, and its frame has few hit points."
            ),
            strike="glass-edged slash", surface="fractured mirror frame",
            fumble=(
                "{attacker} mistakes its reflection for you and headbutts a "
                "covered mirror with a thoroughly embarrassing tinkle."
            ),
        ),
        MonsterSpec(
            "Nameless Witness", 8, 12, 2, (1, 6), 1, 50, 7,
            description=(
                "A veiled shape rises from the royal deposition, clutching a "
                "broken marble tablet. Its erased name follows it as dust across the vault's silent floor."
            ),
            tactics=(
                "It attacks once with the broken tablet at close range. Its "
                "attack bonus and dusty guard are weaker than those of the jailer and silver-bound Watcher."
            ),
            strike="broken tablet swing", surface="dust-laden funeral veil",
            fumble=(
                "{attacker} raises its tablet for a grand accusation, loses "
                "its grip, and stamps its own toes with the evidence."
            ),
        ),
        MonsterSpec(
            "Starless Leech", 10, 12, 3, (1, 8), 1, 100, 10,
            initiative_bonus=1,
            description=(
                "A long black creature uncoils from the orrery's missing star. "
                "Silver studs glitter along its skin, swallowed remnants of the vault's failing royal constellation."
            ),
            tactics=(
                "Its jaws use a larger damage die, and a small initiative "
                "bonus makes it quicker than the Watcher. Its slick body offers a less secure guard."
            ),
            strike="star-studded jaw snap", surface="slick constellation-marked skin",
            fumble=(
                "{attacker} coils for a bite, tangles itself in an orrery "
                "ring, and swings around like a very unhappy pendulum."
            ),
        ),
    ),
    5: (
        MonsterSpec(
            "Blackwater Courtier", 8, 12, 3, (1, 6), 1, 50, 8,
            description=(
                "Dark court water rises into a robed attendant, its face a "
                "rippling hollow. A ceremonial staff forms between its hands as it bows toward the empty royal dais."
            ),
            tactics=(
                "Its ceremonial staff makes one close-range attack each turn. "
                "Its watery robes provide a lighter guard and fewer hit points than the armored Usher."
            ),
            strike="ceremonial staff sweep", surface="blackwater robes",
            fumble=(
                "{attacker} begins an elaborate bow, catches its staff across "
                "its knees, and collapses into a distinctly unroyal splash."
            ),
        ),
        MonsterSpec(
            "Crown Wisp", 6, 11, 2, (1, 4), 1, 50, 6,
            initiative_bonus=2,
            description=(
                "A tiny imitation crown bobs above a knot of darkness. "
                "It darts along the royal mosaic, trailing the shadow of a king who no longer has a heart."
            ),
            tactics=(
                "This slight manifestation acts quickly but has fewer hit points "
                "and a weak guard. Its light shadow lash deals less damage than the court's staff strikes."
            ),
            strike="thin shadow lash", surface="crown-shaped shadow",
            fumble=(
                "{attacker} darts forward, snags its crown on a stone "
                "decoration, and bumps into the wall beneath its own royal hat."
            ),
        ),
        MonsterSpec(
            "Heartless Usher", 11, 14, 3, (1, 6), 1, 50, 10,
            description=(
                "An empty ceremonial breastplate blocks the throneward passage. "
                "A dark cavity opens beneath its royal crest, and white gloves tighten around an audience hall's iron staff."
            ),
            tactics=(
                "Its ceremonial armor makes it harder to hit than the court's "
                "lighter manifestations. Its higher hit points sustain a single staff attack each turn."
            ),
            strike="iron staff thrust", surface="empty ceremonial armor",
            fumble=(
                "{attacker} flourishes its staff at the wrong angle and "
                "knocks its own breastplate against the doorway with a hollow bong."
            ),
        ),
        MonsterSpec(
            "Choir Fragment", 7, 12, 2, (1, 4), 1, 50, 7,
            initiative_bonus=1,
            description=(
                "One voice peels free of the nameless choir and gathers a "
                "body from pale dust. Its reaching hands shake beneath an unfinished plea for the lost city's dawn."
            ),
            tactics=(
                "It has a small initiative bonus but fewer hit points than "
                "the throne's heavy defenders. Its grasp has a lower attack bonus and lighter damage than their blows."
            ),
            strike="dust-woven hand strike", surface="pale dust-woven body",
            fumble=(
                "{attacker} reaches for you, catches its own trailing dust, "
                "and tumbles into a heap with a painfully off-key squeak."
            ),
        ),
        MonsterSpec(
            "Sacrifice Revenant", 12, 13, 3, (1, 8), 1, 100, 12,
            description=(
                "A figure marked by the offering altar's dried handprint rises "
                "from ancient stone. Its cracked blade carries the weight of the king's remembered sacrifice, twisted into service."
            ),
            tactics=(
                "Its larger damage die and higher hit points make a dangerous "
                "exchange of blows. Its blade strikes once per turn behind a firmer guard than the lighter court manifestations."
            ),
            strike="cracked offering-blade swing", surface="handprint-marked stone flesh",
            fumble=(
                "{attacker} lifts its blade in a dramatic salute and "
                "clips the ceiling, showering its own head with ancient plaster."
            ),
        ),
        MonsterSpec(
            "Throne Hunger", 10, 13, 4, (1, 6), 2, 100, 11,
            description=(
                "A mouthlike darkness unfolds from the foundation beside the "
                "last chain. Fragments of royal stone turn within it, moving to the false heartbeat beneath the hollow throne."
            ),
            tactics=(
                "Its higher attack bonus and damage bonus reward careful defense. "
                "Its stone-rimmed body is better guarded than the lighter manifestations, but its jaw strikes only once each turn."
            ),
            strike="royal-stone jaw crush", surface="stone-rimmed darkness",
            fumble=(
                "{attacker} snaps at you, bites a dangling chain instead, "
                "and cracks its own stone jaw with a deeply undignified clunk."
            ),
        ),
    ),
}


MONSTERS_BY_NAME: dict[str, MonsterSpec] = {
    spec.name: spec
    for roster in FLOOR_MONSTERS.values()
    for spec in roster
}


def floor_roster(floor: int) -> tuple[MonsterSpec, ...]:
    """Return one floor's six ordinary-foe templates without drawing RNG."""
    if isinstance(floor, bool) or not isinstance(floor, int) or floor not in FLOOR_MONSTERS:
        raise ValueError("Dungeon floor must be an integer from 1 to 5.")
    return FLOOR_MONSTERS[floor]
