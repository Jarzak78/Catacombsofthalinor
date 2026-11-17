"""D&D-inspired equipment definitions, independent of characters and loot.

Weapons and armor use familiar tabletop damage dice, armor classes, and
enchantment bonuses. Prices suit this five-floor solo campaign rather than
the tabletop economy. The three wizard vestments are homebrew clothing;
they remain unarmored so Mage Armor can improve their base protection.
"""

from dataclasses import dataclass
import re


MAX_ENCHANTMENT = 3
ARMOR_SLOTS = ("boots", "gloves", "pants", "torso", "helmet")
RARITIES = ("mundane", "uncommon", "rare", "very rare")
ARMOR_RARITIES = ("mundane", "rare", "very rare", "legendary")
_CLASS_IDS = ("fighter", "rogue", "wizard")
_WEAPON_SURCHARGES = (0, 35, 80, 140)
_ARMOR_SURCHARGES = (0, 30, 65, 115)

# These bonuses are deliberately separate from an item's enchantment. Ability
# effects increase the score, not its modifier; the character model applies the
# strongest equipped effect of each type and caps ability scores at 20.
ARMOR_AFFIXES = {
    "might": ("Might", "strength", ("fighter",)),
    "agility": ("Agility", "dexterity", _CLASS_IDS),
    "insight": ("Insight", "wisdom", _CLASS_IDS),
    "intellect": ("Intellect", "intelligence", ("wizard",)),
    "presence": ("Presence", "charisma", _CLASS_IDS),
    "shadow": ("Shadow", "stealth", ("fighter", "rogue")),
    "vigilance": ("Vigilance", "perception", _CLASS_IDS),
}


@dataclass(frozen=True)
class EquipmentSpec:
    """One mundane equipment type and the classes proficient with it."""

    id: str
    name: str
    kind: str
    classes: tuple[str, ...]
    base_price: int
    description: str
    damage_dice: tuple[int, int] = (1, 4)
    finesse: bool = False
    two_handed: bool = False
    mastery: str = ""
    base_ac: int = 10
    dex_cap: int | None = None
    unarmored: bool = False
    stealth_disadvantage: bool = False
    focus: bool = False
    slot: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not re.fullmatch(r"[a-z]+(?:_[a-z]+)*", self.id):
            raise ValueError("Equipment IDs must contain lowercase words joined by underscores.")
        if self.kind not in ("weapon", "armor"):
            raise ValueError("Equipment kind must be weapon or armor.")
        if not isinstance(self.slot, str):
            raise ValueError("Equipment slot must be a string.")
        slot = self.slot or ("weapon" if self.kind == "weapon" else "torso")
        if ((self.kind == "weapon" and slot != "weapon")
                or (self.kind == "armor" and slot not in ARMOR_SLOTS)):
            raise ValueError("Equipment slot must match its weapon or armor kind.")
        object.__setattr__(self, "slot", slot)
        if not isinstance(self.classes, tuple) or not self.classes:
            raise ValueError("Equipment must specify a tuple of proficient classes.")
        if any(class_id not in _CLASS_IDS for class_id in self.classes):
            raise ValueError("Equipment classes must be fighter, rogue, or wizard.")
        if len(set(self.classes)) != len(self.classes):
            raise ValueError("Equipment classes cannot contain duplicates.")
        if type(self.base_price) is not int or self.base_price < 1:
            raise ValueError("Equipment price must be a positive integer.")
        if (not isinstance(self.damage_dice, tuple) or len(self.damage_dice) != 2
                or any(type(die) is not int or die < 1 for die in self.damage_dice)):
            raise ValueError("Equipment damage dice must be two positive integers.")
        if self.mastery not in ("", "sap", "vex"):
            raise ValueError("Equipment mastery must be sap, vex, or empty.")
        if type(self.base_ac) is not int or self.base_ac < 0:
            raise ValueError("Equipment base AC must be a nonnegative integer.")
        if self.dex_cap is not None and (type(self.dex_cap) is not int or self.dex_cap < 0):
            raise ValueError("Equipment Dexterity cap must be nonnegative or None.")


EQUIPMENT: dict[str, EquipmentSpec] = {
    "longsword": EquipmentSpec(
        "longsword", "Longsword", "weapon", ("fighter",), 10,
        "A straight, double-edged steel blade balances a narrow crossguard against a leather-wrapped hilt. "
        "The one-handed grip leaves your other hand free, and the blade's deliberate strikes can sap a foe's momentum.",
        damage_dice=(1, 8), mastery="sap"),
    "battleaxe": EquipmentSpec(
        "battleaxe", "Battleaxe", "weapon", ("fighter",), 10,
        "A broad crescent of sharpened steel sits on a short ash haft, its edge nicked by earlier battles. "
        "The one-handed axe concentrates its weight into a powerful chopping stroke.",
        damage_dice=(1, 8)),
    "warhammer": EquipmentSpec(
        "warhammer", "Warhammer", "weapon", ("fighter",), 10,
        "A square iron hammerhead is fitted to an oak handle reinforced with dark metal bands. "
        "The short, one-handed weapon delivers weighty blows through its blunt striking face.",
        damage_dice=(1, 8)),
    "greatsword": EquipmentSpec(
        "greatsword", "Greatsword", "weapon", ("fighter",), 35,
        "A long steel blade rises from a generous crossguard and a grip wrapped for both hands. "
        "Its broad cuts carry two damage dice, but holding it means setting aside your shield.",
        damage_dice=(2, 6), two_handed=True),
    "greataxe": EquipmentSpec(
        "greataxe", "Greataxe", "weapon", ("fighter",), 30,
        "A heavy axehead crowns a long hardwood haft, with a leather grip below a steel collar. "
        "Both hands guide its sweeping chop, trading your shield for a wide range of possible damage.",
        damage_dice=(1, 12), two_handed=True),
    "mace": EquipmentSpec(
        "mace", "Mace", "weapon", ("fighter",), 5,
        "Iron flanges surround the head of this compact mace, above a scuffed leather handle. "
        "Its simple one-handed swings can sap a struck opponent's momentum.",
        damage_dice=(1, 6), mastery="sap"),
    "spear": EquipmentSpec(
        "spear", "Spear", "weapon", ("fighter",), 4,
        "A leaf-shaped steel point is socketed onto a sturdy shaft, with cord wrapped around the handhold. "
        "This spear is used one-handed for close thrusts in the catacombs' cramped passages.",
        damage_dice=(1, 6)),
    "rapier": EquipmentSpec(
        "rapier", "Rapier", "weapon", ("fighter", "rogue"), 12,
        "A slender steel blade extends from a swept basket guard that shelters the wielder's fingers. "
        "The finesse weapon favors precise thrusts, and a successful strike can vex a foe into exposing an opening.",
        damage_dice=(1, 8), finesse=True, mastery="vex"),
    "shortsword": EquipmentSpec(
        "shortsword", "Shortsword", "weapon", ("fighter", "rogue"), 7,
        "A short, double-edged blade has a simple guard and a closely fitted leather grip. "
        "Its compact finesse handling favors quick strikes that can vex an opponent into leaving an opening.",
        damage_dice=(1, 6), finesse=True, mastery="vex"),
    "dagger": EquipmentSpec(
        "dagger", "Dagger", "weapon", _CLASS_IDS, 2,
        "A small steel blade tapers to a sharp point above a plain grip and a narrow crosspiece. "
        "It serves as a light finesse weapon in close combat; this dagger is neither a spell focus nor a ranged weapon here.",
        damage_dice=(1, 4), finesse=True),
    "scimitar": EquipmentSpec(
        "scimitar", "Scimitar", "weapon", ("fighter", "rogue"), 10,
        "A single curved edge sweeps from a brass guard, while a leather-wrapped hilt rests easily in one hand. "
        "The finesse blade suits quick cuts and careful footwork in close combat.",
        damage_dice=(1, 6), finesse=True),
    "quarterstaff": EquipmentSpec(
        "quarterstaff", "Quarterstaff", "weapon", ("fighter", "wizard"), 3,
        "A smooth hardwood staff bears iron ferrules and worn handholds polished by long use. "
        "It is wielded one-handed in this game; any enchantment strengthens its physical strikes rather than your spells.",
        damage_dice=(1, 6)),
    "arcane_staff": EquipmentSpec(
        "arcane_staff", "Arcane Staff", "weapon", ("wizard",), 15,
        "An inset crystal rests in a forked staff head, with fine copper lines winding down its wooden shaft. "
        "The crystal acts as a wizard's focus, allowing an enchanted staff to strengthen both physical strikes and spellcasting.",
        damage_dice=(1, 6), focus=True),
    "padded": EquipmentSpec(
        "padded", "Padded Armor", "armor", ("fighter", "rogue"), 5,
        "Layers of quilted linen form a thick vest, tied at the sides with sturdy cloth cords. "
        "The light torso armor cushions the body, though its bulky folds rustle when you move quietly.",
        base_ac=11, stealth_disadvantage=True),
    "leather": EquipmentSpec(
        "leather", "Leather Armor", "armor", ("fighter", "rogue"), 8,
        "A supple leather vest is stiffened across the chest and shoulders, leaving its joints flexible. "
        "Close stitching and a fitted belt let this light torso armor move without interfering with stealth.",
        base_ac=11),
    "studded_leather": EquipmentSpec(
        "studded_leather", "Studded Leather", "armor", ("fighter", "rogue"), 20,
        "Small metal rivets reinforce a fitted leather vest along its chest, shoulders, and back. "
        "The flexible light torso armor protects better than plain leather while leaving your movements quiet.",
        base_ac=12),
    "scale_mail": EquipmentSpec(
        "scale_mail", "Scale Mail", "armor", ("fighter",), 25,
        "Rows of overlapping metal scales are sewn onto a tough leather coat that covers the torso. "
        "The medium armor bends with limited agility, while its scales scrape audibly against one another.",
        base_ac=14, dex_cap=2, stealth_disadvantage=True),
    "breastplate": EquipmentSpec(
        "breastplate", "Breastplate", "armor", ("fighter",), 45,
        "A shaped steel breastplate curves over the chest, secured to a padded backpiece by leather straps. "
        "This medium torso armor leaves the joints free and avoids the noisy overlaps of scale mail.",
        base_ac=14, dex_cap=2),
    "half_plate": EquipmentSpec(
        "half_plate", "Half Plate", "armor", ("fighter",), 70,
        "Broad steel plates cover a padded torso harness, joined by straps and overlapping metal fittings. "
        "The medium armor offers strong protection and some freedom of movement, but its fittings rattle during stealth.",
        base_ac=15, dex_cap=2, stealth_disadvantage=True),
    "chain_mail": EquipmentSpec(
        "chain_mail", "Chain Mail", "armor", ("fighter",), 25,
        "A heavy shirt of interlocked iron rings hangs over a thick padded lining, secured by a broad belt. "
        "This chain-mail torso piece relies on its rings for protection and jingles when you try to move silently.",
        base_ac=16, dex_cap=0, stealth_disadvantage=True),
    "splint": EquipmentSpec(
        "splint", "Splint Armor", "armor", ("fighter",), 65,
        "Long metal strips are riveted to a thick leather torso harness, with padding beneath each rigid panel. "
        "The heavy armor provides fixed protection, though its weight and fittings hinder stealth.",
        base_ac=17, dex_cap=0, stealth_disadvantage=True),
    "plate": EquipmentSpec(
        "plate", "Plate Armor", "armor", ("fighter",), 120,
        "Carefully fitted steel plates enclose the torso, with turned edges and leather straps over a padded lining. "
        "The heavy breast-and-back harness provides the strongest mundane torso protection, at the cost of noisy movement.",
        base_ac=18, dex_cap=0, stealth_disadvantage=True),
    "robes": EquipmentSpec(
        "robes", "Robes", "armor", ("wizard",), 5,
        "A plain woven robe has loose sleeves, a reinforced collar, and a cord belt for keeping the hem clear. "
        "The cloth torso garment is ordinary clothing rather than armor, leaving room for Mage Armor's protective ward.",
        base_ac=10, unarmored=True),
    "warded_robes": EquipmentSpec(
        "warded_robes", "Warded Robes", "armor", ("wizard",), 15,
        "Fine protective stitching runs through the lining of a dark robe, with a soft collar and fitted cuffs. "
        "These homebrew torso vestments provide modest protection while counting as unarmored clothing for Mage Armor.",
        base_ac=11, unarmored=True),
    "battlemage_robes": EquipmentSpec(
        "battlemage_robes", "Battlemage Robes", "armor", ("wizard",), 30,
        "Layered fabric and reinforced seams form a fitted robe, its heavy hems kept clear by a sturdy sash. "
        "These homebrew torso vestments offer the best mundane wizard clothing protection and remain compatible with Mage Armor.",
        base_ac=12, unarmored=True),
}

# Accessories occupy their own slots. Their mundane protection is already
# represented by the torso's armor profile: adding a plain helmet does not
# create a second base AC or a new Dexterity cap.
_ACCESSORY_FAMILIES = {
    "cloth": (("wizard",), 2, {
        "boots": ("Cloth Boots", "Soft fabric boots have reinforced soles and close ties at the ankle. Their quiet folds keep dust and loose grit out of your footwear."),
        "gloves": ("Cloth Gloves", "Thin woven gloves fit closely around the fingers, with reinforced palms. The supple fabric leaves your hands free to grip a staff or trace spell gestures."),
        "pants": ("Cloth Trousers", "Loose woven trousers have a drawstring waist and double-stitched knees. A narrow cut keeps their hems clear of stairs and rubble."),
        "helmet": ("Cloth Hood", "A close-woven hood falls from a reinforced brow to a soft neck flap. Its light folds shade your face without enclosing it in metal."),
    }),
    "leather": (("fighter", "rogue"), 3, {
        "boots": ("Leather Boots", "Soft leather boots have firm soles and stitched cuffs fitted around the ankle. Their flexible shape suits careful footing through broken masonry."),
        "gloves": ("Leather Gloves", "Supple leather gloves are padded across the palms and knuckles, with snug straps at the wrists. The fingers bend freely around a blade's grip."),
        "pants": ("Leather Pants", "Flexible leather trousers have reinforced knees and a closely fitted belt. The stitched panels bend with your stride rather than clattering against one another."),
        "helmet": ("Leather Cap", "A fitted leather cap covers the brow and crown, lined with soft cloth. Its short side flaps leave your face and ears unobstructed."),
    }),
    "mail": (("fighter",), 4, {
        "boots": ("Mail Boots", "Linked iron rings cover padded boots, with strong leather soles beneath them. Straps hold the metal close around the ankles instead of leaving loose lengths to drag."),
        "gloves": ("Mail Gloves", "Small interlocked rings cover the backs of padded leather gloves. Their palms stay supple enough for a firm one-handed or two-handed weapon grip."),
        "pants": ("Mail Chausses", "Close rows of iron rings cover padded leggings, fastened to a sturdy belt. This leg piece completes a warrior's outfit without replacing the torso armor's protection profile."),
        "helmet": ("Mail Coif", "A fitted hood of fine iron rings settles over a padded cloth lining. A shaped opening leaves the face clear while the lower rings drape over the neck."),
    }),
}
for _family, (_classes, _price, _pieces) in _ACCESSORY_FAMILIES.items():
    for _slot, (_name, _description) in _pieces.items():
        _base_id = f"{_family}_{_slot}"
        EQUIPMENT[_base_id] = EquipmentSpec(
            _base_id, _name, "armor", _classes, _price, _description,
            base_ac=0, unarmored=_family == "cloth", slot=_slot)

DEFAULT_WEAPONS = {"fighter": "longsword", "rogue": "rapier", "wizard": "quarterstaff"}
DEFAULT_ARMOR = {"fighter": "chain_mail", "rogue": "studded_leather", "wizard": "robes"}
DEFAULT_ARMOR_PIECES = {
    class_id: {
        slot: DEFAULT_ARMOR[class_id] if slot == "torso" else f"{family}_{slot}"
        for slot in ARMOR_SLOTS
    }
    for class_id, family in (("fighter", "mail"), ("rogue", "leather"), ("wizard", "cloth"))
}


@dataclass(frozen=True)
class EquipmentItem:
    """A serializable equipment instance with a mundane or magical bonus."""

    base_id: str
    bonus: int = 0
    affix: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.base_id, str) or self.base_id not in EQUIPMENT:
            raise ValueError("Unknown equipment type.")
        if type(self.bonus) is not int or not 0 <= self.bonus <= MAX_ENCHANTMENT:
            raise ValueError(f"Equipment bonus must be an integer from 0 to {MAX_ENCHANTMENT}.")
        if not isinstance(self.affix, str):
            raise ValueError("Armor affix must be a known name or empty.")
        if self.affix:
            if self.kind != "armor" or not self.bonus or self.affix not in ARMOR_AFFIXES:
                raise ValueError("Only enchanted armor can carry a known armor affix.")
            allowed_classes = ARMOR_AFFIXES[self.affix][2]
            if not any(class_id in allowed_classes for class_id in self.spec.classes):
                raise ValueError("Armor affix must suit a class proficient with this armor.")

    @property
    def id(self) -> str:
        result = f"{self.base_id}_{self.bonus}" if self.bonus else self.base_id
        return f"{result}_{self.affix}" if self.affix else result

    @property
    def name(self) -> str:
        result = f"{self.spec.name} +{self.bonus}" if self.bonus else self.spec.name
        return f"{result} of {ARMOR_AFFIXES[self.affix][0]}" if self.affix else result

    @property
    def spec(self) -> EquipmentSpec:
        return EQUIPMENT[self.base_id]

    @property
    def kind(self) -> str:
        return self.spec.kind

    @property
    def slot(self) -> str:
        return self.spec.slot

    @property
    def buffs(self) -> dict[str, int]:
        """Return detached equipped effects; an enchantment has at most one."""
        return {ARMOR_AFFIXES[self.affix][1]: self.bonus} if self.affix else {}

    @property
    def rarity(self) -> str:
        rarities = RARITIES if self.kind == "weapon" else ARMOR_RARITIES
        return rarities[self.bonus]

    @property
    def sale_value(self) -> int:
        return max(1, equipment_price(self) // 2)

    @property
    def description(self) -> str:
        details = [self.spec.description,
                   f"Rarity: {self.rarity}. Slot: {self.slot}."]
        if self.kind == "weapon":
            count, sides = self.spec.damage_dice
            details.append(f"Weapon damage: {count}d{sides}; "
                           f"{'two-handed' if self.spec.two_handed else 'one-handed'}.")
            if self.spec.two_handed:
                details.append("You cannot use a shield while wielding this weapon.")
            if self.spec.finesse:
                details.append("Finesse uses the higher Strength or Dexterity modifier.")
            if self.spec.mastery == "sap":
                details.append("Sap: a hit gives the foe disadvantage on its next attack.")
            elif self.spec.mastery == "vex":
                details.append("Vex: a hit grants advantage on your next attack against that foe.")
            if self.bonus:
                effect = f"+{self.bonus} to attack and damage rolls"
                if self.spec.focus:
                    effect += ", also applied to wizard spell attacks and spell save DC"
                details.append(f"Magical enchantment: {effect}.")
                if not self.spec.focus:
                    details.append("This enchantment affects weapon strikes, not spells.")
        elif self.slot == "torso":
            if self.spec.dex_cap == 0:
                details.append(f"Base AC {self.spec.base_ac}; Dexterity does not alter this base.")
            elif self.spec.dex_cap is None:
                details.append(f"Base AC {self.spec.base_ac} + full Dexterity modifier.")
            else:
                details.append(f"Base AC {self.spec.base_ac} + Dexterity modifier "
                               f"(maximum +{self.spec.dex_cap}).")
            if self.spec.unarmored:
                details.append("Counts as unarmored clothing; Mage Armor can improve its base AC.")
            if self.spec.stealth_disadvantage:
                details.append("Wearing this torso armor gives disadvantage on stealth checks.")
        else:
            details.append("Mundane protection is included in your torso armor profile; "
                           "this piece adds no separate base AC or Dexterity limit.")
        if self.kind == "armor" and self.bonus:
            details.append(f"Magical enchantment: +{self.bonus} to AC; "
                           "the combined armor enchantment bonus is capped at +3 across all five slots.")
        if self.affix:
            target, amount = next(iter(self.buffs.items()))
            if target in ("stealth", "perception"):
                details.append(f"{ARMOR_AFFIXES[self.affix][0]}: +{amount} to {target.title()} checks while equipped.")
            else:
                details.append(f"{ARMOR_AFFIXES[self.affix][0]}: +{amount} to your {target.title()} "
                               "score while equipped, up to a score of 20; this increases the score rather than its modifier directly.")
            details.append("Only the strongest equipped bonus to the same score or skill applies.")
        return " ".join(details)


def _canonical_class(class_id: str) -> str:
    if not isinstance(class_id, str):
        raise ValueError("Choose warrior, rogue, or wizard.")
    normalized = class_id.strip().lower()
    normalized = {"warrior": "fighter", "rouge": "rogue"}.get(normalized, normalized)
    if normalized not in _CLASS_IDS:
        raise ValueError("Choose warrior, rogue, or wizard.")
    return normalized


def equipment_options(class_id: str, kind: str | None = None) -> tuple[EquipmentSpec, ...]:
    """Return the class's proficient equipment, optionally filtered by kind."""
    canonical_class = _canonical_class(class_id)
    if kind not in (None, "weapon", "armor"):
        raise ValueError("Equipment kind must be weapon, armor, or None.")
    return tuple(spec for spec in EQUIPMENT.values()
                 if canonical_class in spec.classes and (kind is None or spec.kind == kind))


def armor_affix_options(class_id: str) -> tuple[str, ...]:
    """Return the loot affixes whose actual effects suit the chosen class."""
    canonical_class = _canonical_class(class_id)
    return tuple(affix for affix, (_, _, classes) in ARMOR_AFFIXES.items()
                 if canonical_class in classes)


def make_equipment(base_id: str, bonus: int = 0, affix: str = "") -> EquipmentItem:
    """Construct and validate an equipment item without mutating a character."""
    return EquipmentItem(base_id, bonus, affix)


def equipment_price(item: EquipmentItem) -> int:
    """Return Mira's campaign price; recovered equipment sells for half."""
    if not isinstance(item, EquipmentItem):
        raise ValueError("An EquipmentItem is required to determine its price.")
    surcharges = _WEAPON_SURCHARGES if item.kind == "weapon" else _ARMOR_SURCHARGES
    return item.spec.base_price + surcharges[item.bonus] + (15 * item.bonus if item.affix else 0)


def resolve_equipment_id(text: str) -> str | None:
    """Recognize a catalog ID or full display name without guessing unknown items."""
    if not isinstance(text, str):
        return None
    candidate = text.strip().casefold()
    if not candidate:
        return None
    candidate = re.sub(r"\s+", " ", candidate)
    affix = ""
    for affix_id, (label, _, _) in ARMOR_AFFIXES.items():
        for suffix in (f" of {label.casefold()}", f"_{affix_id}"):
            if candidate.endswith(suffix):
                candidate = candidate[:-len(suffix)]
                affix = affix_id
                break
        if affix:
            break
    bonus = 0
    match = re.search(r"(?: \+|_)([1-3])$", candidate)
    if match:
        bonus = int(match.group(1))
        candidate = candidate[:match.start()]
    normalized = candidate.replace(" ", "_")
    base_id = normalized if normalized in EQUIPMENT else next(
        (spec.id for spec in EQUIPMENT.values() if candidate == spec.name.casefold()), None)
    if base_id is not None:
        try:
            return EquipmentItem(base_id, bonus, affix).id
        except ValueError:
            return None
    return None
