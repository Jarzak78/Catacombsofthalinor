"""A fighter's statistics and resources using the revised 2024 5e rules."""

from dataclasses import dataclass
import random


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
    """A novice fighter with a longsword, chain mail, shield, and Dueling.

    This model tracks resources without enforcing turn order or rest safety;
    those decisions belong to the game. Later-level character choices such
    as feats and subclasses are outside this introductory character model.
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
    second_wind_uses: int = 2
    action_surge_available: bool = True
    hit_dice_remaining: int = 1
    death_save_successes: int = 0
    death_save_failures: int = 0
    stable: bool = False
    dead: bool = False

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
        """The proficiency bonus for the fighter's current level."""
        return 2 + (self.level - 1) // 4

    @property
    def armor_class(self) -> int:
        """Chain mail's AC 16 plus the shield's +2 bonus."""
        return 18

    @property
    def attack_bonus(self) -> int:
        """The bonus added to a proficient longsword attack roll."""
        return self.strength_modifier + self.proficiency_bonus + self.weapon_bonus

    @property
    def attack_power(self) -> int:
        """Compatibility alias for the d20 attack bonus."""
        return self.attack_bonus

    @property
    def damage_bonus(self) -> int:
        """Strength, Dueling, and the magic weapon's damage bonus."""
        return self.strength_modifier + 2 + self.weapon_bonus

    @property
    def initiative_bonus(self) -> int:
        """The Dexterity bonus added to initiative rolls."""
        return self.dexterity_modifier

    @property
    def is_alive(self) -> bool:
        """Whether the player is alive, including at zero hit points."""
        return not self.dead

    @property
    def is_conscious(self) -> bool:
        """Whether the player can take actions."""
        return self.hp > 0 and not self.dead

    @property
    def xp_to_next_level(self) -> int | None:
        """The cumulative XP threshold for the next level, or None at 20."""
        if self.level >= len(XP_THRESHOLDS):
            return None
        return XP_THRESHOLDS[self.level]

    @property
    def max_second_wind_uses(self) -> int:
        """Maximum uses of Second Wind under the revised fighter rules."""
        if self.level >= 10:
            return 4
        if self.level >= 4:
            return 3
        return 2

    @property
    def second_wind_available(self) -> bool:
        """Whether at least one use of Second Wind remains."""
        return self.second_wind_uses > 0

    def take_damage(self, amount: int, critical: bool = False) -> int:
        """Apply resolved damage and return the hit points actually lost.

        Excess damage at least equal to maximum HP causes instant death.
        Damage while already at zero HP causes one failed death save, or
        two when the damaging attack is a critical hit.
        """
        if amount < 0:
            raise ValueError("Damage cannot be negative.")
        if self.dead or amount == 0:
            return 0

        previous_hp = self.hp
        lost = min(amount, previous_hp)
        self.hp = max(0, previous_hp - amount)
        if self.hp > 0:
            return lost

        self.stable = False
        if amount - previous_hp >= self.max_hp:
            self.dead = True
        elif previous_hp == 0:
            self.death_save_failures += 2 if critical else 1
            if self.death_save_failures >= 3:
                self.dead = True
        return lost

    def heal(self, amount: int) -> int:
        """Restore HP, including unconsciousness, but never revive the dead."""
        if amount < 0:
            raise ValueError("Healing cannot be negative.")
        if self.dead:
            return 0
        restored = min(amount, self.max_hp - self.hp)
        self.hp += restored
        if restored > 0:
            self.death_save_successes = 0
            self.death_save_failures = 0
            self.stable = False
        return restored

    def use_potion(self, rng: random.Random) -> int:
        """Consume a healing potion for 2d4 + 2 HP when useful.

        The caller decides whether the potion is drunk or administered.
        """
        if self.dead or self.hp >= self.max_hp or self.potions <= 0:
            return 0
        self.potions -= 1
        return self.heal(rng.randint(1, 4) + rng.randint(1, 4) + 2)

    def second_wind(self, rng: random.Random) -> int:
        """Spend one conscious use of Second Wind to heal 1d10 + level."""
        if not self.is_conscious or self.second_wind_uses <= 0:
            return 0
        self.second_wind_uses -= 1
        return self.heal(rng.randint(1, 10) + self.level)

    def spend_hit_die(self, rng: random.Random) -> int:
        """Spend one Hit Die during a short rest to heal 1d10 + Constitution."""
        if not self.is_conscious or self.hp >= self.max_hp or self.hit_dice_remaining <= 0:
            return 0
        self.hit_dice_remaining -= 1
        return self.heal(max(0, rng.randint(1, 10) + self.constitution_modifier))

    def refresh_short_rest(self) -> None:
        """Recover one Second Wind use and Action Surge after a valid rest."""
        if self.dead:
            return
        self.second_wind_uses = min(self.max_second_wind_uses, self.second_wind_uses + 1)
        self.action_surge_available = True

    def long_rest(self) -> None:
        """Recover all resources after a valid rest begun with positive HP."""
        if not self.is_conscious:
            return
        self.hp = self.max_hp
        self.death_save_successes = 0
        self.death_save_failures = 0
        self.stable = False
        self.second_wind_uses = self.max_second_wind_uses
        self.action_surge_available = True
        self.hit_dice_remaining = self.level

    def gain_xp(self, amount: int) -> int:
        """Add cumulative XP and return the number of levels advanced.

        Each fighter level adds the fixed 6 + Constitution modifier HP and
        one Hit Die. Conscious players gain the HP increase as current HP;
        advancing a level does not otherwise recover spent resources.
        """
        if amount < 0:
            raise ValueError("Experience cannot be negative.")
        self.xp += amount
        levels_gained = 0
        while self.xp_to_next_level is not None and self.xp >= self.xp_to_next_level:
            hp_increase = max(1, 6 + self.constitution_modifier)
            if self.is_conscious:
                self.hp += hp_increase
            self.max_hp += hp_increase
            self.level += 1
            self.hit_dice_remaining += 1
            levels_gained += 1
        return levels_gained

    def equip_weapon(self, name: str, bonus: int) -> bool:
        """Equip a longsword only when its magic bonus improves the current one."""
        if bonus <= self.weapon_bonus:
            return False
        self.weapon_name = name
        self.weapon_bonus = bonus
        return True

    def death_save(self, rng: random.Random) -> str:
        """Resolve one death save for an unstable player at zero HP.

        Return natural20, success, failure, stable, or dead. No roll is
        made for conscious, already stable, or dead players; those states
        return conscious, stable, or dead respectively.
        """
        if self.dead:
            return "dead"
        if self.is_conscious:
            return "conscious"
        if self.stable:
            return "stable"

        roll = rng.randint(1, 20)
        if roll == 20:
            self.heal(1)
            return "natural20"
        if roll >= 10:
            self.death_save_successes += 1
            if self.death_save_successes >= 3:
                self.stable = True
                self.death_save_successes = 0
                self.death_save_failures = 0
                return "stable"
            return "success"

        self.death_save_failures += 2 if roll == 1 else 1
        if self.death_save_failures >= 3:
            self.dead = True
            return "dead"
        return "failure"
