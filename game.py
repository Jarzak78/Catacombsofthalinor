"""Solo dungeon exploration and D&D-inspired class combat."""

from dataclasses import asdict, replace
from actions import Action
from battle_flavor import hit_description, miss_description
from campaign import FLOORS, stock
from lore_notes import LoreNote
from loot_flavor import (
    discovery_description, loot_clue_description, preview_description,
    weapon_discovery_description,
)
import random

from combat import AttackResult, roll_attack, roll_initiative, roll_dice
from dungeon import Dungeon
from enemy_lore import foe_details
from player import Player
from room import Enemy, Room
from utils import health_bar


HELP = """Explore: north/south/east/west (n/s/e/w), look, map, loot
Foes: examine (free opening opportunity, otherwise one action; rereading is free)
Lore: journal, read (latest note), read <journal number or note id>
Actions: attack (a), dodge (d), disengage (flee/f)
Bonus actions: potion (p), second wind (wind)
Turn control: end, action surge (surge; fighter level 2)
Rest: rest [dice] (1 hour), long rest (8 hours; entrance only)
Portal: portal (after guardian), shop, buy <item id>, sell <item id>/sell all, descend
Classes: skills, hide (Rogue), cast <spell> (Wizard), strike (weapon attack)
Magic items: ember (action, 3d6 damage), mana (bonus action, restores one level-1 slot)
Other: stats, inventory (i), help (h), quit (q)

Attacks: d20 + attack bonus vs Armor Class. Natural 1 critically fails for 1 self-damage; 20 crits.
A miss within 1–2 points of AC gets near-miss narration but deals no damage.
Hit descriptions reflect damage: glancing 1–5, solid 6–10, heavy 11–15, devastating 16+.
Critical hits double damage dice, not modifiers. Warrior longsword hits apply Sap.
Dodge gives attacks against you Disadvantage until your next turn.
Disengage retreats without an opportunity attack; Rogues use a bonus action from level 2.
Potions heal 2d4+2; Second Wind heals 1d10 + fighter level.
Each combat turn has an action and a bonus action. Type 'end' when done.
Other informational and invalid commands do not spend actions or advance combat.
Winning initiative (including ties) lets you examine before your first action for free.
If the monster acts first, roll a Perception save vs DC 12 (Rogues add expertise).
Failure gives its opening attack Advantage; success means a normal attack.
This ambush save is a house rule; it never skips your turn or causes fumble damage.
Short rests recover Warrior Second Wind and Action Surge, or once-per-long-rest
Wizard Arcane Recovery. Any class can spend Hit Dice to heal. 'rest 0' saves your dice; 'rest 1' caps
spending at one die. Plain 'rest' spends dice until healed or out of dice.
Long rests restore HP and all resources.
At 0 HP you die immediately and the adventure ends. Healing and rests cannot revive you.
Hostile rooms show combat only. After victory, use 'look' to examine the room.
In a safe room, 'look' hints at loot; 'loot' reveals exact items and collects them.
Collect treasure with 'loot'. Defeat each guardian, then use 'portal' to shop."""

ALIASES = {
    "n": "north", "s": "south", "e": "east", "w": "west",
    "a": "attack", "d": "dodge", "defend": "dodge",
    "p": "potion", "f": "disengage", "flee": "disengage",
    "wind": "second wind", "surge": "action surge", "save": "end",
    "i": "inventory", "h": "help", "?": "help", "q": "quit",
    "short rest": "rest",
    "inspect": "examine", "examine foe": "examine", "examine enemy": "examine",
}
DIRECTIONS = {"north", "south", "east", "west"}


class Game:
    """One adventure; commands return text and never read terminal input."""

    def __init__(self, name: str = "Adventurer", seed: int | None = None, floors: int = 5,
                 *, player: Player | None = None, class_id: str = "fighter",
                 stats: dict[str, int] | None = None):
        if not 1 <= floors <= len(FLOORS):
            raise ValueError("Choose between 1 and 5 floors.")
        self.total_floors = floors
        self.floor = 1
        self.in_shop = False
        self.floor_cleared = False
        self.rng = random.Random(seed)
        self.player = player if player is not None else Player.create(name, class_id, stats)
        self.dungeon = Dungeon(self.rng, class_id=self.player.class_id)
        self.journal: list[LoreNote] = []
        self.position = self.dungeon.start
        self.previous_position: tuple[int, int] | None = None
        self.room.visited = True
        self.actions_remaining = 1
        self.bonus_action_available = True
        self.dodging = False
        self.enemy_sapped = False
        self.round_number = 0
        self.clear_encounter()
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
        return self.won or self.quit_requested or not self.player.is_alive

    def introduction(self) -> list[str]:
        return [
            "CATACOMBS OF THALINOR",
            "Your guild badge is still bright; your first trial awaits below.",
            f"Today, {self.player.name}, you enter your very first dungeon.",
            f"You are a first-level {self.player.class_name} carrying {self.player.weapon_name}.",
            f"Conquer {self.total_floors} dungeon floors; portals lead to a vendor between floors.",
            "Explore, gather supplies, and grow stronger before challenging him.",
            "Type 'help' for commands. Your starting pack holds three healing potions.",
            "Search with 'loot' for notes as well as treasure. Use 'journal' and 'read 1' to read them.",
            "Combat uses D&D-inspired rules; 'skills' explains your class. Type 'end' to finish your turn.",
            "", self.dungeon.lore.arrival, "", *self.describe_room(),
        ]

    def describe_room(self) -> list[str]:
        if self.in_shop:
            return ["The Lantern Between Worlds", "A portal brings you to Mira, the enchanted outfitter.",
                    "Use 'shop', 'buy <item id>', and 'descend' when ready.",
                    "Your journal is here too: use 'journal' and 'read <number>'."]
        if self.enemy:
            return [self.foe_summary(), self.combat_options()]
        lines = [f"Floor {self.floor}/{self.total_floors}: {self.dungeon.theme.name}",
                 self.room.name, self.room.description]
        if self.floor_cleared and self.position == self.dungeon.boss_position:
            lines.append("A glowing portal is open. Type 'portal' to visit the vendor.")
        if self.room.enemy:
            lines.append(f"The defeated {self.room.enemy.name} lies still.")
        loot = self.room.loot
        has_treasure = loot is not None and not self.room.looted and loot.has_treasure
        has_note = self.room.note is not None and not self.room.note_collected
        if has_treasure or has_note:
            lines.append(preview_description(self.room, self.floor))
        if has_treasure:
            lines.append(loot_clue_description(self.room))
        if has_note:
            lines.append(f"You spot a document: {self.room.note.title}. Use 'loot' to collect it once the room is safe.")
        lines.append("Exits: " + ", ".join(self.room.exits))
        return lines

    def foe_summary(self) -> str:
        enemy = self.enemy
        return f"{enemy.name} blocks your way! HP {enemy.hp}/{enemy.max_hp}, AC {enemy.armor_class}."

    def combat_options(self) -> str:
        if not self.player.is_alive:
            return "You are dead. Start a new adventure to try again."
        if self.foe_examined:
            cost = "reread free"
        elif self.free_examine_available:
            cost = "free before your first action"
        elif self.initiative_result is None:
            cost = "initiative decides the opening cost"
        else:
            cost = "1 action"
        abilities = {"fighter": "wind", "rogue": "hide", "wizard": "cast <spell>"}
        return (f"Combat: attack, dodge, potion, {abilities[self.player.class_id]}, flee, end; "
                f"examine ({cost}). 'skills' lists abilities.")

    def status(self) -> list[str]:
        player = self.player
        target = player.xp_to_next_level
        xp = f"{player.xp}/{target}" if target is not None else f"{player.xp} (maximum level)"
        lines = [
            f"Floor {self.floor}/{self.total_floors} | {player.name} | {player.class_name} {player.level} | HP {player.hp}/{player.max_hp} "
            f"{health_bar(player.hp, player.max_hp)}",
            f"AC {player.armor_class + (5 if self.shield_active else 0)} | Weapon attack {player.attack_bonus:+d} | "
            f"Weapon damage {player.weapon_dice[0]}d{player.weapon_dice[1]}{player.damage_bonus:+d} | XP {xp} | Gold {player.gold}",
            f"STR {player.strength} | DEX {player.dexterity} | INT {player.intelligence} | "
            f"CON {player.constitution} | WIS {player.wisdom} | CHA {player.charisma}",
            f"Hit Dice {player.hit_dice_remaining}/{player.level} (d{player.hit_die_sides}) | "
            f"Perception save {player.perception_bonus:+d} | Ambush DC 12",
        ]
        if player.class_id == "fighter":
            lines.append(f"Second Wind {player.second_wind_uses}/{player.max_second_wind_uses}")
        if player.class_id == "fighter" and player.level >= 2:
            lines.append("Action Surge: " + ("ready" if player.action_surge_available else "spent"))
        if player.class_id == "wizard":
            lines.append(f"Spell attack {player.spell_attack_bonus:+d} | Spell save DC {player.spell_save_dc} | "
                         + "Slots: " + ", ".join(f"level {level}: {player.spell_slots.get(level, 0)}/{count}"
                                                   for level, count in player.max_spell_slots.items()))
        if player.class_id == "rogue":
            lines.append(f"Stealth {player.stealth_bonus:+d} | Sneak Attack {player.sneak_attack_dice_count}d6 once per turn")
        if not player.is_alive:
            lines.append("Dead | Your adventure has ended.")
        elif self.enemy:
            lines.append(self.turn_status())
        return lines

    def turn_status(self) -> str:
        bonus = "ready" if self.bonus_action_available else "spent"
        return f"Round {self.round_number} | Actions left: {self.actions_remaining} | Bonus action: {bonus}"

    def handle_command(self, raw: str) -> list[str]:
        """Execute one command without spending turns on invalid input."""
        command = " ".join(raw.lower().split())
        if command.startswith(("go ", "move ")):
            command = command.split(" ", 1)[1]
        command = ALIASES.get(command, command)
        if command.startswith(("buy ", "rest ", "read ", "cast ", "sell ")):
            kind, argument = command.split(" ", 1)
            return self.perform(Action(kind, argument))
        return self.perform(Action(command))

    def perform(self, action: Action) -> list[str]:
        """Execute a device-independent action; GUIs call this directly."""
        # Journal inspection is informational in every scene, even after victory.
        if action.kind == "journal" and not action.argument:
            return self.journal_lines()
        if action.kind == "read":
            return self.read_note(action.argument)
        if self.over:
            return ["This adventure is over. Start a new adventure to try again."]
        command = action.kind
        if action.argument:
            command += " " + action.argument
        if command == "help":
            return HELP.splitlines()
        if command == "look":
            return self.describe_room()
        if command == "map":
            if self.in_shop:
                return ["You are in the vendor sanctuary, outside the dungeon."]
            return [*self.dungeon.map_lines(self.position),
                    "@ you | ? unexplored | . explored | E enemy | B guardian | $ treasure | N note"]
        if command == "stats":
            return self.status()
        if command == "skills":
            return self.skills()
        if command == "inventory":
            return [f"Weapon: {self.player.weapon_name} (magic bonus +{self.player.weapon_bonus})",
                    f"Armor: runic bonus +{self.player.armor_bonus} | Warding ring +{self.player.ward_bonus}",
                    f"Vitality charm: {self.player.vitality_charm} | Ember stones: {self.player.ember_stones}",
                    f"Healing potions: {self.player.potions} | Mana draughts: {self.player.mana_draughts} | Gold: {self.player.gold}",
                    *(f"{item.id}: {item.name} x{item.amount} — {item.value} gold each. {item.description}"
                      for item in self.player.treasure_inventory),
                    "Sell gems and jewelry to Mira with 'sell <item id>' or 'sell all'.",
                    f"Collected notes: {len(self.journal)}. Type 'journal' to browse."]
        if command == "quit":
            self.quit_requested = True
            return ["You leave the trial for another day. Your first dungeon can wait."]
        if command == "portal":
            return self.enter_portal()
        if command == "shop":
            return self.shop()
        if command.startswith("buy "):
            return self.buy(command[4:])
        if command.startswith("sell "):
            return self.sell(command[5:])
        if command == "descend":
            return self.descend()
        if self.in_shop:
            return ["You are shopping. Use 'buy <item id>' or 'descend' when ready."]
        if command in DIRECTIONS:
            return self.move(command)
        if command.startswith("cast "):
            return self.cast_spell(command[5:])
        if command.startswith("rest "):
            try:
                limit = int(command.split(" ", 1)[1])
            except ValueError:
                return ["Use 'rest', 'rest 0', or 'rest' followed by a number of Hit Dice."]
            if limit < 0:
                return ["The number of Hit Dice cannot be negative."]
            return self.short_rest(dice_limit=limit)
        handlers = {
            "examine": self.examine_foe,
            "loot": self.collect_loot, "attack": self.attack, "strike": self.attack_once,
            "ember": self.use_ember, "mana": self.drink_mana, "hide": self.hide,
            "dodge": self.dodge, "disengage": self.disengage,
            "potion": self.drink_potion, "second wind": self.second_wind,
            "action surge": self.action_surge, "end": self.end_turn,
            "rest": self.short_rest, "long rest": self.long_rest,
        }
        if command in handlers:
            return handlers[command]()
        return ["Unknown command. Type 'help' to see your options."]

    def clear_encounter(self) -> None:
        """Discard opening opportunities and observations when combat changes."""
        self.free_examine_available = False
        self.foe_examined = False
        self.ambush_advantage = False
        self.initiative_result = None
        self.perception_result = None
        self.hidden = False
        self.rogue_vex = False
        self.sneak_attack_used = False
        self.shield_active = False
        self.uncanny_dodge_available = True

    def examine_foe(self) -> list[str]:
        """Study a foe once; revisiting acquired information is free."""
        if self.in_shop or self.enemy is None:
            return ["There is no threatening foe here to examine."]
        if not self.player.is_conscious:
            return ["You must be conscious to examine a foe."]
        if self.foe_examined:
            cost = "You recall your observations; no action is spent."
        elif self.free_examine_available:
            cost = "You seize the initiative and examine your foe for free; no action or bonus action is spent."
        else:
            if self.actions_remaining <= 0:
                return ["Examining this foe needs one action. Wait until you have an action available."]
            self.actions_remaining -= 1
            cost = "You spend one action studying your foe. Your bonus action is unchanged."
        self.foe_examined = True
        self.free_examine_available = False
        details = foe_details(self.enemy, self.player.class_id)
        count, sides = details["damage_dice"]
        bonus = details["damage_bonus"]
        return [cost, f"Examining {details['name']}", details["description"],
                f"HP {details['hp']}/{details['max_hp']} | AC {details['armor_class']} | "
                f"Attack {details['attack_bonus']:+d}",
                f"Normal hit: {count}d{sides}{bonus:+d} damage "
                f"({max(0, count + bonus)}–{max(0, count * sides + bonus)} before critical hits).",
                f"Tactical clue: {details['tactics']}", self.turn_status()]

    def move(self, direction: str) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        if self.enemy:
            return ["An enemy blocks your way. Use Disengage ('flee') to retreat safely."]
        target = self.room.exits.get(direction)
        if target is None:
            return ["There is no passage in that direction."]
        self.previous_position = self.position
        self.position = target
        self.clear_encounter()
        self.room.visited = True
        self.elapsed_minutes += 1
        if self.enemy:
            lines = [self.foe_summary()]
            lines.extend(self.begin_encounter())
            if self.enemy and self.player.is_conscious:
                lines.append(self.combat_options())
            return lines
        return self.describe_room()

    def begin_encounter(self) -> list[str]:
        if not self.player.is_alive:
            return []
        self.clear_encounter()
        enemy = self.enemy
        if enemy is None:
            return []
        hero_roll = roll_initiative(self.rng, self.player.initiative_bonus)
        enemy_roll = roll_initiative(self.rng, enemy.initiative_bonus)
        self.round_number = 0
        self.dodging = False
        self.enemy_sapped = False
        self.initiative_result = {"player": hero_roll, "enemy": enemy_roll,
                                  "hero_first": hero_roll >= enemy_roll}
        lines = [f"Initiative: you {hero_roll}, {enemy.name} {enemy_roll}. "
                 "Ties go to the adventurer."]
        if enemy_roll > hero_roll:
            perception_roll = self.rng.randint(1, 20)
            bonus = self.player.perception_bonus
            total = perception_roll + bonus
            dc = 12
            success = total >= dc
            self.perception_result = {"roll": perception_roll, "bonus": bonus,
                                      "total": total, "dc": dc, "success": success}
            self.ambush_advantage = not success
            lines.append(f"Ambush! {enemy.name} lunges before you can study it.")
            lines.append(f"Perception save: d20 [{perception_roll}] {bonus:+d} = {total} vs DC {dc}. "
                         + ("Success! You spot the attack; it has no ambush Advantage." if success
                            else "Failure! The monster's opening attack has Advantage."))
            lines.extend(self.enemy_turn())
        else:
            self.free_examine_available = True
            lines.append("You act first! 'examine' is free before your first action.")
        if self.enemy is not None and self.player.is_alive:
            lines.extend(self.begin_turn())
        return lines

    def begin_turn(self) -> list[str]:
        if not self.player.is_alive:
            return []
        if self.round_number > 0:
            self.free_examine_available = False
        self.round_number += 1
        self.actions_remaining = 1
        self.bonus_action_available = True
        self.dodging = False
        self.enemy_sapped = False
        self.sneak_attack_used = False
        self.uncanny_dodge_available = True
        return [self.turn_status()]

    def attack(self) -> list[str]:
        if self.player.class_id == "wizard":
            return self.cast_spell("firebolt")
        if self.enemy is None or self.actions_remaining <= 0:
            return self.attack_once()
        lines = self.attack_once()
        if (self.player.class_id == "fighter" and self.player.level >= 5
                and self.enemy is not None and self.player.is_conscious):
            self.actions_remaining += 1
            lines.append("Extra Attack: your second longsword strike.")
            lines.extend(self.attack_once())
        return lines

    def attack_once(self) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        enemy = self.enemy
        if enemy is None:
            return ["There is no enemy here to attack."]
        if self.actions_remaining <= 0:
            return ["Your action is spent. Use an available bonus action or 'end'."]
        self.actions_remaining -= 1
        self.free_examine_available = False
        advantage = self.player.class_id == "rogue" and (self.hidden or self.rogue_vex)
        sneak_eligible = advantage and not self.sneak_attack_used
        self.hidden = self.rogue_vex = False
        result = roll_attack(self.rng, self.player.attack_bonus, enemy.armor_class,
                             self.player.weapon_dice, self.player.damage_bonus,
                             advantage=advantage,
                             extra_damage_dice=(self.player.sneak_attack_dice_count, 6) if sneak_eligible else None)
        sneak = result.extra_damage
        if result.hit and sneak_eligible:
            self.sneak_attack_used = True
        lines = [self.weapon_attack_text(enemy.name, result)]
        if sneak:
            lines.append(f"Sneak Attack: an exposed weak point adds {sneak} damage (included above).")
        if result.critical_fail:
            self.player.take_damage(result.fumble_damage)
            lines.append(f"Your HP: {self.player.hp}/{self.player.max_hp}.")
            if not self.player.is_alive:
                return [*lines, *self.death_message()]
        if result.hit:
            enemy.take_damage(result.damage)
            if self.player.class_id == "fighter":
                self.enemy_sapped = True
                lines.append("Sap: the enemy's next attack has Disadvantage before your next turn.")
            elif self.player.class_id == "rogue":
                self.rogue_vex = True
                lines.append("Vex: your next rapier attack against this foe has Advantage.")
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
            description = miss_description(attacker, defender, result)
            return f"{attacker} {verb} {defender} ({roll})." + (f" {description}" if description else "")
        critical = " Critical hit!" if result.critical else ""
        verb = "hit" if attacker == "You" else "hits"
        description = hit_description(attacker, defender, result)
        return f"{attacker} {verb} {defender} ({roll}) for {result.damage} damage.{critical} {description}"

    def weapon_attack_text(self, defender: str, result: AttackResult) -> str:
        if self.player.class_id == "fighter":
            return self.attack_text("You", defender, result)
        weapon = "rapier" if self.player.class_id == "rogue" else "staff"
        roll = f"d20 [{'/'.join(map(str, result.rolls))}], total {result.total}"
        if result.critical_fail:
            return (f"You miss {defender} ({roll}). Critical fail! You flourish your {weapon}, "
                    "trip over a loose stone, and land on your knee. You take 1 HP of self-damage.")
        if not result.hit:
            return (f"You miss {defender} ({roll})." +
                    (f" Near miss! Your {weapon} glances off the foe's defenses without damage."
                     if result.near_miss else ""))
        if result.damage == 0:
            story = f"Your {weapon} connects, but the foe's defenses absorb the blow."
        else:
            band = ("Glancing" if result.damage <= 5 else "Solid" if result.damage <= 10
                    else "Heavy" if result.damage <= 15 else "Devastating")
            story = f"{band} blow! Your {weapon} " + (
                "flicks through an opening in the foe's guard." if weapon == "rapier" else
                "cracks against the foe with a sharp wooden report.")
        return (f"You hit {defender} ({roll}) for {result.damage} damage. "
                + ("Critical hit! " if result.critical else "") + story)

    def defeat_enemy(self, enemy: Enemy) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        self.player.gold += enemy.gold_reward
        levels = self.player.gain_xp(enemy.xp_reward)
        self.dodging = False
        self.enemy_sapped = False
        self.clear_encounter()
        lines = [f"You defeat {enemy.name}! +{enemy.xp_reward} XP, +{enemy.gold_reward} gold."]
        if levels:
            lines.append(f"You reach {self.player.class_name} level {self.player.level}! Maximum HP increases; "
                         "leveling does not fully heal you.")
            if self.player.class_id == "fighter" and self.player.level >= 2:
                lines.append("Action Surge is unlocked: one extra action, once per short or long rest.")
            lines.append("Type 'skills' to review your abilities at this level.")
        if enemy.boss:
            self.floor_cleared = True
            lines.extend([self.dungeon.lore.revelation,
                          f"Floor {self.floor} cleared! A portal opens beside the fallen guardian.",
                          "Type 'portal' to visit Mira's shop, then 'descend' when ready."])
            if self.room.note and not self.room.note_collected:
                lines.append("A guardian document remains here. Use 'loot' before taking the portal.")
        lines.append("The room is safe. Type 'look' to examine it.")
        return lines

    def enemy_turn(self) -> list[str]:
        if not self.player.is_alive:
            return []
        ambush_advantage = self.ambush_advantage
        self.ambush_advantage = False
        enemy = self.enemy
        if enemy is None:
            return []
        result = roll_attack(
            self.rng, enemy.attack_bonus, self.player.armor_class + (5 if self.shield_active else 0),
            enemy.damage_dice, enemy.damage_bonus,
            advantage=ambush_advantage,
            disadvantage=self.enemy_sapped or self.dodging or self.hidden,
        )
        self.enemy_sapped = False
        self.shield_active = False
        mitigated = (result.hit and self.player.class_id == "rogue" and self.player.level >= 5
                     and self.player.is_conscious and self.uncanny_dodge_available)
        if mitigated:
            self.uncanny_dodge_available = False
            result = replace(result, damage=result.damage // 2)
        lines = [self.attack_text(enemy.name, "you", result)]
        if mitigated:
            lines.append("Uncanny Dodge: you twist aside, halving the blow's damage (included above).")
        if result.critical_fail:
            enemy.take_damage(result.fumble_damage)
            lines.append(f"{enemy.name}: {enemy.hp}/{enemy.max_hp} HP.")
            if not enemy.is_alive:
                lines.extend(self.defeat_enemy(enemy))
        if result.hit:
            self.player.take_damage(result.damage, critical=result.critical)
        lines.append(f"Your HP: {self.player.hp}/{self.player.max_hp}.")
        if not self.player.is_alive:
            lines.extend(self.death_message())
        return lines

    @staticmethod
    def death_message() -> list[str]:
        return ["You die in the catacombs at 0 HP. Your adventure ends here.",
                "Choose 'New Adventure' in the window, or restart the game to try again."]

    def end_turn(self) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        self.free_examine_available = False
        if self.enemy is None:
            return ["There is no combat turn to end. Explore or rest."]
        self.elapsed_minutes += 0.1
        lines = self.enemy_turn()
        if self.player.is_alive and self.enemy is not None:
            lines.extend(self.begin_turn())
        return lines

    def dodge(self) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        if not self.enemy:
            return ["There is no enemy to dodge."]
        if self.actions_remaining <= 0:
            return ["Your action is already spent."]
        self.actions_remaining -= 1
        self.free_examine_available = False
        self.dodging = True
        return ["You Dodge. Visible enemy attacks have Disadvantage until your next turn.",
                self.turn_status()]

    def disengage(self) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        if not self.enemy:
            return ["There is no enemy to disengage from."]
        if self.previous_position is None:
            return ["There is nowhere to retreat."]
        cunning = self.player.class_id == "rogue" and self.player.level >= 2
        if cunning:
            error = self.bonus_action_error()
            if error:
                return error
            self.bonus_action_available = False
        else:
            if self.actions_remaining <= 0:
                return ["Disengage needs an action. Wait until your next turn."]
            self.actions_remaining -= 1
        old_position = self.position
        self.position = self.previous_position
        self.previous_position = old_position
        self.dodging = False
        self.enemy_sapped = False
        self.clear_encounter()
        return [("Cunning Action: you spend a bonus action and retreat." if cunning else
                 "You take the Disengage action and retreat.") + " No opportunity attack is made.",
                *self.describe_room()]

    def bonus_action_error(self) -> list[str]:
        if self.enemy and not self.bonus_action_available:
            return ["You have already used your bonus action this turn."]
        return []

    def drink_potion(self) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
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
        if not self.player.is_alive:
            return self.death_message()
        if self.player.class_id != "fighter":
            return ["Second Wind is a Warrior ability. Use 'skills' for your class abilities."]
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
        if not self.player.is_alive:
            return self.death_message()
        if self.player.class_id != "fighter":
            return ["Action Surge is a Warrior ability. Use 'skills' for your class abilities."]
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
        if not self.player.is_alive:
            return self.death_message()
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
        lines = [f"You take a one-hour short rest. Spent {spent} Hit Dice, healing {healed} HP."]
        if self.player.class_id == "fighter":
            lines.append("You recover one Second Wind use and refresh Action Surge.")
        elif self.player.class_id == "wizard":
            recovered = self.player.recover_arcane_slots()
            if recovered:
                lines.append("Arcane Recovery restores " + ", ".join(
                    f"{count} level-{level} slot(s)" for level, count in recovered.items()) + ".")
        return [*lines, *self.status()]

    def skills(self) -> list[str]:
        """Class guidance is informational and remains useful in every scene."""
        p = self.player
        if p.class_id == "fighter":
            return ["Warrior (Fighter) abilities",
                    "attack / strike: Strength-based longsword; a hit applies Sap (enemy Disadvantage).",
                    "wind: bonus action, heal 1d10 + level; short rest restores one use.",
                    "surge: level 2, one extra combat action; refreshes on a short or long rest.",
                    "Extra Attack: level 5, 'attack' makes two strikes for one action."]
        if p.class_id == "rogue":
            return ["Rogue abilities",
                    "attack / strike: Dexterity-based rapier; a hit applies Vex (your next attack has Advantage).",
                    f"Sneak Attack: {p.sneak_attack_dice_count}d6 extra on an advantaged hit, once per turn; critical hits double these dice.",
                    "hide: Stealth check vs DC 12 + dungeon floor; action at level 1, bonus action from level 2.",
                    "Hiding gives enemy attacks Disadvantage and your next attack Advantage; attacking reveals you.",
                    "Expertise: double proficiency on Stealth and the ambush Perception save.",
                    "Cunning Action: from level 2, 'flee' uses a bonus action and avoids an opportunity attack.",
                    "Uncanny Dodge: from level 5, automatically halve one incoming hit per turn while conscious."]
        return ["Wizard abilities — cast <spell>; each spell below costs one action except Shield",
                "attack / cast firebolt: no slot, Intelligence attack, 1d10 fire damage (2d10 from level 5).",
                "strike: Strength-based quarterstaff attack; runic staff bonuses also improve spell attacks and save DC.",
                "cast missile: level-1 slot, three force darts for 3d4+3 damage; automatically hits.",
                "cast armor: level-1 slot, base AC 13 + Dexterity until your next long rest; cast before a fight.",
                "cast shield: level-1 slot and bonus action, +5 AC against the next enemy strike only.",
                "cast frost: level-2 slot, Intelligence attack for 3d8 cold damage; a hit hinders the enemy's next attack.",
                "cast fireball: level-3 slot, 8d6 fire damage; enemy Dexterity save halves damage.",
                "Short rest: Arcane Recovery restores lower-level slots once per long rest.",
                "Long rest restores all slots; mana draughts restore one spent level-1 slot.",
                "These spell costs and durations are dungeon adaptations; 'stats' shows available slots."]

    def hide(self) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        if self.player.class_id != "rogue":
            return ["Hide is a Rogue ability. Use 'skills' for your class abilities."]
        if not self.enemy:
            return ["Save hiding for a foe you need to evade."]
        if self.hidden:
            return ["You are already hidden; your next attack has Advantage."]
        bonus = self.player.level >= 2
        if bonus:
            error = self.bonus_action_error()
            if error:
                return error
            self.bonus_action_available = False
        else:
            if self.actions_remaining <= 0:
                return ["Hide needs an action at level 1. Wait until your next turn."]
            self.actions_remaining -= 1
            self.free_examine_available = False
        roll = self.rng.randint(1, 20)
        total = roll + self.player.stealth_bonus
        dc = 12 + self.floor
        self.hidden = total >= dc
        return [f"Stealth: d20 [{roll}] {self.player.stealth_bonus:+d} = {total} vs DC {dc}. "
                + ("You slip into shadow; your next attack has Advantage." if self.hidden else
                   "The foe tracks your movement; you remain visible."), self.turn_status()]

    def cast_spell(self, spell: str) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        if self.player.class_id != "wizard":
            return ["Spellcasting is a Wizard ability. Use 'skills' for your class abilities."]
        aliases = {"fire bolt": "firebolt", "magic missile": "missile", "mage armor": "armor",
                   "ice knife": "frost", "shield spell": "shield"}
        spell = aliases.get(spell, spell)
        slot_level = {"firebolt": 0, "missile": 1, "armor": 1, "shield": 1,
                      "frost": 2, "fireball": 3}.get(spell)
        if slot_level is None:
            return ["Unknown spell. Type 'skills' for spell names and costs."]
        enemy = self.enemy
        if spell != "armor" and enemy is None:
            return ["That spell needs a threatening foe. Cast 'armor' to prepare in a safe room."]
        if spell == "armor" and self.player.mage_armor_active:
            return ["Mage Armor is already active; you keep your spell slot."]
        if spell == "shield" and self.shield_active:
            return ["Shield is already waiting for the next strike; you keep your spell slot."]
        if slot_level and self.player.spell_slots.get(slot_level, 0) <= 0:
            return [f"You have no level-{slot_level} spell slots available. Use 'stats' to check resources."]
        if enemy:
            if spell == "shield":
                error = self.bonus_action_error()
                if error:
                    return error
            elif self.actions_remaining <= 0:
                return ["Your action is spent. Wait until your next turn."]
        # All validation precedes resource use and random rolls.
        if slot_level:
            self.player.spend_spell_slot(slot_level)
        if enemy:
            if spell == "shield":
                self.bonus_action_available = False
            else:
                self.actions_remaining -= 1
                self.free_examine_available = False
        if spell == "armor":
            self.player.mage_armor_active = True
            return [f"Mage Armor shimmers around you. AC {self.player.armor_class}; lasts until your next long rest."]
        if spell == "shield":
            self.shield_active = True
            return [f"A luminous Shield unfolds. AC {self.player.armor_class + 5} against the next enemy strike.", self.turn_status()]
        if spell in ("firebolt", "frost"):
            dice = (2 if self.player.level >= 5 else 1, 10) if spell == "firebolt" else (3, 8)
            result = roll_attack(self.rng, self.player.spell_attack_bonus, enemy.armor_class, dice, 0)
            label = "Fire Bolt" if spell == "firebolt" else "Frost Lance"
            if result.hit:
                strength = ("grazes" if result.damage <= 5 else "strikes" if result.damage <= 10
                            else "slams into" if result.damage <= 15 else "engulfs")
                energy = "flame" if spell == "firebolt" else "razor-cold light"
                lines = [f"{label}: d20 [{'/'.join(map(str, result.rolls))}], total {result.total}. "
                         f"Your {energy} {strength} {enemy.name} for {result.damage} damage."
                         + (" Critical hit!" if result.critical else "")]
            elif result.critical_fail:
                lines = [f"{label}: natural 1! A hiccup scatters your spell; a stray spark stings you for 1 damage."]
            else:
                lines = [f"{label}: d20 [{result.roll}], total {result.total}. The spell "
                         + ("skims past the foe's defenses without harm." if result.near_miss else
                            "bursts harmlessly against the stones.")]
            if result.critical_fail:
                self.player.take_damage(result.fumble_damage)
                if not self.player.is_alive:
                    return [*lines, *self.death_message()]
            damage = result.damage
            if spell == "frost" and result.hit:
                self.enemy_sapped = True
                lines.append("Frost binds the foe; its next attack has Disadvantage before your next turn.")
        elif spell == "missile":
            damage = roll_dice(self.rng, 3, 4) + 3
            lines = [f"Three Magic Missiles strike {enemy.name} for {damage} force damage!"]
        else:
            damage = roll_dice(self.rng, 8, 6)
            save_roll = self.rng.randint(1, 20)
            total = save_roll + enemy.initiative_bonus
            saved = total >= self.player.spell_save_dc
            if saved:
                damage //= 2
            lines = [f"Fireball: {enemy.name} rolls Dexterity {total} vs DC {self.player.spell_save_dc}: "
                     f"{'success, half damage' if saved else 'failure'}. Flames deal {damage} damage!"]
        enemy.take_damage(damage)
        if not enemy.is_alive:
            lines.extend(self.defeat_enemy(enemy))
        else:
            lines.extend([f"{enemy.name}: {enemy.hp}/{enemy.max_hp} HP.", self.turn_status()])
        return lines

    def drink_mana(self) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        if self.player.class_id != "wizard":
            return ["Only Wizards can use a mana draught to restore a spell slot."]
        error = self.bonus_action_error()
        if error:
            return error
        if self.player.mana_draughts <= 0:
            return ["You have no mana draughts."]
        if not self.player.restore_level_one_slot():
            return ["Your level-1 slots are full; you keep the mana draught."]
        self.player.mana_draughts -= 1
        if self.enemy:
            self.bonus_action_available = False
        return ["You drink a mana draught and recover one level-1 spell slot."]

    def store_valuable(self, item) -> None:
        for index, held in enumerate(self.player.treasure_inventory):
            if held.id == item.id:
                self.player.treasure_inventory[index] = replace(held, amount=held.amount + item.amount)
                return
        self.player.treasure_inventory.append(item)

    def sell(self, item_id: str) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        if not self.in_shop:
            return ["Mira buys gems and jewelry in the portal sanctuary. Visit her to sell treasure."]
        selected = [item for item in self.player.treasure_inventory if item_id == "all" or item.id == item_id]
        if not selected:
            return ["No matching valuables. Use 'inventory' for item ids or 'sell all'."]
        value = sum(item.amount * item.value for item in selected)
        ids = {item.id for item in selected}
        self.player.treasure_inventory[:] = [item for item in self.player.treasure_inventory if item.id not in ids]
        self.player.gold += value
        return [f"Mira buys your treasure for {value} gold. Gold: {self.player.gold}."]

    def long_rest(self) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        if self.enemy or self.position != self.dungeon.start:
            return ["An eight-hour long rest is only safe at the entrance, away from enemies."]
        if self.elapsed_minutes - self.last_long_rest_end < 960:
            return ["Wait at least 16 hours after your last long rest before starting another."]
        self.elapsed_minutes += 480
        self.last_long_rest_end = self.elapsed_minutes
        self.player.long_rest()
        return ["You spend eight hours resting at the entrance. "
                "HP, Hit Dice, and class resources are restored; Mage Armor fades.", *self.status()]

    def collect_loot(self) -> list[str]:
        if self.in_shop:
            return ["You are at the vendor. Search dungeon rooms for notes and treasure."]
        if not self.player.is_conscious:
            return ["You must be conscious to search for notes and treasure."]
        if self.enemy:
            return ["Defeat the enemy before searching for notes and treasure."]
        lines = []
        loot = self.room.loot
        if loot is not None and not self.room.looted:
            self.room.looted = True
            self.player.gold += loot.gold
            self.player.potions += loot.potions
            lines.append(f"You collect {loot.gold} gold and {loot.potions} healing potion(s).")
            if loot.weapon_name:
                lines.append(weapon_discovery_description(loot.weapon_name, loot.weapon_bonus))
                if self.player.equip_weapon(loot.weapon_name, loot.weapon_bonus):
                    lines.append("You equip the newly discovered weapon.")
                else:
                    lines.append(f"You keep using {self.player.weapon_name}; this find is no better.")
            if loot.armor_name:
                lines.append(f"You uncover {loot.armor_name}. Woven runes reinforce it: +{loot.armor_bonus} Armor Class.")
                if loot.armor_bonus > self.player.armor_bonus:
                    self.player.armor_bonus = loot.armor_bonus
                    lines.append("You equip the newly discovered armor.")
                else:
                    lines.append("Your current armor is as good or better; you keep wearing it.")
            for item in loot.items:
                lines.append(f"You collect {item.name} x{item.amount}. {item.description}")
                if item.kind == "ember":
                    self.player.ember_stones += item.amount
                elif item.kind == "mana":
                    if self.player.class_id == "wizard":
                        self.player.mana_draughts += item.amount
                    else:
                        self.store_valuable(item)
                        lines.append(f"You cannot use this draught; Mira pays {item.value} gold each. Item id: {item.id}.")
                else:
                    self.store_valuable(item)
                    lines.append(f"Mira will pay {item.value} gold each; item id: {item.id}.")
        note = self.room.note
        if note is not None and not self.room.note_collected:
            self.room.note_collected = True
            if not any(entry.id == note.id for entry in self.journal):
                self.journal.append(note)
                lines.append(f"You collect '{note.title}' and add it to your journal.")
                lines.append(f"Type 'read {len(self.journal)}' to read it, or 'journal' to browse your notes.")
        if lines:
            return [discovery_description(self.room, self.floor), *lines]
        return ["There are no unclaimed notes or treasure here."]

    def journal_lines(self) -> list[str]:
        if not self.journal:
            return ["Your journal has no collected notes yet. Search dungeon rooms with 'loot'."]
        return [f"Adventurer's journal — {len(self.journal)} collected note(s)",
                *(f"{index}. {note.title} (Floor {note.floor}; id: {note.id}) — read {index}"
                  for index, note in enumerate(self.journal, 1)),
                "Use 'read <number>', 'read <note id>', or 'read' for your latest note."]

    def read_note(self, argument: str = "") -> list[str]:
        if not self.journal:
            return ["You have no collected notes to read. Search rooms with 'loot' first."]
        query = argument.strip().lower()
        note = None
        if not query:
            note = self.journal[-1]
        else:
            try:
                number = int(query)
            except ValueError:
                note = next((entry for entry in self.journal if entry.id == query), None)
            else:
                if 1 <= number <= len(self.journal):
                    note = self.journal[number - 1]
        if note is None:
            return ["That note is not in your journal. Type 'journal' to see collected note numbers and ids."]
        return [f"{note.title} | Floor {note.floor} | {note.room_name}", "", note.text,
                "", f"Adventurer's clue: {note.hint}"]


    def enter_portal(self) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        if self.in_shop:
            return ["You are already in Mira's sanctuary."]
        if not self.floor_cleared or self.position != self.dungeon.boss_position:
            return ["The portal opens in the guardian's room only after its defeat."]
        self.in_shop = True
        self.elapsed_minutes += 480
        self.last_long_rest_end = self.elapsed_minutes
        self.player.long_rest()
        return ["The portal teleports you to Mira's sanctuary. A safe night's rest restores your resources.",
                *self.describe_room(), *self.shop()]

    def shop(self) -> list[str]:
        if not self.in_shop:
            return ["Visit the vendor through a cleared floor's portal first."]
        return [f"Mira's stock | Gold: {self.player.gold}",
                *(f"{item.id}: {item.name} — {item.price} gold. {item.description}"
                  for item in stock(self.floor, self.player.class_id)),
                "Buy with 'buy <item id>'; sell with 'sell <item id>' or 'sell all'. Type 'descend' when done."]

    def buy(self, item_id: str) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        if not self.in_shop:
            return ["You can only buy items at the vendor."]
        if item_id == "weapon":
            item_id = "sword"
        item = next((item for item in stock(self.floor, self.player.class_id) if item.id == item_id), None)
        if item is None:
            return ["Unknown item. Use 'shop' for item ids and prices."]
        p = self.player
        redundant = ((item.kind == "weapon" and p.weapon_bonus >= item.value)
                     or (item.kind == "armor" and p.armor_bonus >= item.value)
                     or (item.kind == "charm" and p.vitality_charm)
                     or (item.kind == "ward" and p.ward_bonus >= item.value))
        if redundant:
            return ["You already have this item or better gear. Your gold is unchanged."]
        if p.gold < item.price:
            return [f"You need {item.price} gold; you have {p.gold}."]
        p.gold -= item.price
        if item.kind == "weapon":
            p.equip_weapon(item.name, item.value)
        elif item.kind == "armor":
            p.armor_bonus = item.value
        elif item.kind == "ward":
            p.ward_bonus = item.value
        elif item.kind == "charm":
            p.vitality_charm = True
            p.max_hp += item.value
            p.hp += item.value
        elif item.kind == "potion":
            p.potions += item.value
        elif item.kind == "ember":
            p.ember_stones += item.value
        elif item.kind == "mana":
            p.mana_draughts += item.value
        return [f"Bought {item.name} for {item.price} gold. Gold remaining: {p.gold}."]

    def descend(self) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        if not self.in_shop:
            return ["Use the guardian's portal and finish shopping before descending."]
        if self.floor == self.total_floors:
            self.won = True
            return ["Mira's final portal returns you to daylight.",
                    "Your first dungeon is conquered! Every guardian has fallen.", *self.status()]
        self.floor += 1
        self.dungeon = Dungeon(self.rng, floor=self.floor, class_id=self.player.class_id)
        self.position = self.dungeon.start
        self.previous_position = None
        self.room.visited = True
        self.floor_cleared = False
        self.in_shop = False
        self.actions_remaining = 1
        self.bonus_action_available = True
        self.dodging = self.enemy_sapped = False
        self.round_number = 0
        self.clear_encounter()
        return [f"The portal carries you deeper, to floor {self.floor}.",
                self.dungeon.lore.arrival, "", *self.describe_room()]

    def use_ember(self) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        enemy = self.enemy
        if enemy is None:
            return ["Save Ember stones for combat."]
        if self.actions_remaining <= 0:
            return ["Your action is spent."]
        if self.player.ember_stones <= 0:
            return ["You have no Ember stones. Buy them from Mira."]
        self.actions_remaining -= 1
        self.free_examine_available = False
        self.player.ember_stones -= 1
        damage = roll_dice(self.rng, 3, 6)
        enemy.take_damage(damage)
        lines = [f"Your Ember stone bursts for {damage} magic damage!"]
        if not enemy.is_alive:
            lines.extend(self.defeat_enemy(enemy))
        else:
            lines.append(self.turn_status())
        return lines

    def get_state(self) -> dict:
        """Detached JSON-compatible view for renderers; reading never rolls RNG.

        Room identities are [x,y] coordinates within the current floor. Unknown
        rooms expose only their position so graphical maps cannot leak enemies.
        A renderer can display this state and call perform(Action(...)) without
        parsing terminal prose. Mutating the snapshot cannot change the engine.
        """
        rooms = []
        for room in self.dungeon.rooms.values():
            data = {"position": list(room.position), "visited": room.visited}
            if room.visited:
                data.update(name=room.name, description=room.description,
                            exits={k: list(v) for k, v in room.exits.items()},
                            enemy=asdict(room.enemy) if room.enemy else None,
                            loot=asdict(room.loot) if room.loot and not room.looted else None,
                            note={"id": room.note.id, "title": room.note.title} if room.note else None,
                            note_collected=room.note_collected)
            rooms.append(data)
        return {"floor": self.floor, "total_floors": self.total_floors,
                "theme": self.dungeon.theme.name,
                "story": {"arrival": self.dungeon.lore.arrival,
                          "revelation": self.dungeon.lore.revelation if self.floor_cleared else None},
                "scene": "shop" if self.in_shop else "dungeon",
                "position": list(self.position), "player": {**asdict(self.player), "dead": not self.player.is_alive},
                "journal": [asdict(note) for note in self.journal],
                "armor_class": self.player.armor_class + (5 if self.shield_active else 0),
                "attack_bonus": self.player.attack_bonus,
                "class_name": self.player.class_name,
                "spell_attack_bonus": self.player.spell_attack_bonus if self.player.class_id == "wizard" else None,
                "spell_save_dc": self.player.spell_save_dc if self.player.class_id == "wizard" else None,
                "perception_bonus": self.player.perception_bonus,
                "rooms": rooms, "portal_open": self.floor_cleared,
                "portal_position": list(self.dungeon.boss_position) if self.floor_cleared else None,
                "shop": [asdict(item) for item in stock(self.floor, self.player.class_id)] if self.in_shop else [],
                "encounter": {
                    "initiative": dict(self.initiative_result) if self.initiative_result else None,
                    "perception": dict(self.perception_result) if self.perception_result else None,
                    "free_examine_available": self.free_examine_available,
                    "foe_examined": self.foe_examined,
                    "ambush_advantage": self.ambush_advantage,
                    "foe_details": foe_details(self.enemy, self.player.class_id) if self.foe_examined and self.enemy else None,
                    "hidden": self.hidden, "vex": self.rogue_vex,
                    "sneak_attack_used": self.sneak_attack_used,
                    "shield_active": self.shield_active,
                    "uncanny_dodge_available": self.uncanny_dodge_available,
                },
                "turn": {"round": self.round_number, "actions": self.actions_remaining,
                         "bonus_action": self.bonus_action_available},
                "won": self.won, "over": self.over}
