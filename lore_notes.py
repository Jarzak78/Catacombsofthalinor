"""Collectible accounts of Thalinor, uncovered in order of dungeon depth.

These immutable records have no dependency on the game, room, or renderer.
Their clues describe the game's existing commands; the documents themselves
belong to the people who built, tended, and guarded the catacombs.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LoreNote:
    id: str
    floor: int
    room_name: str
    title: str
    text: str
    hint: str


NOTES: dict[int, tuple[LoreNote, ...]] = {
    1: (
        LoreNote(
            id="first-lantern-letter",
            floor=1,
            room_name="The Broken Stair",
            title="A Letter to the Next Lantern",
            text=(
                "To whoever carries the next lantern: the guild calls these tombs "
                "a test of courage. My grandmother called them a promise. Every "
                "family in old Thalinor sent a mason here, even those too poor to "
                "afford a grave of their own. They laid silver in the doorframes "
                "and made us swear never to pry it out. I thought it superstition "
                "until the cracks began glowing from the wrong side. Bring light, "
                "keep your strength, and read what the dead left behind. A trial "
                "can be won with a sword; a promise must first be understood. "
                "—A former guild initiate"
            ),
            hint="Use 'loot' in a room without a living enemy to collect its treasure and any lore note.",
        ),
        LoreNote(
            id="scribe-seal-register",
            floor=1,
            room_name="The Scribe's Tomb",
            title="The Scribe's Seal Register",
            text=(
                "Registered this day: twelve lamps trimmed, seven grave doors "
                "repaired, one eastern seal recast. The families request that "
                "their ancestors' names remain visible beneath the warding "
                "marks. Request granted. These halls are still tombs, whatever "
                "the captains may require of them. The Warden has refused the "
                "new ceremonial blade and keeps the chipped one from its first "
                "watch. It turns neither toward thieves nor toward mourners, "
                "but toward the inner arch whenever the stone grows warm. I "
                "have added that observation to the register, though no column "
                "was provided for it. —Keeper of Names"
            ),
            hint="'wind' heals with Second Wind; in combat it uses your bonus action, leaving your action available.",
        ),
        LoreNote(
            id="roots-mason-warning",
            floor=1,
            room_name="The Rootbound Vault",
            title="A Mason's Warning About Roots",
            text=(
                "Do not cut the pale roots to straighten the coffins. We tried "
                "it in the south vault, and the silver seams rang like struck "
                "bells until morning. The roots were not here when we laid "
                "these stones. They came afterward, guided through holes too "
                "neat to be accidents. Some hand below knows its gardening. "
                "When I pressed my ear to the floor, I heard water, then metal, "
                "then something I will not write down. Leave the growth its "
                "passage. Let the honored dead sleep crooked if they must. "
                "The city has already paid too much for straight lines. "
                "—Master Mason Ilen"
            ),
            hint="'attack' spends an action; use 'end' when your turn is finished so combat can continue.",
        ),
        LoreNote(
            id="warden-threshold-orders",
            floor=1,
            room_name="The Warden's Sanctum",
            title="Orders for the First Threshold",
            text=(
                "Warden: your charge is the first threshold. You are neither "
                "judge of the buried nor conqueror of what lies beneath. Hold "
                "the arch while the roots hold the lower stone. Should the "
                "seals break beyond repair, yield only to one who can bear "
                "your blade and continue the watch. The passage bearing the "
                "lantern mark remains a refuge outside these failing wards; "
                "send the living there before they descend. We cannot promise "
                "that courage will be enough. We can promise that an unwounded "
                "hand carries the lantern farther. This order outlives the "
                "captain who signs it. —The Last Watch"
            ),
            hint="After defeating a guardian, use 'portal' in its room to visit Mira; 'shop' lists item IDs and prices.",
        ),
    ),
    2: (
        LoreNote(
            id="grove-keepers-welcome",
            floor=2,
            room_name="The Tangled Threshold",
            title="Instructions for a New Grove Keeper",
            text=(
                "You will miss the sky for your first seven shifts. Afterward "
                "you will know the amber glow well enough to mistake it for "
                "sunrise. Do not let that comfort make you careless. Every "
                "root in this grove has been trained through a silver channel. "
                "Water the young growth, clear the blocked drains, and record "
                "each broken seam. The gardeners above tend things so they may "
                "grow. We tend these so something else cannot. If you hear "
                "hammering beneath the nursery, mark the hour. If the hammering "
                "stops, wake the elder keeper before you wake anyone else."
            ),
            hint="Finish exploring and looting a floor before using its portal; you cannot return from Mira's sanctuary.",
        ),
        LoreNote(
            id="gardener-last-letter",
            floor=2,
            room_name="The Gardener's Crypt",
            title="The Gardener's Unsent Letter",
            text=(
                "Little sister, you asked whether anything blooms down here. "
                "Yesterday a white flower opened beside the watering bowl. "
                "By supper its petals were warm enough to burn my fingers. "
                "I left it standing. The elders say the roots must learn to "
                "drink the heat that would otherwise rise through our homes. "
                "I used to think we were burying a forest. Now I think we "
                "are teaching the earth to close its fist. Keep Mother's "
                "garden well. Tell her my hands are dirty, my knees ache, "
                "and for once all those hours she made me weed are serving "
                "a purpose. —Your stubborn brother"
            ),
            hint="A safe 'rest' takes one game hour, spends available Hit Dice to heal, and restores one Second Wind use.",
        ),
        LoreNote(
            id="root-archive-deliveries",
            floor=2,
            room_name="The Root Archive",
            title="Ledger of Warm Deliveries",
            text=(
                "First delivery: six sealed urns of furnace ash. Third "
                "delivery: twelve lengths of copper conduit, all still warm. "
                "Fifth delivery: no coal, no food, no word from the city. "
                "The forge sends only what keeps the binding alive. Roots "
                "beside the new pipes have thickened overnight, while the "
                "western beds have begun to gray. I requested a smith to "
                "repair the supply line. The lift returned empty with my "
                "request folded around a fresh handful of ash. Someone "
                "below is answering us, or some machine remembers that it "
                "should. Either way, we must keep receiving. —Archive Keeper"
            ),
            hint="Use 'rest 0' in a safe room to recover one Second Wind use and Action Surge without spending Hit Dice.",
        ),
        LoreNote(
            id="heartwood-binding-tablet",
            floor=2,
            room_name="The Heartwood Cage",
            title="The Binding Grove's Covenant",
            text=(
                "Here we plant no orchard. Here we close the wound under "
                "Thalinor. Let the roots drink the forge's warmth and knot "
                "themselves around the stone that would split. Let the "
                "Sentinel keep the furnace hatch, for the fire below both "
                "sustains this cage and threatens everything above it. To "
                "those who must pass: remember that flame alone did not "
                "save us, nor did root alone. We bound each to the other "
                "because neither could endure its charge apart. If one "
                "has failed, seek the other before you proclaim the city "
                "free. —The First Gardeners"
            ),
            hint="Mira's sanctuary restores your health and rest resources before you choose 'descend' to continue.",
        ),
    ),
    3: (
        LoreNote(
            id="cinder-shift-instructions",
            floor=3,
            room_name="The Cinder Landing",
            title="Instructions for the Night Shift",
            text=(
                "Leave the upper pipes open. The gardeners may complain "
                "about the heat, but their roots die without it. Check the "
                "lower pressure before adding coal; a hungry conduit will "
                "swallow a furnace's worth and ask for more. There are no "
                "swords on this week's order board. There are no plowshares "
                "either. Only links, anchors, seals, and replacements for "
                "the same. If anyone asks when we shall forge honest tools "
                "again, tell them this: every child sleeping above us is "
                "work our hammers still accomplish. Wear your gloves. We "
                "have enough empty benches. —Shift Foreman"
            ),
            hint="'buy armor' equips Mira's listed armor automatically; 'buy sword' upgrades your weapon.",
        ),
        LoreNote(
            id="chain-foundry-pattern",
            floor=3,
            room_name="The Chain Foundry",
            title="Pattern for a Chain That Holds",
            text=(
                "A plain iron link holds a body. A silvered link holds "
                "an oath. Our task requires both. Cut the same warding "
                "sign into every casting, whether it hangs beneath a "
                "tomb arch or disappears through the crucible floor. "
                "No smith may alter the pattern to save metal. Last "
                "week an apprentice shortened one stroke; the finished "
                "link whispered his mother's voice before it cooled. "
                "We broke it without answering. The apprentice lives, "
                "and he has transferred to the bellows. Record mistakes "
                "honestly. Shame is cheaper than another broken restraint. "
                "—The Chainwright's Manual"
            ),
            hint="An Ember stone bought from Mira deals 3d6 magic damage with 'ember', spending an action without an attack roll.",
        ),
        LoreNote(
            id="smith-unfinished-order",
            floor=3,
            room_name="The Master Smith's Office",
            title="The Order With No Charge",
            text=(
                "Received under the royal seal: restraints for one prisoner "
                "of royal station. Destination: the Starless Vault. Charge: "
                "left blank. The clerk told me to stop reading at that line. "
                "I have forged fetters for thieves and traitors, but never "
                "chains whose measurements came from the crown's own tailor. "
                "The court has sent no explanation, only enough silver to "
                "buy my silence twice. I took the metal and returned the "
                "second purse. If this work must be done, let the ledger "
                "show that at least one pair of hands asked why. "
                "—The Master Smith"
            ),
            hint="At fighter level 2, 'surge' grants one additional combat action; short or long rests restore Action Surge.",
        ),
        LoreNote(
            id="colossus-makers-plate",
            floor=3,
            room_name="The Great Crucible",
            title="The Colossus's Maker's Plate",
            text=(
                "Great Engine of the Crucible: preserve the flow to the "
                "binding grove; preserve the tension to the Starless Vault. "
                "Neither duty may cease while the royal prisoner remains "
                "below. Should no worker answer the bells, work without "
                "them. Should no fuel reach the landing, draw upon the "
                "reserve flame. Should the city forget why these furnaces "
                "burn, remember in its place. We have made your chest broad "
                "enough to bear what our own cannot. Forgive us the weight "
                "of it. Let no hand unmake your labor lightly. "
                "—Signed by the remaining smiths of Thalinor"
            ),
            hint="'stats' shows your resources; checking it spends no combat action and advances no game time.",
        ),
    ),
    4: (
        LoreNote(
            id="vault-watch-protocol",
            floor=4,
            room_name="The Silent Causeway",
            title="Protocol of the Starless Watch",
            text=(
                "No visitor crosses this causeway by rank alone. No herald "
                "speaks on behalf of the chamber below. Orders arrive "
                "written, sealed, and countersigned by a living watch "
                "captain. A voice may know your name. It may name your "
                "children, your mistakes, or the summer when the king "
                "walked unguarded through the market. These are not "
                "credentials. Listen for the forge chains instead. Their "
                "tension tells us what the dark would hide. If you must "
                "rest, post your lantern toward the passage and keep your "
                "back to a wall. Never appoint an echo your relief."
            ),
            hint="A long rest is safe only at the floor entrance, with no enemy, and at least 16 game hours after your last one ended.",
        ),
        LoreNote(
            id="unnamed-guardians-oath",
            floor=4,
            room_name="The Hall of Unspoken Names",
            title="The Oath Without Names",
            text=(
                "We erase our names so that no descendant must inherit "
                "this vigil. Let the marble remember our duty instead. "
                "We will hold the royal gate against armies, mourners, "
                "and our own desire to open it. We will not mistake a "
                "familiar voice for a rightful command. We will not let "
                "a crown make cruelty sacred. Should a traveler come "
                "who can end what we can only contain, let that traveler "
                "read the testimony beyond our watch before passing "
                "judgment. The king must remain below. The truth must "
                "not remain buried beside him. —The Starless Guardians"
            ),
            hint="'dodge' spends an action and gives visible enemy attacks Disadvantage until your next turn; use 'end' afterward.",
        ),
        LoreNote(
            id="last-vigil-journal",
            floor=4,
            room_name="The Last Vigil",
            title="A Watcher's Last Journal",
            text=(
                "Tonight it asked whether I had eaten. Exactly as he "
                "used to ask us on winter watch, when his cooks sent "
                "hot bread through the palace gates. I nearly answered. "
                "Then it asked the same question again, with the same "
                "pause and the same little laugh. A memory repeating "
                "itself is not a man. I wrote that on the wall where "
                "I can see it when I wake. Still, I cannot bring myself "
                "to hate the voice. Remember who he was; resist what "
                "he became. Both parts of that sentence are keeping "
                "me here. —The Last Watcher"
            ),
            hint="'potion' and 'wind' both use your bonus action in combat; choose one before ending that turn.",
        ),
        LoreNote(
            id="knight-sworn-testimony",
            floor=4,
            room_name="The Oathbound Gate",
            title="The Void Knight's Sworn Testimony",
            text=(
                "I witnessed no treason. Our king stepped willingly to "
                "the offering stone when the wound beneath Thalinor "
                "opened. He gave his living heart so the houses above "
                "would stand until dawn. They stood. He rose without "
                "it. At first we thought his silence grief; then the "
                "emptiness learned his voice and asked for every chain "
                "to be removed. He had commanded us, before the offering, "
                "to refuse that request whatever lips should speak it. "
                "I have obeyed for longer than any oath should last. "
                "If you pass me, free him from what wears his crown."
            ),
            hint="The defeated guardian's portal offers recovery and shopping before the final floor; collect this floor's remaining loot first.",
        ),
    ),
    5: (
        LoreNote(
            id="foundation-builders-record",
            floor=5,
            room_name="The Foundation Rift",
            title="A Record Beneath the First Stone",
            text=(
                "We set the first foundation beside a spring that made "
                "no sound. The surveyors called the hollow under it "
                "harmless, for a dropped stone never returned an echo. "
                "We built our homes above that silence and called it "
                "peace. Years later the spring turned black, and cracks "
                "ran through streets laid by hands already dead. The "
                "king asked for our oldest maps. We gave him these "
                "pages and watched him read the word harmless until "
                "his lantern burned low. Let whoever finds them now "
                "remember: a danger does not begin on the day we "
                "finally give it a name. —A City Surveyor"
            ),
            hint="'map' shows the dungeon layout and visited rooms without advancing time or spending an action.",
        ),
        LoreNote(
            id="offering-kings-letter",
            floor=5,
            room_name="The Chamber of the Offering",
            title="The King's Letter Before Dawn",
            text=(
                "To those who survive this night: do not call the "
                "offering victory merely because the earth grows "
                "still. The scholars promise that a living heart can "
                "close the wound. They cannot promise what will fill "
                "the place it leaves. I choose this knowing both "
                "things. If I return unchanged, bring me breakfast "
                "and let us mend the city together. If I return "
                "wrong, remember that my last free command was to "
                "protect you from me. No crown, no plea, and no "
                "kindness borrowed from my memory can cancel it. "
                "Let there be a morning for someone."
            ),
            hint="Save healing for injuries: using 'potion' or 'wind' at full HP keeps that resource instead of consuming it.",
        ),
        LoreNote(
            id="city-memory-inventory",
            floor=5,
            room_name="The City's Memory",
            title="An Inventory of Ordinary Lives",
            text=(
                "Received for the memorial: one child's cup, chipped "
                "at the handle; one mason's cord; one gardener's "
                "knife; a ribbon from a wedding that took place after "
                "the terrible night. We were asked to bring jewels. "
                "The king's housekeeper refused them. She said he "
                "had not given his heart for treasure, and would "
                "have laughed to see a royal monument full of it. "
                "So we have brought evidence of mornings. The cup "
                "held milk again. The cord measured a repaired home. "
                "The knife pruned a branch in sunlight. The ribbon "
                "was worn by someone who lived."
            ),
            hint="'inventory' lists your potions, equipped gear, and magic items; reviewing it does not spend an action.",
        ),
        LoreNote(
            id="hollow-throne-final-seal",
            floor=5,
            room_name="The Hollow Throne",
            title="The Last Seal's Promise",
            text=(
                "We cannot destroy the hunger while it wears the "
                "king's strength. We can only bind it: tomb seals "
                "above, living roots beneath them, an enduring forge, "
                "and guardians who remember their oaths. If these "
                "things fail one by one, someone will have to stand "
                "where we could not. To that person we leave no "
                "command to save the crown. Let it fall. When the "
                "false heartbeat stops, the chains will no longer "
                "need our dead hands to hold them. Our king bought "
                "the city a morning. May you give him the rest "
                "he never had. —The Makers of the Final Seal"
            ),
            hint="After the final guardian falls, use 'portal' and then 'descend' at Mira's sanctuary to return to daylight.",
        ),
    ),
}
