"""Solo dungeon exploration with revised 2024 5e martial combat."""

import random

from combat import AttackResult, roll_attack, roll_initiative
from dungeon import Dungeon
from player import Player
from room import Enemy, Room
from utils import health_bar


HELP = """Explore: north/south/east/west (n/s/e/w), look, map, loot
Actions: attack (a), dodge (d), disengage (flee/f)
Bonus actions: potion (p), second wind (wind)
Turn control: end, action surge (surge; fighter level 2)
Rest: rest [dice] (1 hour), long rest (8 hours; entrance only)
Other: stats, inventory (i), help (h), quit (q)

Attacks: d20 + attack bonus vs Armor Class. Natural 1 misses; 20 crits.
Critical hits double weapon dice, not modifiers. Longsword hits apply Sap.
Dodge gives attacks against you Disadvantage until your next turn.
Disengage spends an action and retreats without an opportunity attack.
Potions heal 2d4+2; Second Wind heals 1d10 + fighter level.
Each combat turn has an action and a bonus action. Type 'end' when done.
Informational and invalid commands do not spend actions or advance combat.
Short rests recover one Second Wind use and Action Surge; an injured
fighter can spend Hit Dice to heal. 'rest 0' saves your dice; 'rest 1' caps
spending at one die. Plain 'rest' spends dice until healed or out of dice.
Long rests restore HP and all resources.
At 0 HP you are unconscious: 'end' lets combat and death saves continue.
Collect treasure with 'loot'. Defeat the Warden to clear your first dungeon."""

ALIASES = {
    "n": "north", "s": "south", "e": "east", "w": "west",
    "a": "attack", "d": "dodge", "defend": "dodge",
    "p": "potion", "f": "disengage", "flee": "disengage",
    "wind": "second wind", "surge": "action surge", "save": "end",
    "i": "inventory", "h": "help", "?": "help", "q": "quit",
    "short rest": "rest",
}
DIRECTIONS = {"north", "south", "east", "west"}


class Game:
    """One adventure; commands return text and never read terminal input."""

    def __init__(self, name: str = "Adventurer", seed: int | None = None):
        self.rng = random.Random(seed)
        self.dungeon = Dungeon(self.rng)
        self.player = Player(name=name)
        self.position = self.dungeon.start
        self.previous_position: tuple[int, int] | None = None
        self.room.visited = True
        self.actions_remaining = 1
        self.bonus_action_available = True
        self.dodging = False
        self.enemy_sapped = False
        self.round_number = 0
        self.elapsed_minutes = 0.0
        self.last_long_rest_end = -960.0
        self.won = False
        self.quit_requested = False

    @property
    def room(self) -> Room:
        return self.dungeon.get_room(self.position)

    @property
    def enemy(self) -> Enemy | None:
        enemy = self.room.enemy
        return enemy if enemy is not None and enemy.is_alive else None

    @property
    def over(self) -> bool:
        return self.won or self.quit_requested or self.player.dead

    def introduction(self) -> list[str]:
        return [
            "CATACOMBS OF THALINOR",
            "Your guild badge is still bright, and your sword has yet to face a monster.",
            f"Today, {self.player.name}, you enter your very first dungeon.",
            "You are a first-level fighter with a longsword, shield, and chain mail.",
            "Defeat the Warden and return as a proven adventurer.",
            "Explore, gather supplies, and grow stronger before challenging him.",
            "Type 'help' for commands. Your starting pack holds three healing potions.",
            "Combat uses revised 2024 5e rules; type 'end' to finish your turn.",
            "", *self.describe_room(),
        ]

    def describe_room(self) -> list[str]:
        lines = [self.room.name, self.room.description]
        enemy = self.enemy
        if enemy:
            lines.append(f"{enemy.name} blocks your way! HP {enemy.hp}/{enemy.max_hp}, "
                         f"AC {enemy.armor_class}.")
            lines.append("Attack, dodge, use a bonus action, or disengage; 'end' finishes your turn.")
        elif self.room.enemy:
            lines.append(f"The defeated {self.room.enemy.name} lies still.")
        if self.room.loot and not self.room.looted:
            lines.append("You spot unclaimed treasure. Use 'loot' when the room is safe.")
        lines.append("Exits: " + ", ".join(self.room.exits))
        return lines

    def status(self) -> list[str]:
        player = self.player
        target = player.xp_to_next_level
        xp = f"{player.xp}/{target}" if target is not None else f"{player.xp} (maximum level)"
        lines = [
            f"{player.name} | Fighter {player.level} | HP {player.hp}/{player.max_hp} "
            f"{health_bar(player.hp, player.max_hp)}",
            f"AC {player.armor_class} | Attack +{player.attack_bonus} | "
            f"Damage 1d8+{player.damage_bonus} | XP {xp} | Gold {player.gold}",
            f"Second Wind {player.second_wind_uses}/{player.max_second_wind_uses} | "
            f"Hit Dice {player.hit_dice_remaining}/{player.level}",
        ]
        if player.level >= 2:
            lines.append("Action Surge: " + ("ready" if player.action_surge_available else "spent"))
        if not player.is_conscious and not player.dead:
            lines.append(f"Unconscious | Death saves: {player.death_save_successes} successes, "
                         f"{player.death_save_failures} failures | Stable: {player.stable}")
        elif self.enemy:
            lines.append(self.turn_status())
        return lines

    def turn_status(self) -> str:
        bonus = "ready" if self.bonus_action_available else "spent"
        return f"Round {self.round_number} | Actions left: {self.actions_remaining} | Bonus action: {bonus}"

    def handle_command(self, raw: str) -> list[str]:
        """Execute one command without spending turns on invalid input."""
        if self.over:
            return ["This adventure is over. Run Main.py to begin another."]
        command = " ".join(raw.lower().split())
        if command.startswith(("go ", "move ")):
            command = command.split(" ", 1)[1]
        command = ALIASES.get(command, command)
        if command == "help":
            return HELP.splitlines()
        if command == "look":
            return self.describe_room()
        if command == "map":
            return [*self.dungeon.map_lines(self.position),
                    "@ you | ? unexplored | . explored | E enemy | B Warden | $ treasure"]
        if command == "stats":
            return self.status()
        if command == "inventory":
            return [f"Weapon: {self.player.weapon_name} (magic bonus +{self.player.weapon_bonus})",
                    "Armor: chain mail and shield | Fighting style: Dueling | Mastery: Sap",
                    f"Healing potions: {self.player.potions} | Gold: {self.player.gold}"]
        if command == "quit":
            self.quit_requested = True
            return ["You leave the trial for another day. Your first dungeon can wait."]
        if not self.player.is_conscious:
            if command == "end":
                return self.end_turn()
            return ["You are unconscious and cannot act. Type 'end' to continue combat."]
        if command in DIRECTIONS:
            return self.move(command)
        if command.startswith("rest "):
            try:
                limit = int(command.split(" ", 1)[1])
            except ValueError:
                return ["Use 'rest', 'rest 0', or 'rest' followed by a number of Hit Dice."]
            if limit < 0:
                return ["The number of Hit Dice cannot be negative."]
            return self.short_rest(dice_limit=limit)
        handlers = {
            "loot": self.collect_loot, "attack": self.attack,
            "dodge": self.dodge, "disengage": self.disengage,
            "potion": self.drink_potion, "second wind": self.second_wind,
            "action surge": self.action_surge, "end": self.end_turn,
            "rest": self.short_rest, "long rest": self.long_rest,
        }
        if command in handlers:
            return handlers[command]()
        return ["Unknown command. Type 'help' to see your options."]

    def move(self, direction: str) -> list[str]:
        if self.enemy:
            return ["An enemy blocks your way. Use Disengage ('flee') to retreat safely."]
        target = self.room.exits.get(direction)
        if target is None:
            return ["There is no passage in that direction."]
        self.previous_position = self.position
        self.position = target
        self.room.visited = True
        self.elapsed_minutes += 1
        lines = self.describe_room()
        if self.enemy:
            lines.extend(self.begin_encounter())
        return lines

    def begin_encounter(self) -> list[str]:
        enemy = self.enemy
        if enemy is None:
            return []
        hero_roll = roll_initiative(self.rng, self.player.initiative_bonus)
        enemy_roll = roll_initiative(self.rng, enemy.initiative_bonus)
        self.round_number = 0
        self.dodging = False
        self.enemy_sapped = False
        lines = [f"Initiative: you {hero_roll}, {enemy.name} {enemy_roll}. "
                 "Ties go to the adventurer."]
        if enemy_roll > hero_roll:
            lines.extend(self.enemy_turn())
        return [*lines, *self.begin_turn()]

    def begin_turn(self) -> list[str]:
        self.round_number += 1
        self.actions_remaining = 1
        self.bonus_action_available = True
        self.dodging = False
        self.enemy_sapped = False
        if self.player.dead:
            return []
        if not self.player.is_conscious:
            if self.player.stable:
                return ["You are stable but unconscious. The enemy is still dangerous; type 'end'."]
            outcome = self.player.death_save(self.rng)
            if outcome == "natural20":
                return ["Death save: natural 20! You recover 1 HP and rise, spending half your movement.",
                        self.turn_status()]
            if outcome == "dead":
                return self.death_message()
            return [f"Death save: {outcome}. Successes {self.player.death_save_successes}, "
                    f"failures {self.player.death_save_failures}. Type 'end' to continue."]
        return [self.turn_status()]

    def attack(self) -> list[str]:
        enemy = self.enemy
        if enemy is None:
            return ["There is no enemy here to attack."]
        if self.actions_remaining <= 0:
            return ["Your action is spent. Use a bonus action, Action Surge, or 'end'."]
        self.actions_remaining -= 1
        result = roll_attack(self.rng, self.player.attack_bonus, enemy.armor_class,
                             (1, 8), self.player.damage_bonus)
        lines = [self.attack_text("You", enemy.name, result)]
        if result.hit:
            enemy.take_damage(result.damage)
            self.enemy_sapped = True
            lines.append("Sap: the enemy's next attack has Disadvantage before your next turn.")
        if not enemy.is_alive:
            lines.extend(self.defeat_enemy(enemy))
        else:
            lines.extend([f"{enemy.name}: {enemy.hp}/{enemy.max_hp} HP.", self.turn_status(),
                          "Type 'end' when your turn is finished."])
        return lines

    @staticmethod
    def attack_text(attacker: str, defender: str, result: AttackResult) -> str:
        dice = "/".join(str(value) for value in result.rolls)
        roll = f"d20 [{dice}], total {result.total}"
        if not result.hit:
            verb = "miss" if attacker == "You" else "misses"
            return f"{attacker} {verb} {defender} ({roll})."
        critical = " Critical hit!" if result.critical else ""
        verb = "hit" if attacker == "You" else "hits"
        return f"{attacker} {verb} {defender} ({roll}) for {result.damage} damage.{critical}"

    def defeat_enemy(self, enemy: Enemy) -> list[str]:
        self.player.gold += enemy.gold_reward
        levels = self.player.gain_xp(enemy.xp_reward)
        self.dodging = False
        self.enemy_sapped = False
        lines = [f"You defeat {enemy.name}! +{enemy.xp_reward} XP, +{enemy.gold_reward} gold."]
        if levels:
            lines.append(f"You reach fighter level {self.player.level}! Maximum HP increases; "
                         "leveling does not fully heal you.")
            if self.player.level >= 2:
                lines.append("Action Surge is unlocked: one extra action, once per short or long rest.")
        if enemy.boss:
            self.won = True
            lines.extend([
                "The Warden falls, and the sealed catacombs grow quiet.",
                "You take his bronze seal as proof of your victory.",
                f"Congratulations, {self.player.name}! Your first dungeon is conquered.",
                *self.status(),
            ])
        return lines

    def enemy_turn(self) -> list[str]:
        enemy = self.enemy
        if enemy is None or self.player.dead:
            return []
        unconscious = not self.player.is_conscious
        result = roll_attack(
            self.rng, enemy.attack_bonus, self.player.armor_class,
            enemy.damage_dice, enemy.damage_bonus,
            advantage=unconscious,
            disadvantage=self.enemy_sapped or (self.dodging and not unconscious),
            critical_on_hit=unconscious,
        )
        self.enemy_sapped = False
        lines = [self.attack_text(enemy.name, "you", result)]
        if result.hit:
            self.player.take_damage(result.damage, critical=result.critical)
        lines.append(f"Your HP: {self.player.hp}/{self.player.max_hp}.")
        if self.player.dead:
            lines.extend(self.death_message())
        elif not self.player.is_conscious:
            lines.append("You are unconscious at 0 HP. Close-range hits can cause two failed death saves.")
        return lines

    @staticmethod
    def death_message() -> list[str]:
        return ["You die in the catacombs. Your first trial ends here.",
                "Run Main.py again to try a new adventure."]

    def end_turn(self) -> list[str]:
        if self.enemy is None:
            return ["There is no combat turn to end. Explore or rest."]
        self.elapsed_minutes += 0.1
        lines = self.enemy_turn()
        if not self.player.dead:
            lines.extend(self.begin_turn())
        return lines

    def dodge(self) -> list[str]:
        if not self.enemy:
            return ["There is no enemy to dodge."]
        if self.actions_remaining <= 0:
            return ["Your action is already spent."]
        self.actions_remaining -= 1
        self.dodging = True
        return ["You Dodge. Visible enemy attacks have Disadvantage until your next turn.",
                self.turn_status()]

    def disengage(self) -> list[str]:
        if not self.enemy:
            return ["There is no enemy to disengage from."]
        if self.previous_position is None:
            return ["There is nowhere to retreat."]
        if self.actions_remaining <= 0:
            return ["Disengage needs an action. Use Action Surge or wait until your next turn."]
        self.actions_remaining -= 1
        old_position = self.position
        self.position = self.previous_position
        self.previous_position = old_position
        self.dodging = False
        self.enemy_sapped = False
        return ["You take the Disengage action and retreat. No opportunity attack is made.",
                *self.describe_room()]

    def bonus_action_error(self) -> list[str]:
        if self.enemy and not self.bonus_action_available:
            return ["You have already used your bonus action this turn."]
        return []

    def drink_potion(self) -> list[str]:
        error = self.bonus_action_error()
        if error:
            return error
        if self.player.potions <= 0:
            return ["You have no healing potions left."]
        if self.player.hp == self.player.max_hp:
            return ["You are already at full health; you keep the potion."]
        healed = self.player.use_potion(self.rng)
        if self.enemy:
            self.bonus_action_available = False
        return [f"You drink a potion (2d4+2) and restore {healed} HP. "
                f"Potions left: {self.player.potions}."]

    def second_wind(self) -> list[str]:
        error = self.bonus_action_error()
        if error:
            return error
        if self.player.second_wind_uses <= 0:
            return ["Second Wind is spent. A short rest restores one use."]
        if self.player.hp == self.player.max_hp:
            return ["You are already at full health; you keep your Second Wind use."]
        healed = self.player.second_wind(self.rng)
        if self.enemy:
            self.bonus_action_available = False
        return [f"Second Wind restores {healed} HP (1d10 + fighter level). "
                f"Uses left: {self.player.second_wind_uses}."]

    def action_surge(self) -> list[str]:
        if not self.enemy:
            return ["Save Action Surge for combat."]
        if self.player.level < 2:
            return ["Action Surge unlocks at fighter level 2 (300 total XP)."]
        if not self.player.action_surge_available:
            return ["Action Surge is spent until a short or long rest."]
        self.player.action_surge_available = False
        self.actions_remaining += 1
        return ["Action Surge! You gain one additional action this turn.", self.turn_status()]

    def short_rest(self, dice_limit: int | None = None) -> list[str]:
        if self.enemy:
            return ["You cannot rest while an enemy threatens you."]
        self.elapsed_minutes += 60
        healed = 0
        spent = 0
        limit = self.player.hit_dice_remaining if dice_limit is None else dice_limit
        while (self.player.hp < self.player.max_hp and self.player.hit_dice_remaining > 0
               and spent < limit):
            healed += self.player.spend_hit_die(self.rng)
            spent += 1
        self.player.refresh_short_rest()
        return [f"You take a one-hour short rest. Spent {spent} Hit Dice, healing {healed} HP.",
                "You recover one Second Wind use and refresh Action Surge.", *self.status()]

    def long_rest(self) -> list[str]:
        if self.enemy or self.position != self.dungeon.start:
            return ["An eight-hour long rest is only safe at the entrance, away from enemies."]
        if self.elapsed_minutes - self.last_long_rest_end < 960:
            return ["Wait at least 16 hours after your last long rest before starting another."]
        self.elapsed_minutes += 480
        self.last_long_rest_end = self.elapsed_minutes
        self.player.long_rest()
        return ["You spend eight hours resting at the entrance. "
                "HP, Hit Dice, Second Wind, and Action Surge are restored.", *self.status()]

    def collect_loot(self) -> list[str]:
        if self.enemy:
            return ["Defeat the enemy before searching for treasure."]
        loot = self.room.loot
        if loot is None or self.room.looted:
            return ["There is no unclaimed treasure here."]
        self.room.looted = True
        self.player.gold += loot.gold
        self.player.potions += loot.potions
        lines = [f"You collect {loot.gold} gold and {loot.potions} healing potion(s)."]
        if loot.weapon_name and self.player.equip_weapon(loot.weapon_name, loot.weapon_bonus):
            lines.append(f"You equip {loot.weapon_name} (+{loot.weapon_bonus} to attack and damage).")
        return lines
