import math
import time
import numpy as np
import pyautogui
import cv2
from pycaw.pycaw import AudioUtilities


# ================= AUDIO SETUP =================

devices = AudioUtilities.GetSpeakers()
volume = devices.EndpointVolume

minVol, maxVol = volume.GetVolumeRange()[:2]

# ================= STATE VARIABLES =================

DIST_THRESHOLD = 0.02

# PLAY/PAUSE STATE
palm_active = False
last_play_pause_time = 0
PLAY_PAUSE_COOLDOWN = 0.6


# ================= HELPER FUNCTIONS =================

def distance(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def finger_extended(tip, base, palm):
    return distance(tip, palm) > distance(base, palm) + DIST_THRESHOLD


# ================= ENTERTAINMENT MODE =================

def run_entertainment_mode(hand_landmarks, frame):
    global palm_active, last_play_pause_time

    lm = hand_landmarks.landmark
    current_time = time.time()

    palm = lm[0]

    # Detect finger states
    index_up = finger_extended(lm[8], lm[6], palm)
    middle_up = finger_extended(lm[12], lm[10], palm)
    ring_up = finger_extended(lm[16], lm[14], palm)
    little_up = finger_extended(lm[20], lm[18], palm)

    thumb_tip = lm[4]
    index_tip = lm[8]

    pinch_distance = distance(thumb_tip, index_tip)

    # ================= VOLUME CONTROL =================
    # Only index + thumb active, others curled

    volume_gesture = (
        index_up and
        not middle_up and
        not ring_up and
        not little_up
    )

    PINCH_CLOSE = 0.035   # pinch = decrease
    PINCH_OPEN = 0.07     # hold apart = increase
    STEP = 1.5

    if volume_gesture:

        current_vol = volume.GetMasterVolumeLevel()

        # 🤏 PINCH = decrease continuously
        if pinch_distance < PINCH_CLOSE:
            new_vol = current_vol - STEP

        # 🤏 HOLD APART = increase continuously
        elif pinch_distance > PINCH_OPEN:
            new_vol = current_vol + STEP

        else:
            new_vol = current_vol

        new_vol = max(minVol, min(maxVol, new_vol))
        volume.SetMasterVolumeLevel(new_vol, None)


    # ================= PLAY / PAUSE (FULL OPEN PALM) =================

    open_palm = (
        index_up and
        middle_up and
        ring_up and
        little_up
    )

    if (
        open_palm and
        not palm_active and
        current_time - last_play_pause_time > PLAY_PAUSE_COOLDOWN
    ):
        pyautogui.press("space")
        palm_active = True
        last_play_pause_time = current_time

    if not open_palm:
        palm_active = False


    # ================= VISUAL AUDIO BAR =================

    current_vol = volume.GetMasterVolumeLevel()

    vol_percent = int(
        (current_vol - minVol) / (maxVol - minVol) * 100
    )

    h, w, _ = frame.shape

    bar_x = w - 80
    bar_y = 100
    bar_height = 300
    bar_width = 30

    cv2.rectangle(
        frame,
        (bar_x, bar_y),
        (bar_x + bar_width, bar_y + bar_height),
        (100, 100, 100),
        2
    )

    filled_height = int(bar_height * vol_percent / 100)

    cv2.rectangle(
        frame,
        (bar_x, bar_y + bar_height - filled_height),
        (bar_x + bar_width, bar_y + bar_height),
        (0, 255, 0),
        -1
    )

    cv2.putText(
        frame,
        f"{vol_percent}%",
        (bar_x - 20, bar_y - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 255, 0),
        2
    )