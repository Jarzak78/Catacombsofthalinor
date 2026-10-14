"""The story of Thalinor's fall, revealed one dungeon floor at a time."""
from dataclasses import dataclass
from room_library import ENTRANCE, ROOM_FLAVORS

@dataclass(frozen=True)
class FloorLore:
    arrival: str
    revelation: str
    entrance: tuple[str, str]
    sanctum: tuple[str, str]
    rooms: tuple[tuple[str, str], ...]

LORE = (
    FloorLore(
        "The upper catacombs hold Thalinor's honored dead. The guild calls this a trial, but fresh cracks split seals that have held for centuries.",
        "Beneath the Warden's armor, you find a broken seal engraved with roots. The guardian was keeping something below from rising.",
        ENTRANCE,
        ("The Warden's Sanctum", "Blue fire surrounds the throne of the upper tombs. The Warden raises its blade before a sealed arch. Beyond it, roots strain against the stone; this guardian protects the first threshold, not the end of the catacombs."),
        ROOM_FLAVORS,
    ),
    FloorLore(
        "The portal leaves the moonlit tombs behind. You arrive beneath their foundations, where a buried grove has forced its roots through the dead city's walls.",
        "The Sentinel's roots release a stone tablet: the grove was planted to bind a fire beneath Thalinor. Its keepers fed the roots with power drawn from a deeper forge.",
        ("The Tangled Threshold", "Mira's portal closes behind you in a cavern of woven roots. No moonlight reaches this depth. Warm sap runs down a stair carved through the foundations of the upper tombs."),
        ("The Heartwood Cage", "An enormous root coils around a cracked furnace hatch. The Thornbound Sentinel pulls itself from the living wood, guarding the way to the heat that feeds this buried grove."),
        (
            ("The Saplit Walk", "Amber sap pools along a root-covered walkway. Within its glow, trapped insects cast shadows larger than your shield."),
            ("The Gardener's Crypt", "A skeleton kneels beside a dry watering bowl. Its stone nameplate calls it keeper of the binding grove; roots have grown through both hands."),
            ("The Drowned Nursery", "Black water laps against rows of broken seed jars. A mural shows saplings planted above a red wound in the earth."),
            ("The Thorn Gate", "Barbed vines lace a collapsed gate. Old pruning hooks hang beyond it, their handles polished by generations of forgotten wardens."),
            ("The Spore Chapel", "Pale mushrooms cover a shrine to the city's gardeners. Spores drift through your lantern beam, revealing a warning: do not let the roots wither."),
            ("The Root Archive", "Clay tablets are wedged between thick roots. One records shipments of furnace ash, delivered here long after the city above was abandoned."),
            ("The Hollow Oak", "A petrified trunk fills the chamber. Through a split in its bark you hear the steady clanging of machinery far below."),
            ("The Binding Circle", "Roots follow silver channels cut into the floor. Several channels have snapped, and hot air whistles through the fractures."),
            ("The Keeper's Refuge", "A moss-covered bench stands beside a wall of tally marks. The last entry reads: the forge burns, but the king no longer answers."),
            ("The Ember Well", "Red light flickers at the bottom of a shaft wrapped in roots. Drops of sap fall into the darkness and hiss against unseen metal."),
        ),
    ),
    FloorLore(
        "Below the grove lies the Ashen Forge. Its furnaces still burn without workers, feeding heat into the roots and power into machinery aimed farther down.",
        "In the Colossus's cooling chest, a maker's plate names the Starless Vault. The forge did not make weapons alone: it powered chains built to restrain Thalinor's king.",
        ("The Cinder Landing", "You step from the portal onto an iron platform beneath the grove. Charred roots hang through the ceiling, drinking warmth from pipes that shake with furnace pressure."),
        ("The Great Crucible", "Molten metal lights a vast casting pit. The Ember Colossus stands across its bridge, furnace doors glowing in its chest. Behind it, chains descend through a floor too hot to touch."),
        (
            ("The Bellows Hall", "Leather bellows rise and fall with no hands to work them. Each breath drives sparks across a row of empty smithing stations."),
            ("The Slag Canal", "A narrow bridge crosses a channel of cooling slag. Footprints end at its edge, burned permanently into the iron walkway."),
            ("The Chain Foundry", "Links taller than your torso lie in casting molds. Their runes match the broken seals in the tombs above."),
            ("The Master Smith's Office", "An open ledger rests beneath a layer of ash. Its final order demands chains for a royal prisoner, with no name entered beside the charge."),
            ("The Quenching Chamber", "Steam escapes from cracked stone tanks. A silver chain hangs in the largest bath, cold enough to frost the water around it."),
            ("The Coal Lift", "An abandoned lift drops into a soot-black shaft. A cargo label directs fuel upward to the grove and forged restraints downward to the vault."),
            ("The Broken Anvil", "A massive anvil has split down the middle. Something struck it from within, leaving a handprint in metal that should never have bent."),
            ("The Furnace Shrine", "Smiths' prayer tokens hang above a flame that refuses to die. An inscription promises the fire will endure until the royal seal is restored."),
            ("The Ash Barracks", "Empty armor sits on benches around a cold meal. A warning scratched into a helmet reads: listen for chains, never for the voice beneath them."),
            ("The Pressure Gallery", "Copper gauges tremble above pipes buried in the walls. The deepest pipe beats like a pulse, sending dark flecks through its glass inspection window."),
        ),
    ),
    FloorLore(
        "The forge's roar fades into an unnatural silence. Here, the Starless Vault holds the chains and oaths that once kept a royal darkness sealed below the city.",
        "The Void Knight's oath-stone breaks. Its inscription reveals the truth: Thalinor's king surrendered his living heart to save the city, and the hollow thing left behind learned to speak with his voice.",
        ("The Silent Causeway", "The portal opens on a bridge of black stone. Far above, forge chains vanish into the ceiling. Below, an empty shaft swallows your lantern light before it reaches the bottom."),
        ("The Oathbound Gate", "Silver chains converge on a gate bearing the royal crest. The Void Knight stands motionless before it, sword drawn across a vow to let no living soul reach the hollow throne."),
        (
            ("The Unlit Orrery", "Bronze rings turn around a missing star. Their movement follows no sky; each ring is tethered to a chain running toward the sealed royal gate."),
            ("The Hall of Unspoken Names", "Guardians' names have been scraped from black marble tablets. You can read only their shared oath: the king must remain below."),
            ("The Silver Anchorage", "Enormous chains are bolted into the bedrock. One has snapped, leaving its broken end hovering over the floor as though gravity has forgotten it."),
            ("The Empty Watch", "Stone sentry posts face a blank wall. A dark stain travels across it against the direction of your lantern's shadow."),
            ("The Royal Deposition", "A sealed testimony lies beneath cracked glass. It describes a willing sacrifice, followed by a voice pleading for the chains to be removed."),
            ("The Mirror Prison", "Covered mirrors line narrow cells. One cloth has slipped; its glass reflects a crowned figure where you should be standing."),
            ("The Severed Conduit", "A pipe from the forge ends in a broken rune circle. Sparks drift into darkness and disappear without touching the floor."),
            ("The Last Vigil", "A knight's bedroll lies beside a stone cup. Dust covers everything except the words cut into the wall: remember who he was, resist what he became."),
            ("The Chamber of Echoes", "A voice welcomes you by name from behind the stone. It sounds weary and kind, but its words arrive before your footsteps make an echo."),
            ("The Fallen Constellation", "Silver studs form a royal crown across the ceiling. Their light dims one by one as something far below draws a slow breath."),
        ),
    ),
    FloorLore(
        "You descend below tomb, root, forge, and prison. At Thalinor's foundation, the lost king's sacrifice has become a hunger, and every broken seal points toward its throne.",
        "The Hollow King's crown falls empty. The false heartbeat stops, the chains above settle, and the city is released from the darkness beneath its dead.",
        ("The Foundation Rift", "Mira's portal opens inside the oldest stones of Thalinor. The royal crest has been worn smooth by centuries of dark water. A heartbeat shakes the floor, although nothing living waits here."),
        ("The Hollow Throne", "The city's foundations curve around a throne carved from its own bedrock. The Hollow King rises beneath a fractured crown, an open darkness where his heart should be. All the catacombs' chains lead here."),
        (
            ("The First Foundation", "The earliest builders' tools lie sealed within transparent stone. Their unfinished inscription asks the city's heart to protect all who will live above."),
            ("The Coronation Grave", "A royal procession is carved around an empty sarcophagus. The king's likeness has no face, and every carved witness turns away from him."),
            ("The Chamber of the Offering", "A stone bowl rests on an altar beneath the royal seal. A single dried handprint marks where the king offered his heart to halt the disaster."),
            ("The Blackwater Court", "Dark water covers the floor of an abandoned audience hall. Ripples gather toward an empty dais, as if unseen courtiers still kneel there."),
            ("The Crown's Shadow", "A broken crown is painted above a doorway. Its shadow falls across your path even when your lantern points in the opposite direction."),
            ("The City's Memory", "Small belongings fill shelves cut into the rock: a child's cup, a mason's cord, a gardener's knife. These are the lives the king meant to save."),
            ("The Last Chain", "The final intact restraint crosses the chamber at chest height. Its links strain with each heartbeat from the throne, shedding silver dust."),
            ("The Nameless Choir", "Cracks in the walls carry hundreds of thin voices. For a moment they speak together: he gave his heart, but it was never enough."),
            ("The Sealed Dawn", "A golden mosaic shows sunlight falling over Thalinor before its ruin. Beneath it, a narrow passage exhales cold air from the royal chamber."),
            ("The Heartless Antechamber", "The heartbeat grows loud enough to drown your breathing. An inscription beside the throne door names the man the king once was, before the stone beneath it turns black."),
        ),
    ),
)
