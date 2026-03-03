"""GUI implementation for the ECHO application.

Contains the Tkinter-based UI, camera loop, gesture-driven menu and mode
interaction.  This module is imported by `main.py` so that `python main.py`
launches the desktop app immediately.
"""

import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
import mediapipe as mp
import time
import math

# mode implementations
from modes.assistive import run_assistive_mode
from modes.presentation import run_presentation_mode
from modes.communication import run_communication_mode
from modes.entertainment import run_entertainment_mode

# shared helpers -----------------------------------------------------------
HOLD_TIME = 1.0  # seconds
MODE_NAMES = {
    1: "ASSISTIVE MODE",
    2: "PRESENTATION MODE",
    3: "COMMUNICATION MODE",
    4: "ENTERTAINMENT MODE",
}


# small canvas subclass to draw a rounded rectangle with text
class ModeTile(tk.Canvas):
    CYAN   = "#00d4ff"
    GREEN  = "#4ade80"
    SHADOW = "#0a0a0a"

    def __init__(self, parent, text, finger_num=1, width=200, height=80, **kwargs):
        super().__init__(parent, width=width, height=height, highlightthickness=0, **kwargs)
        self.label_text = text.upper()
        self.finger_num = str(finger_num)
        self.radius = 18
        self.color = self.CYAN
        self._draw()

    def _rounded_rect(self, x1, y1, x2, y2, r, **kw):
        """Draw a rounded rectangle on the canvas."""
        self.create_arc((x1, y1, x1+2*r, y1+2*r), start=90,  extent=90,  **kw)
        self.create_arc((x2-2*r, y1, x2, y1+2*r),  start=0,   extent=90,  **kw)
        self.create_arc((x1, y2-2*r, x1+2*r, y2),  start=180, extent=90,  **kw)
        self.create_arc((x2-2*r, y2-2*r, x2, y2),  start=270, extent=90,  **kw)
        self.create_rectangle((x1+r, y1, x2-r, y2), **kw)
        self.create_rectangle((x1, y1+r, x2, y2-r), **kw)

    def _draw(self):
        self.delete("all")
        w = int(self["width"])
        h = int(self["height"])
        r = self.radius
        # shadow (offset 3px down-right)
        self._rounded_rect(3, 3, w, h, r, fill=self.SHADOW, outline=self.SHADOW)
        # main shape
        self._rounded_rect(0, 0, w-3, h-3, r, fill=self.color, outline=self.color)
        # main label
        self.create_text((w-3)//2, (h-3)//2 + 2, text=self.label_text,
                         fill="#1a1a2e", font=("Segoe UI", 13, "bold"))

    def set_color(self, color):
        self.color = color
        self._draw()


def distance(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def finger_extended(tip, base, palm):
    return distance(tip, palm) > distance(base, palm) + 0.02


def count_non_thumb_fingers(lm):
    palm = lm[0]
    count = 0
    fingers = [(8, 6), (12, 10), (16, 14), (20, 18)]
    for tip, base in fingers:
        if finger_extended(lm[tip], lm[base], palm):
            count += 1
    return count


class EchoApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ECHO – minimal desktop UI")
        self.geometry("1345x830")

        self.app_state = "menu"
        self.current_mode = None
        self.last_finger_count = None
        self.gesture_start_time = None

        self._build_ui()
        self._bind_keys()

        # camera + mediapipe
        self.cap = cv2.VideoCapture(0)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        self.mp_draw = mp.solutions.drawing_utils

        self.running = True
        self.after(10, self._update_frame)

    def _build_ui(self):
        # overall background
        self.configure(bg="#0d0d0d")

        # grid layout: left panel 1/3, separator, right panel 2/3
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=1, uniform="a")
        self.grid_columnconfigure(1, weight=0)         # thin separator
        self.grid_columnconfigure(2, weight=2, uniform="a")

        # left panel (slightly lighter dark)
        left_frame = tk.Frame(self, bg="#111118")
        left_frame.grid(row=0, column=0, sticky="nswe")

        # vertical separator
        sep = tk.Frame(self, bg="#00d4ff", width=2)
        sep.grid(row=0, column=1, sticky="ns")

        # right panel
        right_frame = tk.Frame(self, bg="#0d0d0d")
        right_frame.grid(row=0, column=2, sticky="nswe")

        # --- left panel contents ---
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(0, weight=1)   # spacer top
        left_frame.grid_rowconfigure(6, weight=1)   # spacer bottom

        # ECHO title
        title_lbl = tk.Label(
            left_frame, text="E C H O", fg="#00d4ff", bg="#111118",
            font=("Consolas", 22, "bold"),
        )
        title_lbl.grid(row=0, column=0, sticky="s", pady=(0, 10))

        # four tiles
        self.tiles = []
        names = ("Assistive", "Presentation", "Communication", "Entertainment")
        for idx, name in enumerate(names, start=1):
            tile = ModeTile(left_frame, name, finger_num=idx,
                            width=260, height=72, bg="#111118")
            tile.grid(row=idx, column=0, pady=14)
            self.tiles.append(tile)

        # hint text below tiles
        hint = tk.Label(
            left_frame, text="Hold 1\u20134 fingers to select",
            fg="#cccccc", bg="#111118", font=("Segoe UI", 8),
        )
        hint.grid(row=5, column=0, pady=(6, 0))

        # --- right panel (camera) ---
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        cam_border = tk.Frame(right_frame, bg="#1a1a2e", padx=6, pady=6)
        cam_border.grid(row=0, column=0, padx=20, pady=20, sticky="nswe")
        self.image_label = tk.Label(cam_border, bg="#0d0d0d")
        self.image_label.pack(expand=True, fill="both")

        # --- footer ---
        footer = tk.Frame(self, bg="#111118", height=32)
        footer.grid(row=1, column=0, columnspan=3, sticky="we")
        self.status_label = tk.Label(
            footer,
            text="ESC  go back        Q  quit",
            fg="#cccccc", bg="#111118",
            font=("Consolas", 9),
        )
        self.status_label.pack(pady=5)

    def _bind_keys(self):
        self.bind("<Escape>", lambda e: self._return_to_menu())
        self.bind("q", lambda e: self.quit())
        self.bind("Q", lambda e: self.quit())

    def _highlight_menu(self, finger_count=None):
        for idx, tile in enumerate(self.tiles, start=1):
            if (self.app_state == "active" and idx == self.current_mode) or \
               (self.app_state == "menu" and finger_count == idx):
                tile.set_color(ModeTile.GREEN)
            else:
                tile.set_color(ModeTile.CYAN)

    def _update_frame(self):
        if not self.running:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.after(30, self._update_frame)
            return

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self.hands.process(rgb)

        detected = None
        if result.multi_hand_landmarks:
            for hand in result.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(frame, hand, self.mp_hands.HAND_CONNECTIONS)
                detected = count_non_thumb_fingers(hand.landmark)
                if self.app_state == "active":
                    if self.current_mode == 1:
                        run_assistive_mode(hand)
                    elif self.current_mode == 2:
                        run_presentation_mode(hand)
                    elif self.current_mode == 3:
                        run_communication_mode(hand)
                    elif self.current_mode == 4:
                        run_entertainment_mode(hand, frame)

        if self.app_state == "menu":
            if detected in [1, 2, 3, 4]:
                if detected == self.last_finger_count:
                    if time.time() - self.gesture_start_time >= HOLD_TIME:
                        self.current_mode = detected
                        self.app_state = "active"
                        self.last_finger_count = None
                        self.gesture_start_time = None
                else:
                    self.last_finger_count = detected
                    self.gesture_start_time = time.time()
            else:
                self.last_finger_count = None
                self.gesture_start_time = None
            cv2.putText(
                frame,
                "Select mode by holding 1/2/3/4 fingers",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )
        elif self.app_state == "active":
            cv2.putText(
                frame,
                f"MODE: {MODE_NAMES.get(self.current_mode)}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                2,
            )

        self._highlight_menu(detected if self.app_state == "menu" else None)

        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(img)
        imgtk = ImageTk.PhotoImage(pil)
        self.image_label.imgtk = imgtk
        self.image_label.configure(image=imgtk)

        self.after(15, self._update_frame)

    def _return_to_menu(self):
        self.app_state = "menu"
        self.current_mode = None
        self.last_finger_count = None
        self.gesture_start_time = None

    def quit(self):
        self.running = False
        super().quit()


if __name__ == "__main__":
    app = EchoApp()
    app.mainloop()
