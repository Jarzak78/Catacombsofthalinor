"""Solo dungeon exploration with revised 2024 5e martial combat."""

from dataclasses import asdict
from actions import Action
from battle_flavor import hit_description, miss_description
from campaign import FLOORS, stock
from lore_notes import LoreNote
import random

from combat import AttackResult, roll_attack, roll_initiative, roll_dice
from dungeon import Dungeon
from player import Player
from room import Enemy, Room
from utils import health_bar


HELP = """Explore: north/south/east/west (n/s/e/w), look, map, loot
Lore: journal, read (latest note), read <journal number or note id>
Actions: attack (a), dodge (d), disengage (flee/f)
Bonus actions: potion (p), second wind (wind)
Turn control: end, action surge (surge; fighter level 2)
Rest: rest [dice] (1 hour), long rest (8 hours; entrance only)
Portal: portal (after guardian), shop, buy <item id>, descend
Magic: ember (consumes an action and an Ember stone)
Other: stats, inventory (i), help (h), quit (q)

Attacks: d20 + attack bonus vs Armor Class. Natural 1 critically fails for 1 self-damage; 20 crits.
A miss within 1–2 points of AC gets near-miss narration but deals no damage.
Hit descriptions reflect damage: glancing 1–5, solid 6–10, heavy 11–15, devastating 16+.
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
Collect treasure with 'loot'. Defeat each guardian, then use 'portal' to shop."""

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

    def __init__(self, name: str = "Adventurer", seed: int | None = None, floors: int = 5):
        if not 1 <= floors <= len(FLOORS):
            raise ValueError("Choose between 1 and 5 floors.")
        self.total_floors = floors
        self.floor = 1
        self.in_shop = False
        self.floor_cleared = False
        self.rng = random.Random(seed)
        self.dungeon = Dungeon(self.rng)
        self.player = Player(name=name)
        self.journal: list[LoreNote] = []
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
            f"Conquer {self.total_floors} dungeon floors; portals lead to a vendor between floors.",
            "Explore, gather supplies, and grow stronger before challenging him.",
            "Type 'help' for commands. Your starting pack holds three healing potions.",
            "Search with 'loot' for notes as well as treasure. Use 'journal' and 'read 1' to read them.",
            "Combat uses revised 2024 5e rules; type 'end' to finish your turn.",
            "", self.dungeon.lore.arrival, "", *self.describe_room(),
        ]

    def describe_room(self) -> list[str]:
        if self.in_shop:
            return ["The Lantern Between Worlds", "A portal brings you to Mira, the enchanted outfitter.",
                    "Use 'shop', 'buy <item id>', and 'descend' when ready.",
                    "Your journal is here too: use 'journal' and 'read <number>'."]
        lines = [f"Floor {self.floor}/{self.total_floors}: {self.dungeon.theme.name}",
                 self.room.name, self.room.description]
        if self.floor_cleared and self.position == self.dungeon.boss_position:
            lines.append("A glowing portal is open. Type 'portal' to visit the vendor.")
        enemy = self.enemy
        if enemy:
            lines.append(f"{enemy.name} blocks your way! HP {enemy.hp}/{enemy.max_hp}, "
                         f"AC {enemy.armor_class}.")
            lines.append("Attack, dodge, use a bonus action, or disengage; 'end' finishes your turn.")
        elif self.room.enemy:
            lines.append(f"The defeated {self.room.enemy.name} lies still.")
        if self.room.loot and not self.room.looted:
            lines.append("You spot unclaimed treasure. Use 'loot' when the room is safe.")
        if self.room.note and not self.room.note_collected:
            lines.append(f"You spot a document: {self.room.note.title}. Use 'loot' to collect it once the room is safe.")
        lines.append("Exits: " + ", ".join(self.room.exits))
        return lines

    def status(self) -> list[str]:
        player = self.player
        target = player.xp_to_next_level
        xp = f"{player.xp}/{target}" if target is not None else f"{player.xp} (maximum level)"
        lines = [
            f"Floor {self.floor}/{self.total_floors} | {player.name} | Fighter {player.level} | HP {player.hp}/{player.max_hp} "
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
        command = " ".join(raw.lower().split())
        if command.startswith(("go ", "move ")):
            command = command.split(" ", 1)[1]
        command = ALIASES.get(command, command)
        if command.startswith(("buy ", "rest ", "read ")):
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
            return ["This adventure is over. Run Main.py to begin another."]
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
        if command == "inventory":
            return [f"Weapon: {self.player.weapon_name} (magic bonus +{self.player.weapon_bonus})",
                    f"Armor: runic bonus +{self.player.armor_bonus} | Warding ring +{self.player.ward_bonus}",
                    f"Vitality charm: {self.player.vitality_charm} | Ember stones: {self.player.ember_stones}",
                    f"Healing potions: {self.player.potions} | Gold: {self.player.gold}",
                    f"Collected notes: {len(self.journal)}. Type 'journal' to browse."]
        if command == "quit":
            self.quit_requested = True
            return ["You leave the trial for another day. Your first dungeon can wait."]
        if not self.player.is_conscious:
            if command == "end":
                return self.end_turn()
            return ["You are unconscious and cannot act. Type 'end' to continue combat."]
        if command == "portal":
            return self.enter_portal()
        if command == "shop":
            return self.shop()
        if command.startswith("buy "):
            return self.buy(command[4:])
        if command == "descend":
            return self.descend()
        if self.in_shop:
            return ["You are shopping. Use 'buy <item id>' or 'descend' when ready."]
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
            "loot": self.collect_loot, "attack": self.attack, "ember": self.use_ember,
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
        if self.enemy is not None or not self.player.is_conscious:
            lines.extend(self.begin_turn())
        return lines

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
                return ["You are stable but unconscious. "
                        + ("The enemy is still dangerous; type 'end'." if self.enemy
                           else "The room is safe; type 'end' to recover and wake.")]
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
        if self.enemy is None or self.actions_remaining <= 0:
            return self.attack_once()
        lines = self.attack_once()
        if self.player.level >= 5 and self.enemy is not None and self.player.is_conscious:
            self.actions_remaining += 1
            lines.append("Extra Attack: your second longsword strike.")
            lines.extend(self.attack_once())
        return lines

    def attack_once(self) -> list[str]:
        enemy = self.enemy
        if enemy is None:
            return ["There is no enemy here to attack."]
        if self.actions_remaining <= 0:
            return ["Your action is spent. Use a bonus action, Action Surge, or 'end'."]
        self.actions_remaining -= 1
        result = roll_attack(self.rng, self.player.attack_bonus, enemy.armor_class,
                             (1, 8), self.player.damage_bonus)
        lines = [self.attack_text("You", enemy.name, result)]
        if result.critical_fail:
            self.player.take_damage(result.fumble_damage)
            lines.append(f"Your HP: {self.player.hp}/{self.player.max_hp}.")
            if self.player.dead:
                return [*lines, *self.death_message()]
            if not self.player.is_conscious:
                return [*lines, "You are unconscious at 0 HP. Type 'end' to continue."]
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
            description = miss_description(attacker, defender, result)
            return f"{attacker} {verb} {defender} ({roll})." + (f" {description}" if description else "")
        critical = " Critical hit!" if result.critical else ""
        verb = "hit" if attacker == "You" else "hits"
        description = hit_description(attacker, defender, result)
        return f"{attacker} {verb} {defender} ({roll}) for {result.damage} damage.{critical} {description}"

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
            self.floor_cleared = True
            lines.extend([self.dungeon.lore.revelation,
                          f"Floor {self.floor} cleared! A portal opens beside the fallen guardian.",
                          "Type 'portal' to visit Mira's shop, then 'descend' when ready."])
            if self.room.note and not self.room.note_collected:
                lines.append("A guardian document remains here. Use 'loot' before taking the portal.")
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
        if result.critical_fail:
            enemy.take_damage(result.fumble_damage)
            lines.append(f"{enemy.name}: {enemy.hp}/{enemy.max_hp} HP.")
            if not enemy.is_alive:
                lines.extend(self.defeat_enemy(enemy))
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
            if not self.player.dead and not self.player.is_conscious:
                if self.player.stable:
                    hours = self.rng.randint(1, 4)
                    self.elapsed_minutes += hours * 60
                    self.player.heal(1)
                    return [f"With the room safe, you recover for {hours} hour(s) and wake with 1 HP.",
                            *self.status()]
                self.elapsed_minutes += 0.1
                return self.begin_turn()
            return ["There is no combat turn to end. Explore or rest."]
        self.elapsed_minutes += 0.1
        lines = self.enemy_turn()
        if not self.player.dead and (self.enemy is not None or not self.player.is_conscious):
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
            if loot.weapon_name and self.player.equip_weapon(loot.weapon_name, loot.weapon_bonus):
                lines.append(f"You equip {loot.weapon_name} (+{loot.weapon_bonus} to attack and damage).")
        note = self.room.note
        if note is not None and not self.room.note_collected:
            self.room.note_collected = True
            if not any(entry.id == note.id for entry in self.journal):
                self.journal.append(note)
                lines.append(f"You collect '{note.title}' and add it to your journal.")
                lines.append(f"Type 'read {len(self.journal)}' to read it, or 'journal' to browse your notes.")
        return lines or ["There are no unclaimed notes or treasure here."]

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
                  for item in stock(self.floor)),
                "Buy with 'buy <item id>'; purchases equip automatically. Type 'descend' when done."]

    def buy(self, item_id: str) -> list[str]:
        if not self.in_shop:
            return ["You can only buy items at the vendor."]
        item = next((item for item in stock(self.floor) if item.id == item_id), None)
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
        return [f"Bought {item.name} for {item.price} gold. Gold remaining: {p.gold}."]

    def descend(self) -> list[str]:
        if not self.in_shop:
            return ["Use the guardian's portal and finish shopping before descending."]
        if self.floor == self.total_floors:
            self.won = True
            return ["Mira's final portal returns you to daylight.",
                    "Your first dungeon is conquered! Every guardian has fallen.", *self.status()]
        self.floor += 1
        self.dungeon = Dungeon(self.rng, floor=self.floor)
        self.position = self.dungeon.start
        self.previous_position = None
        self.room.visited = True
        self.floor_cleared = False
        self.in_shop = False
        self.actions_remaining = 1
        self.bonus_action_available = True
        self.dodging = self.enemy_sapped = False
        self.round_number = 0
        return [f"The portal carries you deeper, to floor {self.floor}.",
                self.dungeon.lore.arrival, "", *self.describe_room()]

    def use_ember(self) -> list[str]:
        enemy = self.enemy
        if enemy is None:
            return ["Save Ember stones for combat."]
        if self.actions_remaining <= 0:
            return ["Your action is spent."]
        if self.player.ember_stones <= 0:
            return ["You have no Ember stones. Buy them from Mira."]
        self.actions_remaining -= 1
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
                "position": list(self.position), "player": asdict(self.player),
                "journal": [asdict(note) for note in self.journal],
                "armor_class": self.player.armor_class, "attack_bonus": self.player.attack_bonus,
                "rooms": rooms, "portal_open": self.floor_cleared,
                "portal_position": list(self.dungeon.boss_position) if self.floor_cleared else None,
                "shop": [asdict(item) for item in stock(self.floor)] if self.in_shop else [],
                "turn": {"round": self.round_number, "actions": self.actions_remaining,
                         "bonus_action": self.bonus_action_available},
                "won": self.won, "over": self.over}
