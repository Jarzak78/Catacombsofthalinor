"""Authored room-to-art matches, independent of random map placement.

Each floor atlas has two columns and six rows.  Its twelve panels follow the
floor's authored entrance, ten ordinary rooms, and guardian chamber.  Exact
room identity selects a panel; neither room coordinates nor keyword guessing
can accidentally give a nursery the picture of a forge or reveal another room.
"""

from dataclasses import dataclass
from types import MappingProxyType

from floor_lore import LORE


ATLAS_COLUMNS = 2
ATLAS_ROWS = 6


@dataclass(frozen=True)
class RoomArt:
    id: str
    floor: int
    name: str
    description: str
    atlas: str
    cell: int
    landmarks: tuple[str, ...]
    # Painting fractions: horizontal center, floor contact, width, height.
    # Rendering projects these through the same crop as the room background.
    # A passage is painted here only when the live map actually has that exit.
    # None means foreground architecture obscures a far passage in this portrait.
    front_passage: tuple[float, float, float, float] | None


# Concrete visual references for every authored panel.  These are a source
# record for the room paintings, not extra room objects, loot, or interactions.
_LANDMARKS = (
    (
        ("cracked stairway", "moonlight"),
        ("broken statues", "carved stone mouths"),
        ("pale ceiling roots", "empty stone coffins"),
        ("silver altar", "cold candles"),
        ("water between flagstones", "torn banners", "battlefield mural"),
        ("rusting weapon racks", "faint runes"),
        ("stone desk", "parchment fragments", "faded inscription"),
        ("central dry well",),
        ("heavy hanging chains",),
        ("stone bench", "shattered waterskin", "scratched sun"),
        ("collapsed dome", "solid rock ceiling", "bronze astronomical rings"),
        ("blue fire", "ancient throne", "sealed arch", "straining roots"),
    ),
    (
        ("woven roots", "warm sap", "foundation stair"),
        ("root-covered walkway", "amber sap", "trapped insects"),
        ("kneeling skeleton", "dry watering bowl", "roots through hands"),
        ("black water", "broken seed jars", "sapling mural"),
        ("collapsed gate", "barbed vines", "pruning hooks"),
        ("pale mushrooms", "gardener shrine", "drifting spores"),
        ("clay tablets", "thick roots"),
        ("split petrified trunk",),
        ("silver floor channels", "roots", "fractured stone"),
        ("moss-covered bench", "wall tally marks"),
        ("root-wrapped shaft", "red light", "dripping sap"),
        ("enormous coiling root", "cracked furnace hatch"),
    ),
    (
        ("iron platform", "charred ceiling roots", "furnace pipes"),
        ("leather bellows", "sparks", "empty smithing stations"),
        ("narrow bridge", "cooling slag canal", "burned footprints"),
        ("giant chain links", "casting molds", "seal runes"),
        ("ash-covered ledger", "smith's office"),
        ("cracked quenching tanks", "steam", "frosted silver chain"),
        ("abandoned lift", "soot-black shaft", "cargo label"),
        ("split anvil", "impressed handprint"),
        ("smiths' prayer tokens", "enduring flame", "inscription"),
        ("empty armor", "benches", "cold meal", "scratched helmet"),
        ("copper gauges", "wall pipes", "glass inspection window"),
        ("molten casting pit", "bridge", "descending chains"),
    ),
    (
        ("black-stone bridge", "ceiling chains", "lightless shaft"),
        ("bronze orrery rings", "missing central star", "chain tethers"),
        ("black marble tablets", "scraped inscriptions"),
        ("bedrock chain anchors", "hovering broken chain end"),
        ("stone sentry posts", "blank wall", "dark stain"),
        ("sealed testimony", "cracked glass"),
        ("narrow cells", "covered mirrors", "slipped cloth"),
        ("forge pipe", "broken rune circle", "sparks"),
        ("dusty bedroll", "stone cup", "wall inscription"),
        ("echoing stone chamber", "deep wall recesses"),
        ("silver ceiling studs", "royal crown constellation"),
        ("converging silver chains", "royal-crest gate"),
    ),
    (
        ("ancient foundations", "worn royal crest", "dark water"),
        ("builders' tools in transparent stone", "unfinished inscription"),
        ("empty sarcophagus", "royal procession relief", "faceless king carving"),
        ("stone offering bowl", "altar", "royal seal", "dried handprint"),
        ("flooded audience hall", "dark ripples", "empty dais"),
        ("painted broken crown", "doorway", "unnatural shadow"),
        ("rock shelves", "child's cup", "mason's cord", "gardener's knife"),
        ("chest-high silver restraint", "silver dust"),
        ("many wall cracks",),
        ("golden sunlight mosaic", "narrow royal passage"),
        ("throne door", "inscription", "blackening stone"),
        ("bedrock throne", "curving foundations", "converging chains"),
    ),
)


# Authored against each painting rather than a single center-screen doorway.
# Keep openings on peripheral masonry when the room's defining object occupies
# the rear center.  These placements neither create nor hide a map connection.
_FRONT_PASSAGES = (
    (
        (.77, .80, .12, .52), (.50, .80, .14, .55),
        (.95, .82, .075, .50), (.16, .80, .11, .48),
        (.125, .80, .10, .50), (.50, .80, .14, .56),
        (.93, .80, .09, .48), (.20, .80, .12, .48),
        (.56, .80, .11, .48), (.24, .82, .12, .48),
        None, (.52, .82, .075, .50),  # Observatory rubble obscures the far wall.
    ),
    (
        (.70, .66, .12, .50), (.50, .53, .11, .45),
        (.74, .67, .12, .50), None,  # Nursery jars and mural fill the rear wall.
        (.92, .82, .08, .47), (.94, .76, .075, .42),
        (.90, .80, .08, .43), (.16, .80, .10, .46),
        (.50, .29, .075, .24), (.63, .79, .09, .45),
        None, (.13, .81, .09, .45),  # Ember Well rim obscures the far floor.
    ),
    (
        (.50, .59, .12, .50), (.52, .60, .12, .50),
        (.50, .45, .11, .44), (.32, .80, .10, .47),
        (.70, .63, .12, .50), (.40, .69, .09, .42),
        (.83, .81, .11, .50), (.75, .70, .18, .58),
        (.13, .81, .09, .50), (.62, .46, .085, .40),
        None, (.50, .56, .10, .45),  # Pressure Gallery pipework hides the wall.
    ),
    (
        None, (.70, .76, .10, .48),  # Silent Causeway has no visible far wall.
        (.82, .80, .12, .54), (.90, .80, .10, .49),
        (.70, .80, .10, .50), (.92, .80, .08, .50),
        (.80, .65, .08, .40), (.70, .64, .10, .49),
        (.83, .82, .12, .52), (.70, .80, .11, .50),
        (.50, .97, .12, .35), None,  # Oathbound Gate chains obscure the far wall.
    ),
    (
        (.80, .80, .10, .50), (.16, .80, .085, .48),
        (.94, .82, .075, .48), (.15, .83, .10, .50),
        (.50, .41, .12, .35), (.17, .82, .10, .50),
        (.50, .82, .12, .50), (.94, .82, .07, .43),
        (.73, .82, .10, .50), (.50, .96, .08, .22),
        (.84, .83, .09, .50), None,  # Hollow Throne chains cover its low wall.
    ),
)


def _build_catalog():
    by_id, by_room = {}, {}
    for floor, (lore, landmarks, passages) in enumerate(zip(LORE, _LANDMARKS, _FRONT_PASSAGES), 1):
        rooms = (lore.entrance, *lore.rooms, lore.sanctum)
        if (len(rooms) != ATLAS_COLUMNS * ATLAS_ROWS
                or len(landmarks) != len(rooms) or len(passages) != len(rooms)):
            raise ValueError(f"Floor {floor} needs one art panel per authored room.")
        for cell, ((name, description), features) in enumerate(zip(rooms, landmarks)):
            art_id = f"floor_{floor}_room_{cell:02d}"
            identity = (floor, name)
            if identity in by_room:
                raise ValueError(f"Duplicate room art identity: {identity!r}")
            spec = RoomArt(art_id, floor, name, description,
                           f"floor_{floor}.png", cell, features, passages[cell])
            by_id[art_id] = spec
            by_room[identity] = spec
    if len(LORE) != len(_LANDMARKS) or len(LORE) != len(_FRONT_PASSAGES):
        raise ValueError("Every dungeon floor needs an authored room art set.")
    return MappingProxyType(by_id), MappingProxyType(by_room)


ROOM_ART_BY_ID, ROOM_ART_BY_ROOM = _build_catalog()
ROOM_ART = ROOM_ART_BY_ID


def room_art_for(floor: int, name: str) -> RoomArt | None:
    """Match an exact, already visible room identity; unknown rooms fall back."""
    if type(floor) is not int or not isinstance(name, str):
        return None
    return ROOM_ART_BY_ROOM.get((floor, name))


def room_art_by_id(art_id: str) -> RoomArt | None:
    """Resolve a public art identifier without exposing any live dungeon data."""
    return ROOM_ART_BY_ID.get(art_id) if isinstance(art_id, str) else None
