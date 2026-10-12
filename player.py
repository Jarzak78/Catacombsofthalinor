"""Adventurer statistics and class resources, independent of the game UI."""

from dataclasses import dataclass, field
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from loot_library import TreasureItem


ABILITY_NAMES = (
    "strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma",
)
CLASS_PRESETS = {
    "fighter": (16, 14, 14, 10, 12, 10),
    "rogue": (10, 16, 14, 12, 14, 10),
    "wizard": (8, 14, 14, 16, 12, 10),
}


XP_THRESHOLDS: tuple[int, ...] = (
    0, 300, 900, 2700, 6500, 14000, 23000, 34000, 48000, 64000,
    85000, 100000, 120000, 140000, 165000, 195000, 225000, 265000,
    305000, 355000,
)


def ability_modifier(score: int) -> int:
    """Return the 5e modifier associated with an ability score."""
    return (score - 10) // 2


@dataclass
class Player:
    """A warrior, rogue, or wizard and their persistent resources.

    This model tracks resources without enforcing turn order or rest safety;
    those decisions belong to the game. The default constructor preserves
    the original warrior; create() applies class equipment and starting HP.
    """

    name: str = "Adventurer"
    level: int = 1
    xp: int = 0
    gold: int = 0
    potions: int = 3
    max_hp: int = 12
    hp: int = 12
    strength: int = 16
    dexterity: int = 14
    constitution: int = 14
    intelligence: int = 10
    wisdom: int = 12
    charisma: int = 10
    weapon_name: str = "Longsword"
    weapon_bonus: int = 0
    armor_bonus: int = 0
    ward_bonus: int = 0
    vitality_charm: bool = False
    ember_stones: int = 0
    second_wind_uses: int = 2
    action_surge_available: bool = True
    hit_dice_remaining: int = 1
    dead: bool = False
    class_id: str = "fighter"
    mage_armor_active: bool = False
    spell_slots: dict[int, int] = field(default_factory=dict)
    arcane_recovery_available: bool = True
    mana_draughts: int = 0
    treasure_inventory: list["TreasureItem"] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Normalize the class while keeping explicit statistics and HP."""
        self.hp = max(0, self.hp)
        if self.hp == 0:
            self.dead = True
        if not isinstance(self.class_id, str):
            raise ValueError("Choose warrior, rogue, or wizard.")
        self.class_id = self.class_id.strip().lower()
        if self.class_id == "warrior":
            self.class_id = "fighter"
        if self.class_id == "rouge":
            self.class_id = "rogue"
        if self.class_id not in CLASS_PRESETS:
            raise ValueError("Choose warrior, rogue, or wizard.")
        if self.class_id != "fighter":
            self.second_wind_uses = 0
            self.action_surge_available = False
        if self.class_id == "wizard":
            # Copy explicit resource maps so separate characters never share them.
            self.spell_slots = dict(self.spell_slots or self.max_spell_slots)
        else:
            self.spell_slots = {}
            self.arcane_recovery_available = False
            self.mage_armor_active = False

    @classmethod
    def create(cls, name: str = "Adventurer", class_id: str = "fighter",
               stats: dict[str, int] | None = None) -> "Player":
        """Create a level-one adventurer from presets or six rolled scores."""
        player = cls(name=name, class_id=class_id)
        if stats is None:
            scores = dict(zip(ABILITY_NAMES, CLASS_PRESETS[player.class_id]))
        else:
            if not isinstance(stats, dict) or set(stats) != set(ABILITY_NAMES):
                raise ValueError("Starting stats must contain all six ability names.")
            if any(type(score) is not int or not 3 <= score <= 18
                   for score in stats.values()):
                raise ValueError("Starting ability scores must be integers from 3 to 18.")
            scores = dict(stats)
        for ability, score in scores.items():
            setattr(player, ability, score)
        player.max_hp = max(1, player.hit_die_sides + player.constitution_modifier)
        player.hp = player.max_hp
        player.weapon_name = {
            "fighter": "Longsword", "rogue": "Rapier", "wizard": "Quarterstaff",
        }[player.class_id]
        return player

    @property
    def class_name(self) -> str:
        """The class label used in character displays."""
        return {"fighter": "Warrior (Fighter)", "rogue": "Rogue", "wizard": "Wizard"}[self.class_id]

    @property
    def hit_die_sides(self) -> int:
        """The die rolled when this class spends a Hit Die."""
        return {"fighter": 10, "rogue": 8, "wizard": 6}[self.class_id]

    @property
    def fixed_level_hp(self) -> int:
        """The class's fixed HP gain before adding Constitution."""
        return {"fighter": 6, "rogue": 5, "wizard": 4}[self.class_id]

    @property
    def weapon_dice(self) -> tuple[int, int]:
        """Damage dice for the class's one-handed starting weapon."""
        return (1, 6 if self.class_id == "wizard" else 8)

    @property
    def weapon_ability(self) -> str:
        """The ability used for attacks with this class's weapon."""
        return "dexterity" if self.class_id == "rogue" else "strength"

    @property
    def weapon_ability_modifier(self) -> int:
        return ability_modifier(getattr(self, self.weapon_ability))

    @property
    def strength_modifier(self) -> int:
        """Strength's modifier, used for longsword attacks and damage."""
        return ability_modifier(self.strength)

    @property
    def dexterity_modifier(self) -> int:
        """Dexterity's modifier, used for initiative."""
        return ability_modifier(self.dexterity)

    @property
    def constitution_modifier(self) -> int:
        """Constitution's modifier, used for hit points and Hit Dice."""
        return ability_modifier(self.constitution)

    @property
    def intelligence_modifier(self) -> int:
        """Intelligence's ability-check modifier."""
        return ability_modifier(self.intelligence)

    @property
    def wisdom_modifier(self) -> int:
        """Wisdom's ability-check modifier."""
        return ability_modifier(self.wisdom)

    @property
    def charisma_modifier(self) -> int:
        """Charisma's ability-check modifier."""
        return ability_modifier(self.charisma)

    @property
    def proficiency_bonus(self) -> int:
        """The proficiency bonus for the adventurer's current level."""
        return 2 + (self.level - 1) // 4

    @property
    def armor_class(self) -> int:
        """Class armor, Dexterity where applicable, and magical protection."""
        if self.class_id == "fighter":
            base = 18
        elif self.class_id == "rogue":
            base = 12 + self.dexterity_modifier
        else:
            base = (13 if self.mage_armor_active else 10) + self.dexterity_modifier
        return base + self.armor_bonus + self.ward_bonus

    @property
    def attack_bonus(self) -> int:
        """The bonus added to a proficient class-weapon attack roll."""
        return self.weapon_ability_modifier + self.proficiency_bonus + self.weapon_bonus

    @property
    def attack_power(self) -> int:
        """Compatibility alias for the d20 attack bonus."""
        return self.attack_bonus

    @property
    def damage_bonus(self) -> int:
        """Weapon ability, the warrior's Dueling, and magic weapon bonus."""
        dueling = 2 if self.class_id == "fighter" else 0
        return self.weapon_ability_modifier + dueling + self.weapon_bonus

    @property
    def initiative_bonus(self) -> int:
        """The Dexterity bonus added to initiative rolls."""
        return self.dexterity_modifier

    @property
    def perception_bonus(self) -> int:
        """Wisdom, plus the rogue's Perception expertise against ambushes."""
        expertise = 2 * self.proficiency_bonus if self.class_id == "rogue" else 0
        return self.wisdom_modifier + expertise

    @property
    def stealth_bonus(self) -> int:
        """Dexterity and the rogue's expertise for hiding."""
        expertise = 2 * self.proficiency_bonus if self.class_id == "rogue" else 0
        return self.dexterity_modifier + expertise

    @property
    def sneak_attack_dice_count(self) -> int:
        """Extra d6s available to a rogue's qualifying Sneak Attack."""
        return (self.level + 1) // 2 if self.class_id == "rogue" else 0

    @property
    def spell_attack_bonus(self) -> int:
        """Wizard spell accuracy, including a magical staff's focus bonus."""
        return self.intelligence_modifier + self.proficiency_bonus + self.weapon_bonus

    @property
    def spell_save_dc(self) -> int:
        """The DC resisted by enemies targeted by wizard saving-throw spells."""
        return 8 + self.spell_attack_bonus

    @property
    def max_spell_slots(self) -> dict[int, int]:
        """Wizard slots for the campaign's supported spell levels."""
        if self.class_id != "wizard":
            return {}
        if self.level == 1:
            return {1: 2}
        if self.level == 2:
            return {1: 3}
        if self.level == 3:
            return {1: 4, 2: 2}
        if self.level == 4:
            return {1: 4, 2: 3}
        return {1: 4, 2: 3, 3: 2}

    def spend_spell_slot(self, level: int) -> bool:
        """Spend one available wizard slot, without inventing unknown slots."""
        if (self.class_id != "wizard" or not self.is_conscious
                or type(level) is not int or level not in self.max_spell_slots
                or self.spell_slots.get(level, 0) <= 0):
            return False
        self.spell_slots[level] -= 1
        return True

    def recover_arcane_slots(self) -> dict[int, int]:
        """Recover low-level slots once per long rest, returning restored counts.

        The game must first grant a valid short rest. The recovery budget is
        half the wizard level rounded up; lower-level slots are restored first.
        Only first- and second-level slots can be recovered in this campaign.
        """
        if (self.class_id != "wizard" or not self.is_conscious
                or not self.arcane_recovery_available):
            return {}
        budget = (self.level + 1) // 2
        recovered = {}
        for slot_level, maximum in self.max_spell_slots.items():
            if slot_level > 2:
                continue
            missing = maximum - self.spell_slots.get(slot_level, 0)
            count = min(missing, budget // slot_level)
            if count > 0:
                self.spell_slots[slot_level] = self.spell_slots.get(slot_level, 0) + count
                recovered[slot_level] = count
                budget -= count * slot_level
        if recovered:
            self.arcane_recovery_available = False
        return recovered

    def restore_level_one_slot(self) -> bool:
        """Restore one expended first-level wizard slot from a magic item."""
        maximum = self.max_spell_slots.get(1, 0)
        remaining = self.spell_slots.get(1, 0)
        if not self.is_alive or self.class_id != "wizard" or remaining >= maximum:
            return False
        self.spell_slots[1] = remaining + 1
        return True

    @property
    def is_alive(self) -> bool:
        """Whether the player has positive HP and has not died."""
        return not self.dead and self.hp > 0

    @property
    def is_conscious(self) -> bool:
        """Whether the player can take actions."""
        return self.is_alive

    @property
    def xp_to_next_level(self) -> int | None:
        """The cumulative XP threshold for the next level, or None at 20."""
        if self.level >= len(XP_THRESHOLDS):
            return None
        return XP_THRESHOLDS[self.level]

    @property
    def max_second_wind_uses(self) -> int:
        """Maximum uses of Second Wind under the revised fighter rules."""
        if self.class_id != "fighter":
            return 0
        if self.level >= 10:
            return 4
        if self.level >= 4:
            return 3
        return 2

    @property
    def second_wind_available(self) -> bool:
        """Whether at least one use of Second Wind remains."""
        return self.class_id == "fighter" and self.second_wind_uses > 0

    def take_damage(self, amount: int, critical: bool = False) -> int:
        """Apply resolved damage; reaching zero HP ends the adventurer's life.

        The optional critical flag is accepted for attack-call compatibility;
        critical damage has already been calculated by the combat rules.
        """
        if amount < 0:
            raise ValueError("Damage cannot be negative.")
        if self.dead:
            return 0

        previous_hp = max(0, self.hp)
        lost = min(amount, previous_hp)
        self.hp = max(0, previous_hp - amount)
        if self.hp == 0:
            self.dead = True
        return lost

    def heal(self, amount: int) -> int:
        """Restore a living adventurer's HP without reviving the dead."""
        if amount < 0:
            raise ValueError("Healing cannot be negative.")
        if not self.is_alive:
            return 0
        restored = min(amount, self.max_hp - self.hp)
        self.hp += restored
        return restored

    def use_potion(self, rng: random.Random) -> int:
        """Consume a healing potion for 2d4 + 2 HP when useful and alive."""
        if not self.is_alive or self.hp >= self.max_hp or self.potions <= 0:
            return 0
        self.potions -= 1
        return self.heal(rng.randint(1, 4) + rng.randint(1, 4) + 2)

    def second_wind(self, rng: random.Random) -> int:
        """Spend one conscious use of Second Wind to heal 1d10 + level."""
        if not self.is_conscious or not self.second_wind_available:
            return 0
        self.second_wind_uses -= 1
        return self.heal(rng.randint(1, 10) + self.level)

    def spend_hit_die(self, rng: random.Random) -> int:
        """Spend one class Hit Die during a short rest, adding Constitution."""
        if not self.is_conscious or self.hp >= self.max_hp or self.hit_dice_remaining <= 0:
            return 0
        self.hit_dice_remaining -= 1
        return self.heal(max(0, rng.randint(1, self.hit_die_sides) + self.constitution_modifier))

    def refresh_short_rest(self) -> None:
        """Recover one Second Wind use and Action Surge after a valid rest."""
        if not self.is_alive:
            return
        self.second_wind_uses = min(self.max_second_wind_uses, self.second_wind_uses + 1)
        self.action_surge_available = self.class_id == "fighter"

    def long_rest(self) -> None:
        """Recover all resources after a valid rest begun with positive HP."""
        if not self.is_conscious:
            return
        self.hp = self.max_hp
        self.second_wind_uses = self.max_second_wind_uses
        self.action_surge_available = self.class_id == "fighter"
        self.hit_dice_remaining = self.level
        self.spell_slots = self.max_spell_slots
        self.arcane_recovery_available = self.class_id == "wizard"
        self.mage_armor_active = False

    def gain_xp(self, amount: int) -> int:
        """Add cumulative XP and return the number of levels advanced.

        Each class level adds its fixed HP gain + Constitution modifier and
        one Hit Die. Conscious players gain the HP increase as current HP;
        advancing a level does not otherwise recover spent resources.
        """
        if amount < 0:
            raise ValueError("Experience cannot be negative.")
        self.xp += amount
        levels_gained = 0
        while self.xp_to_next_level is not None and self.xp >= self.xp_to_next_level:
            hp_increase = max(1, self.fixed_level_hp + self.constitution_modifier)
            if self.is_conscious:
                self.hp += hp_increase
            self.max_hp += hp_increase
            old_slots = self.max_spell_slots
            self.level += 1
            for slot_level, maximum in self.max_spell_slots.items():
                newly_gained = maximum - old_slots.get(slot_level, 0)
                self.spell_slots[slot_level] = self.spell_slots.get(slot_level, 0) + newly_gained
            self.hit_dice_remaining += 1
            levels_gained += 1
        return levels_gained

    def equip_weapon(self, name: str, bonus: int) -> bool:
        """Equip a compatible class weapon only when its magic bonus improves."""
        if bonus <= self.weapon_bonus:
            return False
        self.weapon_name = name
        self.weapon_bonus = bonus
        return True

