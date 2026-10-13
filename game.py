"""Solo dungeon exploration and D&D-inspired class combat."""

from dataclasses import asdict, replace
from actions import Action
from battle_flavor import hit_description, miss_description
from campaign import FLOORS, preferred_item_id, sanctuary_dialogue, shop_items, stock
from equipment import DEFAULT_ARMOR, DEFAULT_WEAPONS, EQUIPMENT, make_equipment, resolve_equipment_id
from lore_notes import LoreNote
from loot_flavor import (
    discovery_description, loot_clue_description, preview_description,
    weapon_discovery_description,
)
import random

from combat import (AttackResult, damage_notation, format_damage_pool,
                    roll_attack, roll_initiative, roll_dice)
from dungeon import Dungeon
from enemy_lore import foe_details
from player import Player
from room import Enemy, Room
from utils import health_bar


HELP = """Explore: north/south/east/west (n/s/e/w), look, map, loot
Foes: examine (free opening opportunity, otherwise one action; rereading is free)
Items: examine <item id or name> (free); inventory [page] lists carried items
Lore: journal, read (latest note), read <journal number or note id>
Actions: attack (a), dodge (d), disengage (flee/f)
Bonus actions: potion (p), second wind (wind)
Turn control: end, action surge (surge; fighter level 2)
Rest: rest [dice] (1 hour), long rest (8 hours; entrance only)
Portal: portal (after guardian), menu, shop <category> [page], buy <item id or name>, descend
Equipment: inventory, equip <item id or name> (safe room), sell <item id>/sell all (vendor)
Classes: skills, hide (Rogue), cast <spell> (Wizard), strike (weapon attack)
Magic items: ember (action, 3d6 damage), mana (bonus action, restores one level-1 slot)
Other: stats, inventory (i), help (h), quit (q)

Attacks: d20 + attack bonus vs Armor Class. Natural 1 critically fails for 1 self-damage; 20 crits.
A miss within 1–2 points of AC gets near-miss narration but deals no damage.
Hit descriptions reflect damage: glancing 1–5, solid 6–10, heavy 11–15, devastating 16+.
Critical hits double damage dice, not modifiers. Weapon mastery determines Sap or Vex effects.
Dodge gives attacks against you Disadvantage until your next turn.
Disengage retreats without an opportunity attack; Rogues use a bonus action from level 2.
Potions heal 2d4+2; Second Wind heals 1d10 + fighter level.
Each combat turn has an action and a bonus action. Type 'end' when done.
Other informational and invalid commands do not spend actions or advance combat.
Winning initiative (including ties) lets you examine before your first action for free.
In a new hostile room, a Perception check vs DC 12 can spot the foe before it notices you.
Success gives you the opening turn and a free examination. Rogues can try 'hide' once
without spending an action or bonus action, then attack from hiding for Sneak Attack.
Hide checks require DC 20. Sneak Attack requires a hidden Rogue using a finesse weapon.
Failed opening Hide alerts the foe: if it wins initiative, its opening attack has Advantage.
If entry Perception fails, roll initiative; a monster acting first has ambush Advantage.
Revisiting a hostile room uses initiative and the usual Perception ambush save vs DC 12.
Perception checks and saves use Wisdom; Rogues add expertise. They cause no fumble damage.
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
            return [f"Mira: {sanctuary_dialogue(self.floor)}", *self.sanctuary_menu()]
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
        if self.enemy_unaware:
            if self.player.class_id == "rogue" and self.hidden:
                return "The foe is unaware. Use 'attack' for an advantaged Sneak Attack, or examine it for free."
            if self.opening_hide_available:
                return "The foe is unaware. Choose 'hide' (one free attempt), 'attack', or 'examine' (free)."
            return "The foe is unaware. Strike first with 'attack', or 'examine' it for free."
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
            f"Perception {player.perception_bonus:+d} | Spotting and ambush DC 12",
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
            lines.append(f"Stealth {player.stealth_bonus:+d} | Hide DC 20 | Sneak Attack {player.sneak_attack_dice_count}d6 while hidden, once per turn")
        if player.equipment_buffs:
            lines.append("Effective abilities with gear: " + " | ".join(
                f"{ability[:3].upper()} {score}" for ability, score in player.effective_abilities.items()))
            lines.append("Gear effects: " + ", ".join(f"{effect} +{amount}" for effect, amount in player.equipment_buffs.items()))
        if not player.is_alive:
            lines.append("Dead | Your adventure has ended.")
        elif self.enemy:
            lines.append(self.turn_status())
        return lines

    def turn_status(self) -> str:
        bonus = "ready" if self.bonus_action_available else "spent"
        if self.enemy_unaware:
            return f"Foe unaware | Opening actions left: {self.actions_remaining} | Bonus action: {bonus}"
        return f"Round {self.round_number} | Actions left: {self.actions_remaining} | Bonus action: {bonus}"

    def handle_command(self, raw: str) -> list[str]:
        """Execute one command without spending turns on invalid input."""
        command = " ".join(raw.lower().split())
        if command.startswith(("go ", "move ")):
            command = command.split(" ", 1)[1]
        command = ALIASES.get(command, command)
        if command.startswith(("buy ", "rest ", "read ", "cast ", "sell ", "equip ", "shop ", "examine ", "inventory ", "inspect ")):
            kind, argument = command.split(" ", 1)
            if kind == "inspect":
                kind = "examine"
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
            return self.inventory()
        if command.startswith("inventory "):
            return self.inventory(command[10:])
        if command.startswith("examine "):
            return self.examine_item(command[8:])
        if command == "examine" and self.in_shop:
            return self.examine_item("")
        if command == "quit":
            self.quit_requested = True
            return ["You leave the trial for another day. Your first dungeon can wait."]
        if command == "portal":
            return self.enter_portal()
        if command == "menu":
            return self.sanctuary_menu() if self.in_shop else ["Mira's menu is available in her sanctuary."]
        if self.in_shop and command in ("1", "2", "3", "4", "5", "6"):
            return {"1": lambda: self.shop("weapons"), "2": lambda: self.shop("armor"),
                    "3": lambda: self.shop("supplies"), "4": self.inventory,
                    "5": lambda: self.sell("all"), "6": self.descend}[command]()
        if command == "shop" or command.startswith("shop "):
            return self.shop(command[5:] if command.startswith("shop ") else "")
        if command.startswith("buy "):
            return self.buy(command[4:])
        if command.startswith("sell "):
            return self.sell(command[5:])
        if command.startswith("equip "):
            return self.equip(command[6:])
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
        self.scouting_result = None
        self.enemy_unaware = False
        self.opening_hide_available = False

    def reveal_opening(self) -> None:
        """An action or the end of the opening turn alerts a spotted foe."""
        self.enemy_unaware = False
        self.opening_hide_available = False

    def examine_foe(self) -> list[str]:
        """Study a foe once; revisiting acquired information is free."""
        if self.in_shop:
            return ["Use 'examine <item id or name>' to read an item's description and effects."]
        if self.enemy is None:
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
            self.reveal_opening()
            cost = "You spend one action studying your foe. Your bonus action is unchanged."
        self.foe_examined = True
        self.free_examine_available = False
        details = foe_details(self.enemy, self.player.class_id, weapon_mastery=self.player.weapon_mastery)
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
        first_visit = not self.room.visited
        self.clear_encounter()
        self.room.visited = True
        self.elapsed_minutes += 1
        if self.enemy:
            lines = [self.foe_summary()]
            lines.extend(self.begin_encounter(scout=first_visit))
            if self.enemy and self.player.is_conscious:
                lines.append(self.combat_options())
            return lines
        return self.describe_room()

    def begin_encounter(self, *, scout: bool = False) -> list[str]:
        if not self.player.is_alive:
            return []
        self.clear_encounter()
        enemy = self.enemy
        if enemy is None:
            return []
        if scout:
            roll = self.rng.randint(1, 20)
            bonus = self.player.perception_bonus
            total, dc = roll + bonus, 12
            success = total >= dc
            self.scouting_result = {"roll": roll, "bonus": bonus, "total": total,
                                    "dc": dc, "success": success}
            lines = [f"Perception check: d20 [{roll}] {bonus:+d} = {total} vs DC {dc}. "
                     + ("Success! You spot the foe first." if success else
                        "Failure! The foe notices your arrival.")]
            if success:
                self.round_number = 0
                self.dodging = self.enemy_sapped = False
                self.enemy_unaware = True
                self.opening_hide_available = self.player.class_id == "rogue"
                self.free_examine_available = True
                self.initiative_result = {"player": None, "enemy": None,
                                          "hero_first": True, "source": "scouting"}
                lines.append(f"{enemy.name} has not noticed you. You act first; 'examine' is free.")
                return [*lines, *self.begin_turn()]
            return [*lines, *self._roll_encounter_initiative(entry_failed=True)]
        return self._roll_encounter_initiative()

    def _roll_encounter_initiative(self, *, entry_failed: bool = False,
                                  ambush_allowed: bool = True,
                                  failed_hide: bool = False,
                                  preserve_opening_budget: bool = False) -> list[str]:
        """Resolve ordinary initiative after failed spotting or revealed stealth."""
        enemy = self.enemy
        if enemy is None or not self.player.is_alive:
            return []
        opening_budget = (self.actions_remaining, self.bonus_action_available)
        self.reveal_opening()
        self.free_examine_available = False
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
            if failed_hide:
                self.ambush_advantage = True
                lines.append(f"Caught hiding! {enemy.name} wins initiative and attacks with Advantage.")
            elif not ambush_allowed:
                lines.append(f"{enemy.name} reacts first. You already spotted it; this is no ambush.")
            elif entry_failed:
                self.ambush_advantage = True
                lines.append(f"Ambush! {enemy.name}'s opening attack has Advantage after your failed spotting check.")
            else:
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
            turn_lines = self.begin_turn()
            if preserve_opening_budget and hero_roll >= enemy_roll:
                # Failing to hide cannot refund a bonus action already spent
                # before this same opening turn's first enemy response.
                self.actions_remaining, self.bonus_action_available = opening_budget
                turn_lines = [self.turn_status()]
            lines.extend(turn_lines)
        return lines

    def begin_turn(self) -> list[str]:
        if not self.player.is_alive:
            return []
        if self.round_number > 0:
            self.free_examine_available = False
            self.reveal_opening()
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
            lines.append("Extra Attack: your second weapon strike.")
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
        self.reveal_opening()
        was_hidden = self.hidden
        advantage = was_hidden or self.rogue_vex
        sneak_eligible = (self.player.class_id == "rogue" and
                          self.player.equipped_weapon.spec.finesse and was_hidden and
                          not self.sneak_attack_used)
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
            if self.player.class_id == "fighter" and self.player.weapon_mastery == "sap":
                self.enemy_sapped = True
                lines.append("Sap: the enemy's next attack has Disadvantage before your next turn.")
            elif self.player.class_id in ("fighter", "rogue") and self.player.weapon_mastery == "vex":
                self.rogue_vex = True
                lines.append("Vex: your next weapon attack against this foe has Advantage.")
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
        return f"{attacker} {verb} {defender} ({roll}) for {damage_notation(result)} damage.{critical} {description}"

    def weapon_attack_text(self, defender: str, result: AttackResult) -> str:
        if self.player.class_id == "fighter" and self.player.weapon_id == "longsword":
            return self.attack_text("You", defender, result)
        weapon = self.player.equipped_weapon.spec.name.lower()
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
                "flicks through an opening in the foe's guard." if self.player.equipped_weapon.spec.finesse else
                "lands squarely with a sharp impact.")
        return (f"You hit {defender} ({roll}) for {damage_notation(result)} damage. "
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
        if self.enemy_unaware:
            return ["The foe has not noticed you. Choose your opening action, or 'end' to give up the opening."]
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
        self.reveal_opening()
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
        self.reveal_opening()
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
                    f"attack / strike: {p.weapon_name}, using {p.weapon_ability}; mastery: {p.weapon_mastery or 'none'}.",
                    "Sap weapons hinder the enemy's next attack; Vex weapons grant your next strike Advantage.",
                    "One-handed weapons allow your shield and Dueling; two-handed weapons trade both for damage.",
                    "wind: bonus action, heal 1d10 + level; short rest restores one use.",
                    "surge: level 2, one extra combat action; refreshes on a short or long rest.",
                    "Extra Attack: level 5, 'attack' makes two strikes for one action."]
        if p.class_id == "rogue":
            return ["Rogue abilities",
                    f"attack / strike: {p.weapon_name}; finesse uses your better Strength or Dexterity modifier.",
                    "Vex weapons grant your next attack Advantage; other finesse weapons can still deliver Sneak Attack.",
                    f"Sneak Attack: {p.sneak_attack_dice_count}d6 extra while hidden with a finesse weapon, once per turn; critical hits double these dice.",
                    "hide: Stealth check vs DC 20; action at level 1, bonus action from level 2.",
                    "Spot a new foe with Perception to get one free opening Hide attempt, then attack before it notices you.",
                    "Hiding gives enemy attacks Disadvantage and your next attack Advantage; attacking reveals you.",
                    "Armor that hinders stealth gives Hide checks Disadvantage.",
                    "Expertise: double proficiency on Stealth, room-entry Perception, and the ambush save.",
                    "Cunning Action: from level 2, 'flee' uses a bonus action and avoids an opportunity attack.",
                    "Uncanny Dodge: from level 5, automatically halve one incoming hit per turn while conscious."]
        return ["Wizard abilities — cast <spell>; each spell below costs one action except Shield",
                "attack / cast firebolt: no slot, Intelligence attack, 1d10 fire damage (2d10 from level 5).",
                "strike: attack with your equipped weapon; finesse uses the better Strength or Dexterity modifier.",
                "An enchanted Arcane Staff improves spell attacks and save DC; Quarterstaff enchantments improve physical strikes.",
                "cast missile: level-1 slot, three force darts for 3d4+3 damage; automatically hits.",
                "cast armor: level-1 slot, base AC 13 + Dexterity until your next long rest; cast before a fight.",
                "cast shield: level-1 slot and bonus action, +5 AC against the next enemy strike only.",
                "cast frost: level-2 slot, Intelligence attack for 3d8 cold damage; a hit hinders the enemy's next attack.",
                "cast fireball: level-3 slot, 8d6 fire damage; enemy Dexterity save halves damage.",
                "Short rest: Arcane Recovery restores lower-level slots once per long rest.",
                "Long rest restores all slots; mana draughts restore one spent level-1 slot.",
                "These spell costs and durations are dungeon adaptations; 'stats' shows available slots."]

    def _stealth_roll(self) -> tuple[int, str]:
        rolls = [self.rng.randint(1, 20)]
        if self.player.stealth_disadvantage:
            rolls.append(self.rng.randint(1, 20))
        return min(rolls), "/".join(str(roll) for roll in rolls)

    def hide(self) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        if self.player.class_id != "rogue":
            return ["Hide is a Rogue ability. Use 'skills' for your class abilities."]
        if not self.enemy:
            return ["Save hiding for a foe you need to evade."]
        if self.hidden:
            return ["You are already hidden; your next attack has Advantage."]
        if self.enemy_unaware and self.opening_hide_available:
            self.opening_hide_available = False
            roll, dice = self._stealth_roll()
            total, dc = roll + self.player.stealth_bonus, 20
            self.hidden = total >= dc
            lines = [f"Opening Hide: d20 [{dice}] {self.player.stealth_bonus:+d} = {total} vs DC {dc}. "
                     + ("You vanish into shadow; the foe remains unaware. 'attack' can deliver a Sneak Attack."
                        if self.hidden else "The foe catches your movement! You are revealed."),
                     "Your opening Hide attempt spends no action or bonus action."]
            if self.player.stealth_disadvantage:
                lines.insert(1, "Your armor hinders stealth: roll with Disadvantage.")
            if self.hidden:
                return [*lines, self.turn_status()]
            return [*lines, *self._roll_encounter_initiative(
                failed_hide=True, preserve_opening_budget=True)]
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
        roll, dice = self._stealth_roll()
        total = roll + self.player.stealth_bonus
        dc = 20
        self.hidden = total >= dc
        return [f"Stealth: d20 [{dice}] {self.player.stealth_bonus:+d} = {total} vs DC {dc}. "
                + ("You slip into shadow; your next attack has Advantage." if self.hidden else
                   "The foe tracks your movement; you remain visible."),
                *( ["Your armor hinders stealth: roll with Disadvantage."] if self.player.stealth_disadvantage else []),
                self.turn_status()]

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
                self.reveal_opening()
        if spell == "armor":
            self.player.mage_armor_active = True
            return [f"Mage Armor shimmers around you. AC {self.player.armor_class}; lasts until your next long rest."]
        if spell == "shield":
            self.shield_active = True
            return [f"A luminous Shield unfolds. AC {self.player.armor_class + 5} against the next enemy strike.", self.turn_status()]
        if spell in ("firebolt", "frost"):
            self.hidden = False
            dice = (2 if self.player.level >= 5 else 1, 10) if spell == "firebolt" else (3, 8)
            result = roll_attack(self.rng, self.player.spell_attack_bonus, enemy.armor_class, dice, 0)
            label = "Fire Bolt" if spell == "firebolt" else "Frost Lance"
            if result.hit:
                strength = ("grazes" if result.damage <= 5 else "strikes" if result.damage <= 10
                            else "slams into" if result.damage <= 15 else "engulfs")
                energy = "flame" if spell == "firebolt" else "razor-cold light"
                lines = [f"{label}: d20 [{'/'.join(map(str, result.rolls))}], total {result.total}. "
                         f"Your {energy} {strength} {enemy.name} for {damage_notation(result)} damage."
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
            self.hidden = False
            damage = roll_dice(self.rng, 3, 4) + 3
            lines = [f"Three Magic Missiles strike {enemy.name} for {format_damage_pool((3, 4), 3, damage)} force damage!"]
        else:
            self.hidden = False
            damage = roll_dice(self.rng, 8, 6)
            original_damage = damage
            save_roll = self.rng.randint(1, 20)
            total = save_roll + enemy.initiative_bonus
            saved = total >= self.player.spell_save_dc
            if saved:
                damage //= 2
            lines = [f"Fireball: {enemy.name} rolls Dexterity {total} vs DC {self.player.spell_save_dc}: "
                     f"{'success, half damage' if saved else 'failure'}. Flames deal "
                     f"{format_damage_pool((8, 6), 0, damage, original_total=original_damage)} damage!"]
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

    def inventory(self, page: str = "") -> list[str]:
        """Show carried equipment, its stable IDs, and the copies in use."""
        p = self.player
        lines = [f"Weapon: {p.weapon_name} | Armor: {p.armor_name} | AC {p.armor_class}",
                 f"Warding ring +{p.ward_bonus} | Vitality charm: {p.vitality_charm}",
                 f"Healing potions: {p.potions} | Ember stones: {p.ember_stones} | "
                 f"Mana draughts: {p.mana_draughts} | Gold: {p.gold}"]
        lines.extend(f"{slot.title()}: {item.name}" for slot, item in p.equipped_armor_slots.items())
        grouped = {}
        for item in p.equipment_inventory:
            group = grouped.setdefault(item.id, [item, 0, 0])
            group[1] += 1
            group[2] += int(p.is_equipped(item))
        entries = []
        for item, count, equipped in grouped.values():
            tag = " | equipped" if equipped else ""
            entries.append(f"{item.id}: {item.name} x{count} | {item.rarity}{tag} | sell {item.sale_value} gold each")
        entries.extend(f"{item.id}: {item.name} x{item.amount} | sell {item.value} gold each"
                       for item in p.treasure_inventory)
        try:
            page_number = int(page or "1")
        except (TypeError, ValueError):
            return ["Use 'inventory' or 'inventory <page number>'."]
        page_count = max(1, (len(entries) + 7) // 8)
        if not 1 <= page_number <= page_count:
            return [f"Inventory has pages 1–{page_count}. Use 'inventory <page number>'."]
        lines.append(f"Pack — page {page_number}/{page_count}")
        lines.extend(entries[(page_number - 1) * 8:page_number * 8])
        lines.extend(["Read details with 'examine <item id or name>'.",
                      "Equip in a safe room with 'equip <item id or name>'.",
                      "At Mira's shop, sell valuables and spare gear with 'sell <item id>' or 'sell all'. Equipped gear is kept.",
                      f"Collected notes: {len(self.journal)}. Type 'journal' to browse."])
        return lines

    def examine_item(self, query: str) -> list[str]:
        """Inspect owned items or Mira's stock without spending turns or dice."""
        query = " ".join(query.casefold().split())
        if query in ("foe", "enemy"):
            return self.examine_foe()
        if query.startswith("item "):
            query = query[5:]
        if not query:
            return ["Use 'examine <item id or name>'."]
        canonical = resolve_equipment_id(query)
        held = next((item for item in self.player.equipment_inventory if item.id == canonical), None)
        offered = next((item for item in stock(self.floor, self.player.class_id)
                        if item.id == (canonical or query) or item.name.casefold() == query), None)
        if held is not None or (self.in_shop and offered is not None and offered.equipment is not None):
            item = held if held is not None else offered.equipment
            lines = [f"Item: {item.name}", f"Slot: {item.slot} | Rarity: {item.rarity}",
                     f"Description: {item.description}"]
            if held is not None:
                lines.append("Equipped." if self.player.is_equipped(held) else "Carried in your pack.")
            if self.in_shop and offered is not None:
                lines.append(f"Price: {offered.price} gold | buy {offered.id}")
            lines.append(f"Spare-copy sell value: {item.sale_value} gold.")
            return lines
        valuable = next((item for item in self.player.treasure_inventory
                         if item.id == query or item.name.casefold() == query), None)
        if valuable is not None:
            return [f"Item: {valuable.name} x{valuable.amount}", f"Description: {valuable.description}",
                    f"Sell value: {valuable.value} gold each."]
        if offered is not None and (self.in_shop or
                (offered.kind == "potion" and self.player.potions) or
                (offered.kind == "ember" and self.player.ember_stones) or
                (offered.kind == "mana" and self.player.mana_draughts) or
                (offered.kind == "charm" and self.player.vitality_charm) or
                (offered.kind == "ward" and self.player.ward_bonus)):
            return [f"Item: {offered.name}", f"Description: {offered.description}",
                    *( [f"Price: {offered.price} gold | buy {offered.id}"] if self.in_shop else [])]
        return ["That item is not in your pack or the current shop. Use 'inventory' or a shop category for IDs."]

    def equip(self, item_id: str) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        if self.enemy:
            return ["Change equipment in a safe room or at Mira's shop, away from a living foe."]
        selected_id = resolve_equipment_id(item_id)
        item = next((owned for owned in self.player.equipment_inventory if owned.id == selected_id), None)
        if item is None:
            return ["You do not carry that equipment. Use 'inventory' for item IDs and names."]
        if not self.player.can_equip(item):
            return [f"Your class is not proficient with {item.name}. You can sell it to Mira."]
        if not self.player.equip_equipment(item):
            return ["You already have that equipment in use."]
        return [f"You equip {item.name}. AC {self.player.armor_class}; "
                f"weapon attack {self.player.attack_bonus:+d}.", f"Description: {item.description}"]

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
            return ["Mira buys valuables and spare equipment in the portal sanctuary. Visit her to sell treasure."]
        item_id = " ".join(item_id.casefold().split())
        normalized = resolve_equipment_id(item_id) or item_id
        selected = [item for item in self.player.treasure_inventory
                    if item_id == "all" or item.id == item_id or item.name.casefold() == item_id]
        gear = [item for item in self.player.sellable_equipment() if item_id == "all" or item.id == normalized]
        if not selected and not gear:
            return ["No matching valuables or spare gear. Equipped equipment is kept; use 'inventory' for item IDs."]
        value = sum(item.amount * item.value for item in selected) + sum(item.sale_value for item in gear)
        ids = {item.id for item in selected}
        self.player.treasure_inventory[:] = [item for item in self.player.treasure_inventory if item.id not in ids]
        sold_copies = {id(item) for item in gear}
        self.player.equipment_inventory[:] = [item for item in self.player.equipment_inventory if id(item) not in sold_copies]
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
            finds = list(loot.equipment)
            for kind, name, bonus in (("weapon", loot.weapon_name, loot.weapon_bonus),
                                      ("armor", loot.armor_name, loot.armor_bonus)):
                if name:
                    canonical = resolve_equipment_id(name)
                    if canonical:
                        base_id = max((key for key in EQUIPMENT if canonical == key or canonical.startswith(key + "_")), key=len)
                        suffix = canonical[len(base_id):].lstrip("_").split("_", 1)
                        affix = suffix[1] if len(suffix) > 1 and bonus else ""
                        if EQUIPMENT[base_id].kind != kind:
                            base_id = (DEFAULT_WEAPONS if kind == "weapon" else DEFAULT_ARMOR)[self.player.class_id]
                            affix = ""
                    else:
                        base_id = (DEFAULT_WEAPONS if kind == "weapon" else DEFAULT_ARMOR)[self.player.class_id]
                        affix = ""
                        if kind == "weapon" and "staff" in name.lower() and self.player.class_id == "wizard":
                            base_id = "arcane_staff"
                    finds.append(make_equipment(base_id, bonus, affix))
            for item in finds:
                equipped = self.player.collect_equipment(item)
                lines.append(f"You find {item.name} ({item.rarity}). Item id: {item.id}. {item.description}")
                if equipped:
                    lines.append("You equip this clear upgrade; your previous equipment stays in your pack.")
                else:
                    lines.append(f"You store it in your pack. Use 'equip {item.id}' to choose it, or sell spare gear to Mira.")
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
                *self.describe_room()]

    def sanctuary_menu(self) -> list[str]:
        if not self.in_shop:
            return ["Mira's sanctuary menu is available after using a guardian's portal."]
        leave = "Leave the dungeon" if self.floor == self.total_floors else "Descend to the next floor"
        return [f"Mira's sanctuary | Floor {self.floor} | Gold: {self.player.gold}",
                "1. Weapons — shop weapons", "2. Armor by slot — shop armor",
                "3. Supplies — shop supplies", "4. Inventory — inventory",
                "5. Sell spare items — sell all", f"6. {leave} — descend",
                "Choose 1–6, or use the commands shown. Type 'menu' to return."]

    def shop(self, category: str = "") -> list[str]:
        if not self.in_shop:
            return ["Visit the vendor through a cleared floor's portal first."]
        parts = category.split()
        if not parts or parts == ["menu"]:
            return self.sanctuary_menu()
        if parts == ["armor"]:
            return ["Armor — choose a slot:", "Boots — shop boots", "Gloves — shop gloves",
                    "Pants — shop pants", "Torso — shop torso", "Helmet — shop helmet",
                    "Type 'menu' to return to Mira's sanctuary menu."]
        if len(parts) > 2:
            return ["Use 'shop <category> [page]'. Armor categories: boots, gloves, pants, torso, helmet."]
        try:
            items = shop_items(self.floor, self.player.class_id, parts[0])
            page = int(parts[1]) if len(parts) == 2 else 1
        except (ValueError, TypeError):
            return ["Choose shop weapons, shop supplies, or shop boots/gloves/pants/torso/helmet, followed by an optional page number."]
        pages = max(1, (len(items) + 7) // 8)
        if not 1 <= page <= pages:
            return [f"This category has pages 1–{pages}. Use 'shop {parts[0]} <page>'."]
        return [f"Mira's {parts[0]} | Gold: {self.player.gold} | Page {page}/{pages}",
                *(f"{item.id}: {item.name} — {item.price} gold"
                  for item in items[(page - 1) * 8:page * 8]),
                "Use 'examine <item id or name>' for descriptions and effects.",
                "Buy with 'buy <item id or name>'. Type 'menu' to return.",
                *( [f"More items: shop {parts[0]} {page + 1}"] if page < pages else [])]

    def buy(self, item_id: str) -> list[str]:
        if not self.player.is_alive:
            return self.death_message()
        if not self.in_shop:
            return ["You can only buy items at the vendor."]
        requested = " ".join(item_id.casefold().split())
        item_id = requested
        if item_id in ("sword", "weapon", "armor"):
            item_id = preferred_item_id(self.floor, self.player.class_id,
                                        "armor" if item_id == "armor" else "weapon")
        else:
            item_id = resolve_equipment_id(item_id) or item_id
        item = next((item for item in stock(self.floor, self.player.class_id)
                     if item.id == item_id or item.name.casefold() == requested), None)
        if item is None:
            return ["Unknown item. Use 'shop' for item ids and prices."]
        p = self.player
        redundant = ((item.equipment is not None and any(
                         owned.base_id == item.equipment.base_id and owned.bonus >= item.equipment.bonus
                         for owned in p.equipment_inventory))
                     or (item.kind == "charm" and p.vitality_charm)
                     or (item.kind == "ward" and p.ward_bonus >= item.value))
        if redundant:
            return ["You already have this item or better gear. Your gold is unchanged."]
        if p.gold < item.price:
            return [f"You need {item.price} gold; you have {p.gold}."]
        p.gold -= item.price
        equipped = None
        if item.equipment is not None:
            equipped = p.collect_equipment(item.equipment)
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
        lines = [f"Bought {item.name} for {item.price} gold. Gold remaining: {p.gold}."]
        if item.equipment is not None:
            lines.append("You equip this clear upgrade; your old gear stays in your pack." if equipped else
                         f"Stored in your pack. Choose it with 'equip {item.equipment.id}' when ready.")
            lines.append(f"Description: {item.equipment.description}")
        return lines

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
        self.reveal_opening()
        self.hidden = False
        self.player.ember_stones -= 1
        damage = roll_dice(self.rng, 3, 6)
        enemy.take_damage(damage)
        lines = [f"Your Ember stone bursts for {format_damage_pool((3, 6), 0, damage)} magic damage!"]
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
                "position": list(self.position), "player": {
                    **asdict(self.player), "dead": not self.player.is_alive,
                    "armor_name": self.player.armor_name,
                    "combined_armor_bonus": self.player.combined_armor_bonus,
                    "effective_abilities": dict(self.player.effective_abilities),
                    "equipment_buffs": dict(self.player.equipment_buffs),
                    "armor_slots": {slot: {**asdict(item), "id": item.id, "name": item.name,
                                           "slot": item.slot, "buffs": dict(item.buffs)}
                                    for slot, item in self.player.equipped_armor_slots.items()},
                    "equipment_inventory": [
                        {**asdict(item), "id": item.id, "name": item.name, "kind": item.kind,
                         "slot": item.slot, "buffs": dict(item.buffs),
                         "rarity": item.rarity, "sale_value": item.sale_value,
                         "description": item.description, "equipped": self.player.is_equipped(item)}
                        for item in self.player.equipment_inventory],
                },
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
                    "foe_details": foe_details(self.enemy, self.player.class_id, weapon_mastery=self.player.weapon_mastery) if self.foe_examined and self.enemy else None,
                    "hidden": self.hidden, "vex": self.rogue_vex,
                    "sneak_attack_used": self.sneak_attack_used,
                    "shield_active": self.shield_active,
                    "uncanny_dodge_available": self.uncanny_dodge_available,
                    "scouting": dict(self.scouting_result) if self.scouting_result else None,
                    "enemy_unaware": self.enemy_unaware,
                    "opening_hide_available": self.opening_hide_available,
                },
                "turn": {"round": self.round_number, "actions": self.actions_remaining,
                         "bonus_action": self.bonus_action_available},
                "won": self.won, "over": self.over}
