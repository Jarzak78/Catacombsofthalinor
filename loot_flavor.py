"""Authored search descriptions, independent of rewards and game state."""

from room import Room


_FALLBACK = (
    "Beneath the settled dust, you find a small cache tucked into a cracked "
    "stone recess and carefully uncover its contents."
)

_DISCOVERIES = {
    1: {
        "The Broken Stair": (
            "You search beneath the broken steps and uncover a weathered leather "
            "satchel, its strap trapped under a fallen piece of masonry."
        ),
        "Hall of Whispering Kings": (
            "Behind a fallen king's statue, you find an old cedar chest; its "
            "tarnished clasp gives way with a tired metallic click."
        ),
        "The Rootbound Vault": (
            "You follow the pale roots to a burial box wedged between empty "
            "coffins, brushing tangled fibers from its warped wooden lid."
        ),
        "Chapel of the Last Light": (
            "A shallow offering drawer sits beneath the silver altar; you pull "
            "it open, disturbing a blanket of ancient candle wax."
        ),
        "The Sunken Gallery": (
            "Beneath a torn banner, you discover a brass coffer raised on a "
            "stone ledge, mercifully above the chamber's dark water."
        ),
        "The Ashen Armory": (
            "You search the rusting weapon racks and uncover a smith's "
            "storage chest, its scorched lid buried beneath flakes of iron."
        ),
        "The Scribe's Tomb": (
            "A narrow compartment hides beneath the scribe's stone desk; "
            "you ease it open while brittle parchment rustles across the floor."
        ),
        "The Echoing Well": (
            "An abandoned adventurer's pack hangs from a peg inside the "
            "dry well's rim; you retrieve it as the buckle's clink echoes below."
        ),
        "The Hall of Chains": (
            "You lift a loose flagstone beneath the hanging chains and reveal "
            "an iron strongbox wrapped in a crumbling burial cloth."
        ),
        "The Pilgrim's Refuge": (
            "Beside the stone bench, a pilgrim's dried remains shelter a "
            "patched traveling bag; you carefully lift its flap clear of the dust."
        ),
        "The Starless Observatory": (
            "You discover a brass instrument case beneath the collapsed "
            "bronze rings, its star-patterned lid scratched by centuries of falling stone."
        ),
        "The Warden's Sanctum": (
            "Behind the Warden's throne, you uncover a stone reliquary "
            "bearing the royal seal; blue fire flickers across its worn edges."
        ),
    },
    2: {
        "The Tangled Threshold": (
            "You part the woven roots beside the stair and find a "
            "keeper's satchel tucked into a dry pocket of the ancient foundations."
        ),
        "The Saplit Walk": (
            "Amber light reveals a wooden storage box beneath the walkway; "
            "you peel a brittle skin of dried sap from its lid."
        ),
        "The Gardener's Crypt": (
            "Beside the kneeling gardener, a small wicker basket has "
            "hardened around its contents; you carefully loosen the roots holding it shut."
        ),
        "The Drowned Nursery": (
            "You search a shelf above the black water and discover a "
            "sealed clay storage jar, its faded label marked with a sapling."
        ),
        "The Thorn Gate": (
            "Beyond the collapsed gate, you uncover a pruning keeper's "
            "leather roll beneath the old hooks, pulling thorny vines from its clasp."
        ),
        "The Spore Chapel": (
            "A stone offering niche lies behind the mushrooms covering "
            "the shrine; you brush away pale caps and uncover a linen-wrapped cache."
        ),
        "The Root Archive": (
            "Between the clay tablets, a root has split an archive "
            "chest open; you clear the splintered wood to reach what remains inside."
        ),
        "The Hollow Oak": (
            "You search the petrified trunk's hollow and find a leather "
            "pouch wedged behind a fold of bark, its stitching preserved in dry sap."
        ),
        "The Binding Circle": (
            "At the circle's edge, you uncover a shallow keeper's box "
            "beneath a loose silver channel, carefully lifting its root-scarred lid."
        ),
        "The Keeper's Refuge": (
            "Beneath the moss-covered bench rests a gardener's supply "
            "crate; you slide it free while flakes of faded green paint fall away."
        ),
        "The Ember Well": (
            "An iron bucket rests beside the root-wrapped shaft, covered "
            "with an old oilcloth; you unfold the cloth in the well's red glow."
        ),
        "The Heartwood Cage": (
            "Within the Sentinel's loosened roots, you discover a stone "
            "keeper's casket, its weathered lid patterned with leaves and a sealed furnace."
        ),
    },
    3: {
        "The Cinder Landing": (
            "Beneath the iron platform's railing, you find a worker's "
            "tool chest coated in soot; its hinges complain as you lift the lid."
        ),
        "The Bellows Hall": (
            "You search an empty smithing station and uncover a "
            "riveted storage tin beneath the workbench, brushing furnace sparks from its dusty lid."
        ),
        "The Slag Canal": (
            "A scorched courier's bag lies behind the bridge's iron "
            "brace; you draw it onto the walkway, away from the cooling slag below."
        ),
        "The Chain Foundry": (
            "Between the giant casting molds, you discover a locked "
            "supply chest whose brittle clasp crumbles under your hand, revealing its dusty interior."
        ),
        "The Master Smith's Office": (
            "Under the ash-covered ledger, you find the smith's desk "
            "drawer hanging crooked; a careful tug frees it from its swollen wooden runners."
        ),
        "The Quenching Chamber": (
            "On a shelf above the cracked tanks sits a watertight "
            "metal case; you wipe condensation from its lid and release the corroded catches."
        ),
        "The Coal Lift": (
            "You uncover a small cargo crate behind the abandoned "
            "lift's counterweight, its shipping marks almost hidden beneath generations of coal dust."
        ),
        "The Broken Anvil": (
            "Inside the split anvil's shadow, a smith's leather apron "
            "covers a shallow storage tray; you fold the stiff material away."
        ),
        "The Furnace Shrine": (
            "Below the smiths' prayer tokens, you discover a stone "
            "offering basin covered by a bronze plate, still warm beside the enduring flame."
        ),
        "The Ash Barracks": (
            "An old footlocker waits beneath a bench of empty armor; "
            "you lift its lid, sending a fine cloud of ash through the stale air."
        ),
        "The Pressure Gallery": (
            "Behind a loose gauge panel, you find a maintenance "
            "satchel sheltered from the pipes' heat, its buckles furred with green copper stains."
        ),
        "The Great Crucible": (
            "Across the casting bridge, you uncover a heavy forge "
            "strongbox beneath a stone ledge, its lid stamped with the royal chainmaker's crest."
        ),
    },
    4: {
        "The Silent Causeway": (
            "Beside the black bridge's parapet, you discover a guard's "
            "supply casket wedged into the stone, its silver hinges cold beneath your fingers."
        ),
        "The Unlit Orrery": (
            "Beneath the turning bronze rings, you find an astronomer's "
            "storage case fitted into the plinth; its empty star-shaped clasp falls open."
        ),
        "The Hall of Unspoken Names": (
            "Behind a loosened marble tablet, you uncover a guardian's "
            "burial pouch, its faded stitching the only name left upon these scraped stones."
        ),
        "The Silver Anchorage": (
            "You search beneath the chain bolts and discover a "
            "rivet-studded maintenance chest, its lid dusted with silver shed by the ancient restraints."
        ),
        "The Empty Watch": (
            "Inside an abandoned sentry post, you find a narrow "
            "guard's locker; its unfastened door opens without a sound in the unnatural silence."
        ),
        "The Royal Deposition": (
            "Beneath the cracked testimony display rests an archivist's "
            "document box; you lift its warped lid, disturbing the dust around a faded royal seal."
        ),
        "The Mirror Prison": (
            "Under a cell's stone bench, you discover a prisoner's "
            "cloth bundle; you unfold it carefully, keeping your lantern turned away from the mirrors."
        ),
        "The Severed Conduit": (
            "Beside the broken rune circle, you uncover an engineer's "
            "supply tin beneath a fallen pipe bracket, its surface peppered with old scorch marks."
        ),
        "The Last Vigil": (
            "You search beside the knight's bedroll and find a "
            "worn campaign pack, carefully untying the cord that has held it shut for centuries."
        ),
        "The Chamber of Echoes": (
            "In a shallow wall recess, a leather dispatch case "
            "rests beneath fallen stone; the scrape of its lid returns as a strangely distant echo."
        ),
        "The Fallen Constellation": (
            "Below the silver ceiling studs, you uncover a ceremonial "
            "coffer draped in faded midnight cloth, its crown-shaped latch catching your lantern's light."
        ),
        "The Oathbound Gate": (
            "Behind the fallen knight's station, you find an oathkeeper's "
            "stone chest bound with tarnished silver; its lid bears the same crest as the gate."
        ),
    },
    5: {
        "The Foundation Rift": (
            "You search a dry ledge above the dark water and "
            "discover a mason's sealed supply box, its old royal crest worn almost smooth."
        ),
        "The First Foundation": (
            "Beside the tools sealed in stone, you uncover a "
            "builder's wooden casket in a shallow niche, protected by the city's oldest masonry."
        ),
        "The Coronation Grave": (
            "At the empty sarcophagus's foot, you find a ceremonial "
            "burial chest, its carved procession worn down to faceless figures beneath your hands."
        ),
        "The Chamber of the Offering": (
            "Beneath the altar's stone bowl, you discover a recessed "
            "offering tray; you slide it free without touching the dried handprint above."
        ),
        "The Blackwater Court": (
            "On the raised dais, you uncover a courtier's lacquered "
            "coffer, lifting its water-stained lid while dark ripples gather around the steps below."
        ),
        "The Crown's Shadow": (
            "Behind a fallen doorway stone, you find a velvet-lined "
            "travel case; its faded royal embroidery disappears briefly beneath the crown's impossible shadow."
        ),
        "The City's Memory": (
            "Among the shelves of humble belongings, you discover a "
            "cloth-wrapped communal storage box; you lift the covering with care for the forgotten hands."
        ),
        "The Last Chain": (
            "Beneath the straining restraint, you uncover a warden's "
            "iron supply chest, its edges buried in the silver dust falling from the final chain."
        ),
        "The Nameless Choir": (
            "You find a pilgrim's dried remains beside a cracked "
            "wall, a small satchel cradled against the ribs; you gently loosen its stiff leather ties."
        ),
        "The Sealed Dawn": (
            "Below the golden mosaic, you discover a shallow stone "
            "coffer carved with a rising sun, its interior sheltered from the passage's bitter cold."
        ),
        "The Heartless Antechamber": (
            "Beside the throne door, you uncover a royal attendant's "
            "chest beneath a fallen stone, its decayed lid engraved with the king's human likeness."
        ),
        "The Hollow Throne": (
            "At the throne's base, you discover a royal reliquary "
            "hidden beneath a broken flagstone; in the new silence, its lid opens with a soft scrape."
        ),
    },
}


def discovery_description(room: Room, floor: int) -> str:
    """Describe a successful search without inspecting or changing its loot."""
    return _DISCOVERIES.get(floor, {}).get(room.name, _FALLBACK)
