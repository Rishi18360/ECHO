import pyautogui
import math
import time
import cv2
from pycaw.pycaw import AudioUtilities

from modes.one_euro_filter import OneEuroFilter2D


pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True

#Screen size
screen_w, screen_h = pyautogui.size()

#Cursor state
cursor_x, cursor_y = pyautogui.position()

# Tracking state
last_hand_x = None
last_hand_y = None

_hand_filter = OneEuroFilter2D(min_cutoff=0.8, beta=0.5, d_cutoff=1.0)

sensitivity = 8.0

#Threshold
DIST_THRESHOLD = 0.02

# Click state
middle_active = False
click_start_time = None
DOUBLE_CLICK_HOLD = 0.9


#Audio-setup

devices = AudioUtilities.GetSpeakers()
volume = devices.EndpointVolume

minVol, maxVol = volume.GetVolumeRange()[:2]


#HELPER FUNCTIONS

def distance(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def finger_extended(tip, base, palm):
    return distance(tip, palm) > distance(base, palm) + DIST_THRESHOLD


#ASSISTIVE MODE

def run_assistive_mode(hand_landmarks, frame):
    global last_hand_x, last_hand_y
    global cursor_x, cursor_y
    global middle_active, click_start_time

    lm = hand_landmarks.landmark
    current_time = time.time()

    index_up = finger_extended(lm[8], lm[6], lm[0])
    middle_up = finger_extended(lm[12], lm[10], lm[0])
    ring_up = finger_extended(lm[16], lm[14], lm[0])
    little_up = finger_extended(lm[20], lm[18], lm[0])

    thumb_tip = lm[4]
    index_tip = lm[8]
    pinch_distance = distance(thumb_tip, index_tip)

    #VOLUME CONTROL

    volume_gesture = (
        index_up and
        not middle_up and
        not ring_up and
        not little_up
    )

    DISTANCE_THRESHOLD = 0.10
    MAX_VOL_SET = 0.21
    STEP = 1.2

    if volume_gesture:

        current_vol = volume.GetMasterVolumeLevel()

        if pinch_distance <= DISTANCE_THRESHOLD:
            new_vol = current_vol - STEP

        elif pinch_distance <= MAX_VOL_SET:
            new_vol = current_vol + STEP

        else:
            new_vol = current_vol

        new_vol = max(minVol, min(maxVol, new_vol))
        volume.SetMasterVolumeLevel(new_vol, None)


    #CURSOR MOVEMENT
    if index_up and not middle_up and not ring_up and not little_up:

        index_tip = lm[8]
        now = current_time

        filtered_hand_x, filtered_hand_y = _hand_filter.filter(
            index_tip.x, index_tip.y, now
        )

        if last_hand_x is None or last_hand_y is None:
            last_hand_x = filtered_hand_x
            last_hand_y = filtered_hand_y
            return

        dx = filtered_hand_x - last_hand_x
        dy = filtered_hand_y - last_hand_y

        MAX_DELTA = 0.15
        if abs(dx) > MAX_DELTA or abs(dy) > MAX_DELTA:
            last_hand_x = filtered_hand_x
            last_hand_y = filtered_hand_y
            return

        target_x = cursor_x + dx * screen_w * sensitivity
        target_y = cursor_y + dy * screen_h * sensitivity

        cursor_x = round(target_x, 2)
        cursor_y = round(target_y, 2)

        MARGIN = 10
        cursor_x = max(MARGIN, min(screen_w - MARGIN, cursor_x))
        cursor_y = max(MARGIN, min(screen_h - MARGIN, cursor_y))

        pyautogui.moveTo(cursor_x, cursor_y, _pause=False)

        last_hand_x = filtered_hand_x
        last_hand_y = filtered_hand_y


    #CLICK LOGIC
    elif index_up and middle_up and not ring_up and not little_up:

        if not middle_active:
            middle_active = True
            click_start_time = current_time

        else:
            hold_duration = current_time - click_start_time

            if hold_duration >= DOUBLE_CLICK_HOLD:
                pyautogui.doubleClick()
                middle_active = False
                click_start_time = None

        last_hand_x = None
        last_hand_y = None
        _hand_filter.reset()


    else:
        # If middle is released before hold threshold then its single click
        if middle_active and click_start_time is not None:
            hold_duration = current_time - click_start_time

            if hold_duration < DOUBLE_CLICK_HOLD:
                pyautogui.click()

        middle_active = False
        click_start_time = None
        last_hand_x = None
        last_hand_y = None
        _hand_filter.reset()


    #Audio bar

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