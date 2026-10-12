"""A small native desktop adapter for the existing dungeon engine."""

import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import traceback

from character_creation import CLASS_NAMES, CLASS_SUMMARIES
from entrance_art import draw_entrance
from ui_controller import DesktopSession, minimap_data


BG = "#10171f"
PANEL = "#1a2530"
INK = "#dce2e7"
MUTED = "#a2b2c0"
GOLD = "#dfb565"
MONO = ("Consolas", 12)


class DungeonWindow:
    """Widgets display snapshots; commands and rolls belong to the controller."""

    def __init__(self, root: tk.Tk, session: DesktopSession | None = None):
        self.root = root
        self.session = session or DesktopSession()
        self.seed, self.floors = self.session.seed, self.session.floors
        self.screen = "title"
        self.history: list[str] = []
        self.history_index = 0
        self.map_state: dict = {}
        root.title("Catacombs of Thalinor")
        root.geometry("1180x820")
        root.minsize(960, 740)
        root.configure(bg=BG)
        self._styles()
        self.body = ttk.Frame(root, padding=24)
        self.body.pack(fill="both", expand=True)
        self.body.columnconfigure(0, weight=1)
        self.body.rowconfigure(0, weight=1)
        self.frames: dict[str, ttk.Frame] = {}
        for scene in ("title", "creation", "dungeon"):
            frame = ttk.Frame(self.body)
            frame.grid(row=0, column=0, sticky="nsew")
            self.frames[scene] = frame
        self._title_screen()
        self._creation_screen()
        self._dungeon_screen()
        self.show_screen("title")

    def _styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=INK, font=("Segoe UI", 11))
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=INK)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Heading.TLabel", font=("Segoe UI", 25, "bold"), foreground=GOLD)
        style.configure("Section.TLabel", font=("Segoe UI", 13, "bold"), foreground=GOLD)
        style.configure("TButton", background="#283b4c", foreground=INK, padding=(12, 8))
        style.map("TButton", background=[("active", "#3c566d"), ("disabled", "#1d2731")],
                  foreground=[("disabled", "#687783")])
        style.configure("Accent.TButton", background="#b78a3d", foreground="#10171f",
                        font=("Segoe UI", 12, "bold"), padding=(20, 12))
        style.map("Accent.TButton", background=[("active", "#dfb565"), ("disabled", "#28313a")],
                  foreground=[("disabled", "#687783")])
        style.configure("Compact.TButton", padding=(8, 3), font=("Segoe UI", 10))
        style.configure("TRadiobutton", background=BG, foreground=INK, padding=6)
        style.map("TRadiobutton", background=[("active", BG)], foreground=[("disabled", "#687783")])
        style.configure("TEntry", fieldbackground="#0c1219", foreground=INK, padding=8)
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                        foreground=INK, rowheight=35, font=MONO)
        style.configure("Treeview.Heading", background="#283b4c", foreground=GOLD,
                        font=("Segoe UI", 11, "bold"))
        style.map("Treeview", background=[("selected", "#354b60")])

    def show_screen(self, scene: str) -> None:
        self.screen = scene
        self.frames[scene].tkraise()

    def _title_screen(self) -> None:
        frame = self.frames["title"]
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)
        ttk.Label(frame, text="CATACOMBS OF THALINOR", style="Heading.TLabel",
                  anchor="center").grid(row=0, column=0, pady=(12, 8), sticky="ew")
        ttk.Label(frame, text="Beneath the stones, a king still waits.", style="Muted.TLabel",
                  anchor="center").grid(row=1, column=0, pady=(0, 20), sticky="ew")
        self.entrance_canvas = tk.Canvas(frame, bg=BG, highlightthickness=0, height=400)
        self.entrance_canvas.grid(row=2, column=0, sticky="nsew")
        self.entrance_canvas.bind("<Configure>", lambda event: draw_entrance(
            self.entrance_canvas, event.width, event.height))
        ttk.Label(frame, text="Choose an adventurer. Descend into five forgotten depths.",
                  style="Muted.TLabel", anchor="center").grid(row=3, column=0, pady=(20, 12), sticky="ew")
        self.creation_button = ttk.Button(frame, text="Character Creation", style="Accent.TButton",
                                          command=self.open_creation)
        self.creation_button.grid(row=4, column=0, pady=(0, 14))
        ttk.Button(frame, text="Exit", command=self.root.destroy).grid(row=5, column=0, pady=(0, 12))

    def _creation_screen(self) -> None:
        frame = self.frames["creation"]
        frame.columnconfigure(0, weight=1)
        ttk.Label(frame, text="CHARACTER CREATION", style="Heading.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text="Choose your class, roll your abilities, and prepare for the descent.",
                  style="Muted.TLabel").grid(row=1, column=0, pady=(4, 18), sticky="w")
        name_row = ttk.Frame(frame)
        name_row.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(name_row, text="Adventurer's name").pack(side="left", padx=(0, 12))
        self.name_var = tk.StringVar(value=self.session.name)
        self.name_entry = ttk.Entry(name_row, textvariable=self.name_var, width=30)
        self.name_entry.pack(side="left")
        choices = ttk.Frame(frame)
        choices.grid(row=3, column=0, sticky="ew", pady=(0, 18))
        self.class_var = tk.StringVar(value=self.session.class_id)
        self.class_buttons = {}
        for col, class_id in enumerate(CLASS_NAMES):
            choices.columnconfigure(col, weight=1, uniform="class")
            card = ttk.Frame(choices, padding=(8, 8))
            card.grid(row=0, column=col, sticky="nsew", padx=(0, 14) if col < 2 else 0)
            button = ttk.Radiobutton(card, text=CLASS_NAMES[class_id], variable=self.class_var,
                                     value=class_id, command=self.select_class)
            button.pack(anchor="w")
            self.class_buttons[class_id] = button
            description = ttk.Label(card, text=CLASS_SUMMARIES[class_id], wraplength=300,
                                    style="Muted.TLabel", justify="left")
            description.pack(anchor="w", padx=6, pady=(4, 0))
            card.bind("<Configure>", lambda event, label=description:
                      label.configure(wraplength=max(180, event.width - 32)))
        scores = ttk.Frame(frame)
        scores.grid(row=4, column=0, sticky="nsew")
        scores.columnconfigure(0, weight=1)
        scores.columnconfigure(1, minsize=260)
        frame.rowconfigure(4, weight=1)
        self.score_table = ttk.Treeview(scores, columns=("stat", "dice", "drop", "total"),
                                        show="headings", height=6, selectmode="none")
        for column, title, width in (("stat", "Ability", 155), ("dice", "4d6", 200),
                                     ("drop", "Dropped", 100), ("total", "Score", 80)):
            self.score_table.heading(column, text=title)
            self.score_table.column(column, width=width, anchor="center", stretch=column == "dice")
        self.score_table.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        summary = ttk.Frame(scores, padding=14, style="Card.TFrame")
        summary.grid(row=0, column=1, sticky="nsew")
        self.preview_var = tk.StringVar()
        ttk.Label(summary, textvariable=self.preview_var, background=PANEL, justify="left",
                  wraplength=225, font=("Segoe UI", 12)).pack(anchor="nw")
        ttk.Label(frame, text="Each score uses 4d6, dropping one lowest die. You may replace all six scores once.",
                  style="Muted.TLabel", wraplength=1000).grid(row=5, column=0, pady=(12, 8), sticky="w")
        self.creation_message = tk.StringVar(value="Select a class, then click Roll Stats.")
        ttk.Label(frame, textvariable=self.creation_message, foreground=GOLD,
                  wraplength=1040).grid(row=6, column=0, pady=(0, 12), sticky="w")
        controls = ttk.Frame(frame)
        controls.grid(row=7, column=0, sticky="ew")
        self.back_button = ttk.Button(controls, text="Back to Title", command=self.back_to_title)
        self.back_button.pack(side="left")
        self.roll_button = ttk.Button(controls, text="Roll Stats", command=self.roll_stats)
        self.roll_button.pack(side="left", padx=(12, 8))
        self.reroll_button = ttk.Button(controls, text="Reroll (1 left)", command=self.reroll_stats)
        self.reroll_button.pack(side="left", padx=(0, 8))
        self.accept_button = ttk.Button(controls, text="Create Character", command=self.accept_character)
        self.accept_button.pack(side="left")
        self.enter_button = ttk.Button(controls, text="Enter the Dungeon", style="Accent.TButton",
                                       command=self.enter_dungeon)
        self.enter_button.pack(side="right")
        self.refresh_creation()

    def _dungeon_screen(self) -> None:
        frame = self.frames["dungeon"]
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)
        ttk.Label(frame, text="CATACOMBS OF THALINOR", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.status_var = tk.StringVar()
        ttk.Label(frame, textvariable=self.status_var, style="Muted.TLabel", wraplength=1080).grid(
            row=1, column=0, sticky="ew", pady=(6, 14))
        play = ttk.Frame(frame)
        play.grid(row=2, column=0, sticky="nsew")
        play.columnconfigure(0, weight=1)
        play.columnconfigure(1, minsize=270)
        play.rowconfigure(0, weight=1)
        left = ttk.Frame(play)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)
        self.terminal = scrolledtext.ScrolledText(left, bg="#080e15", fg=INK,
            insertbackground=GOLD, font=MONO, wrap="word", relief="flat", borderwidth=0,
            padx=14, pady=12, state="disabled", width=66, height=25)
        self.terminal.grid(row=0, column=0, sticky="nsew")
        self.terminal.tag_configure("command", foreground=GOLD)
        self.terminal.tag_configure("notice", foreground="#90b9d6")
        input_row = ttk.Frame(left)
        input_row.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        input_row.columnconfigure(1, weight=1)
        ttk.Label(input_row, text=">").grid(row=0, column=0, padx=(0, 8))
        self.command_var = tk.StringVar()
        self.command_entry = ttk.Entry(input_row, textvariable=self.command_var, font=MONO)
        self.command_entry.grid(row=0, column=1, sticky="ew")
        self.command_entry.bind("<Return>", lambda _event: self.send_command())
        self.command_entry.bind("<Up>", lambda _event: self.recall_command(-1))
        self.command_entry.bind("<Down>", lambda _event: self.recall_command(1))
        self.send_button = ttk.Button(input_row, text="Send", command=self.send_command)
        self.send_button.grid(row=0, column=2, padx=(10, 0))
        ttk.Label(left, text="Type a command and press Enter. 'help' lists commands; 'skills' explains your abilities.",
                  style="Muted.TLabel", wraplength=760).grid(row=2, column=0, sticky="w", pady=(8, 0))
        right = ttk.Frame(play)
        right.grid(row=0, column=1, sticky="nsew")
        ttk.Label(right, text="MINIMAP", style="Section.TLabel").pack(anchor="w")
        self.map_label = tk.StringVar()
        ttk.Label(right, textvariable=self.map_label, style="Muted.TLabel", wraplength=255).pack(anchor="w", pady=(4, 8))
        self.map_canvas = tk.Canvas(right, width=260, height=144, bg="#0c141d",
                                    highlightthickness=1, highlightbackground="#34495a")
        self.map_canvas.pack(fill="x")
        self.map_canvas.bind("<Configure>", lambda _event: self.draw_map())
        ttk.Label(right, text="@ You   ? Unexplored   E Foe\nB Guardian   $ Loot   N Note", font=("Consolas", 10),
                  style="Muted.TLabel").pack(anchor="w", pady=(6, 8))
        ttk.Label(right, text="MOVE", style="Section.TLabel").pack(anchor="w")
        movement = ttk.Frame(right)
        movement.pack(fill="x", pady=(4, 8))
        self.movement_buttons = {}
        for direction, row, col in (("north", 0, 1), ("west", 1, 0), ("east", 1, 2), ("south", 2, 1)):
            button = ttk.Button(movement, text=direction.title(), width=6, style="Compact.TButton",
                                command=lambda d=direction: self.send_command(d))
            button.grid(row=row, column=col, padx=1, pady=1)
            self.movement_buttons[direction] = button
        ttk.Label(right, text="ACTIONS", style="Section.TLabel").pack(anchor="w")
        actions = ttk.Frame(right)
        actions.pack(fill="x", pady=(4, 6))
        self.action_buttons = {}
        for index, (title, command) in enumerate((
                ("Look", "look"), ("Loot", "loot"), ("Examine", "examine"), ("Inventory", "inventory"),
                ("Attack", "attack"), ("Dodge", "dodge"), ("Potion", "potion"), ("End Turn", "end"))):
            button = ttk.Button(actions, text=title, width=8, style="Compact.TButton",
                                command=lambda c=command: self.send_command(c))
            button.grid(row=index // 3, column=index % 3, padx=2, pady=2, sticky="ew")
            self.action_buttons[command] = button
        self.class_action = ttk.Button(right, text="Class Ability", style="Compact.TButton", command=self.use_class_ability)
        self.class_action.pack(fill="x", pady=(0, 4))
        self.spell_menu = tk.Menu(self.root, tearoff=False, bg=PANEL, fg=INK,
                                  activebackground="#354b60", activeforeground=GOLD)
        for spell in ("firebolt", "missile", "armor", "shield", "frost", "fireball"):
            self.spell_menu.add_command(label=f"Cast {spell.title()}", command=lambda s=spell: self.send_command("cast " + s))
        self.restart_button = ttk.Button(right, text="New Adventure", style="Compact.TButton",
                                         command=self.new_adventure, state="disabled")
        self.restart_button.pack(fill="x", pady=(4, 0))

    def open_creation(self) -> None:
        self.session.begin_creation()
        self.show_screen("creation")
        self.refresh_creation()

    def back_to_title(self) -> None:
        self.session.show_title()
        self.show_screen("title")

    def select_class(self) -> None:
        self.session.choose_class(self.class_var.get())
        self.refresh_creation()

    def roll_stats(self) -> None:
        self.session.roll_stats()
        self.creation_message.set("Scores rolled. Accept this set or use your one reroll to replace all six.")
        self.refresh_creation()

    def reroll_stats(self) -> None:
        self.session.reroll_stats()
        self.creation_message.set("Your one reroll is used. Accept these scores or leave character creation.")
        self.refresh_creation()

    def accept_character(self) -> None:
        self.session.set_name(self.name_var.get())
        player = self.session.accept_character()
        self.name_var.set(player.name)
        self.creation_message.set(f"{player.name}, the {CLASS_NAMES[player.class_id]}, is ready. Enter the dungeon when you are ready.")
        self.refresh_creation()

    def refresh_creation(self) -> None:
        state = self.session.get_state()
        self.score_table.delete(*self.score_table.get_children())
        if state["rolls"]:
            for roll in state["rolls"]:
                self.score_table.insert("", "end", values=(roll["stat"].title(),
                    "  ".join(map(str, roll["dice"])), roll["dropped"], roll["total"]))
        else:
            for stat in ("Strength", "Dexterity", "Intelligence", "Constitution", "Wisdom", "Charisma"):
                self.score_table.insert("", "end", values=(stat, "—", "—", "—"))
        preview = state["preview"]
        if preview:
            text = (f"{preview['class_name']}\n\nStarting HP: {preview['max_hp']}\nArmor Class: {preview['armor_class']}\n"
                    f"Weapon attack: {preview['attack_bonus']:+d}\n{preview['weapon_name']}\n\n3 healing potions")
            if preview["spell_attack_bonus"] is not None:
                text += f"\nSpell attack: {preview['spell_attack_bonus']:+d}\nSpell save DC: {preview['spell_save_dc']}"
            self.preview_var.set(text)
        else:
            self.preview_var.set("Your adventurer\n\nRoll your abilities to see starting health, armor, and attacks.")
        accepted = state["accepted"]
        self.roll_button.configure(state="disabled" if state["rolls"] or accepted else "normal")
        self.reroll_button.configure(state="normal" if state["reroll_available"] else "disabled",
                                    text="Reroll (used)" if state["reroll_used"] else "Reroll (1 left)")
        self.accept_button.configure(state="normal" if state["rolls"] and not accepted else "disabled")
        self.enter_button.configure(state="normal" if accepted else "disabled")
        self.name_entry.configure(state="disabled" if accepted else "normal")
        for button in self.class_buttons.values():
            button.configure(state="disabled" if accepted else "normal")

    def enter_dungeon(self) -> None:
        messages = self.session.enter_dungeon()
        self.show_screen("dungeon")
        self.append_messages(messages[1:])
        self.refresh_dungeon()
        self.command_entry.focus_set()

    def append_messages(self, lines: list[str], tag: str = "") -> None:
        self.terminal.configure(state="normal")
        self.terminal.insert("end", "\n".join(lines) + "\n\n", tag)
        self.terminal.configure(state="disabled")
        self.terminal.see("end")

    def send_command(self, command: str | None = None) -> None:
        raw = self.command_var.get() if command is None else command
        raw = raw.strip()
        if not raw:
            return
        if command is None:
            self.command_var.set("")
        self.history.append(raw)
        self.history_index = len(self.history)
        self.append_messages(["> " + raw], "command")
        self.append_messages(self.session.submit_command(raw))
        self.refresh_dungeon()
        self.command_entry.focus_set()

    def recall_command(self, delta: int) -> str:
        self.history_index = max(0, min(len(self.history), self.history_index + delta))
        self.command_var.set(self.history[self.history_index] if self.history_index < len(self.history) else "")
        self.command_entry.icursor("end")
        return "break"

    def refresh_dungeon(self) -> None:
        state = self.session.get_state()
        p = state["player"]
        self.status_var.set(f"{p['name']} · {state['class_name']} {p['level']} · Floor {state['floor']}/{state['total_floors']}"
                            f" · HP {p['hp']}/{p['max_hp']} · AC {state['armor_class']} · Gold {p['gold']}"
                            + (" · Adventure ended" if state["over"] else ""))
        self.map_state = minimap_data(state)
        self.map_label.set(self.map_state["label"])
        self.draw_map()
        ability = {"fighter": "Second Wind", "rogue": "Hide", "wizard": "Spells"}[p["class_id"]]
        self.class_action.configure(text=ability)
        self.restart_button.configure(state="normal" if state["over"] else "disabled")
        current = next((room for room in state["rooms"] if room["position"] == state["position"]), {})
        for direction, button in self.movement_buttons.items():
            button.configure(state="normal" if state["scene"] == "dungeon" and not state["over"]
                             and direction in current.get("exits", {}) else "disabled")

    def draw_map(self) -> None:
        self.map_canvas.delete("all")
        data = self.map_state
        if not data:
            return
        w = max(260, self.map_canvas.winfo_width())
        if not data["visible"]:
            self.map_canvas.create_oval(w / 2 - 34, 40, w / 2 + 34, 108, outline=GOLD, width=3)
            self.map_canvas.create_text(w / 2, 132, text="Vendor sanctuary", fill=INK, font=("Segoe UI", 11))
            return
        step_x = (w - 54) / max(1, data["width"] - 1)
        step_y = 48
        def center(x, y):
            return 27 + x * step_x, 29 + y * step_y
        for edge in data["edges"]:
            self.map_canvas.create_line(*center(*edge["start"]), *center(*edge["end"]), fill="#536779", width=2)
        colors = {"@": GOLD, "?": "#172431", "E": "#914a44", "B": "#914a44",
                  "$": "#497b65", "N": "#526d9b", ".": "#364b5b"}
        for node in data["nodes"]:
            x, y = center(node["x"], node["y"])
            self.map_canvas.create_rectangle(x - 13, y - 13, x + 13, y + 13,
                fill=colors[node["marker"]], outline="#5c7184" if node["visited"] else "#283a4b")
            self.map_canvas.create_text(x, y, text=node["marker"], fill=BG if node["marker"] == "@" else INK,
                                         font=("Consolas", 12, "bold"))

    def use_class_ability(self) -> None:
        class_id = self.session.game.player.class_id
        if class_id == "wizard":
            try:
                self.spell_menu.tk_popup(self.class_action.winfo_rootx(), self.class_action.winfo_rooty())
            finally:
                self.spell_menu.grab_release()
        else:
            self.send_command("wind" if class_id == "fighter" else "hide")

    def new_adventure(self) -> None:
        if self.session.game is None or not self.session.game.over:
            return
        self.session = DesktopSession(seed=self.seed, floors=self.floors)
        self.name_var.set(self.session.name)
        self.class_var.set(self.session.class_id)
        self.creation_message.set("Select a class, then click Roll Stats.")
        self.history.clear()
        self.history_index = 0
        self.command_var.set("")
        self.terminal.configure(state="normal")
        self.terminal.delete("1.0", "end")
        self.terminal.configure(state="disabled")
        self.refresh_creation()
        self.show_screen("title")


def run_gui(name: str = "Adventurer", seed: int | None = None, floors: int = 5) -> None:
    root = tk.Tk()
    def show_error(_kind, error, _trace):
        messagebox.showerror("Game error", str(error), parent=root)
    root.report_callback_exception = show_error
    DungeonWindow(root, DesktopSession(name=name, seed=seed, floors=floors))
    root.mainloop()


def run_gui_smoke(report_path: Path, name: str = "Adventurer", seed: int | None = None,
                  floors: int = 5) -> None:
    """Drive real widgets in an actual Tk window, including packaged Windows."""
    root = None
    checks = []
    report = {"success": False, "checks": checks}
    errors = []
    try:
        root = tk.Tk()
        root.report_callback_exception = lambda kind, error, trace: errors.append(str(error))
        app = DungeonWindow(root, DesktopSession(name=name, seed=seed, floors=floors))
        root.update()
        assert app.screen == "title" and app.entrance_canvas.find_all()
        checks.append("title_screen")
        app.creation_button.invoke()
        root.update()
        assert app.screen == "creation" and app.session.rolls is None
        assert app.enter_button.instate(["disabled"])
        checks.append("character_creation")
        for class_id in CLASS_NAMES:
            app.class_buttons[class_id].invoke()
            assert app.session.class_id == class_id
        checks.append("class_choice")
        app.roll_button.invoke()
        root.update()
        assert len(app.session.rolls) == 6 and len(app.score_table.get_children()) == 6
        for roll in app.session.rolls:
            assert roll.dropped == min(roll.dice) and roll.total == sum(roll.dice) - min(roll.dice)
        checks.append("4d6_drop_lowest")
        app.reroll_button.invoke()
        rng_after = app.session.stat_rng.getstate()
        rolls_after = app.session.rolls
        assert app.reroll_button.instate(["disabled"])
        app.reroll_button.invoke()
        app.back_button.invoke()
        app.creation_button.invoke()
        assert app.reroll_button.instate(["disabled"]) and app.roll_button.instate(["disabled"])
        assert app.session.rolls == rolls_after and app.session.stat_rng.getstate() == rng_after
        checks.append("one_reroll")
        app.accept_button.invoke()
        root.update()
        assert app.enter_button.instate(["!disabled"]) and app.name_entry.instate(["disabled"])
        app.enter_button.invoke()
        root.update()
        assert app.screen == "dungeon" and app.session.game is not None
        assert "Forgotten Catacombs" in app.terminal.get("1.0", "end")
        checks.append("enter_dungeon")
        before = app.session.game.get_state()
        app.command_var.set("look")
        app.send_button.invoke()
        root.update()
        assert "> look" in app.terminal.get("1.0", "end") and app.session.game.get_state() == before
        checks.append("command_submission")
        initial_map = app.map_state
        assert sum(node["marker"] == "?" for node in initial_map["nodes"]) == 11
        assert sum(node["marker"] == "@" for node in initial_map["nodes"]) == 1
        assert app.map_canvas.find_all()
        direction = next(iter(app.session.game.room.exits))
        app.movement_buttons[direction].invoke()
        root.update()
        assert sum(node["visited"] for node in app.map_state["nodes"]) == 2
        assert app.map_state == minimap_data(app.session.game.get_state())
        checks.append("minimap")
        root.geometry("960x740")
        root.update()
        for widget in (app.command_entry, app.send_button, app.class_action, app.restart_button):
            assert widget.winfo_height() > 1
            assert widget.winfo_rooty() + widget.winfo_height() <= root.winfo_rooty() + root.winfo_height(), "A control is cut off at minimum window size."
        checks.append("responsive_layout")
        # A real enemy strike must end the run and enable a clean restart.
        from room import Enemy
        class FatalRolls:
            def __init__(self):
                self.calls = []
            def randint(self, low, high):
                self.calls.append((low, high))
                return 20 if high == 20 else 1
        game = app.session.game
        assert game.player.is_alive
        game.player.take_damage(game.player.hp - 1)
        game.room.enemy = Enemy("Practice guardian", 20, 20, 12, 3, (1, 6), 1, 50, 3)
        game.clear_encounter()
        game.dodging = game.enemy_sapped = False
        game.rng = FatalRolls()
        app.action_buttons["end"].invoke()
        root.update()
        assert game.over and game.player.dead and game.player.hp == 0
        assert game.rng.calls == [(1, 20), (1, 6), (1, 6)]
        assert "You die in the catacombs at 0 HP" in app.terminal.get("1.0", "end")
        assert "Death save:" not in app.terminal.get("1.0", "end")
        assert app.restart_button.instate(["!disabled"])
        checks.append("instant_death")
        dead_state = game.get_state()
        app.action_buttons["potion"].invoke()
        root.update()
        assert game.get_state() == dead_state and len(game.rng.calls) == 3
        checks.append("post_death_actions")
        app.restart_button.invoke()
        root.update()
        assert app.screen == "title" and app.session.game is None and app.session.rolls is None
        assert not app.history and not app.terminal.get("1.0", "end").strip()
        checks.append("new_adventure")
        assert not errors, errors
        report["success"] = True
    except Exception as error:
        report.update(error=str(error), traceback=traceback.format_exc())
    finally:
        if root is not None:
            root.destroy()
        Path(report_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
