import pyautogui
import math
import time

# Screen size
screen_w, screen_h = pyautogui.size()

# Cursor state
cursor_x, cursor_y = pyautogui.position()

# Tracking state
last_hand_x = None
last_hand_y = None

# Sensitivity
sensitivity = 8.0

# Smoothing
SMOOTHING = 0.20

# Threshold
DIST_THRESHOLD = 0.02

# Click state
middle_active = False
click_start_time = None
DOUBLE_CLICK_HOLD = 0.9


#HELPER FUNCTIONS

def distance(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def finger_extended(tip, base, palm):
    return distance(tip, palm) > distance(base, palm) + DIST_THRESHOLD


#ASSISTIVE MODE

def run_assistive_mode(hand_landmarks):
    global last_hand_x, last_hand_y
    global cursor_x, cursor_y
    global middle_active, click_start_time

    lm = hand_landmarks.landmark
    current_time = time.time()

    index_up = finger_extended(lm[8], lm[6], lm[0])
    middle_up = finger_extended(lm[12], lm[10], lm[0])
    ring_up = finger_extended(lm[16], lm[14], lm[0])
    little_up = finger_extended(lm[20], lm[18], lm[0])

    #CURSOR MOVEMENT
    if index_up and not middle_up and not ring_up and not little_up:

        index_tip = lm[8]
        hand_x = index_tip.x
        hand_y = index_tip.y

        if last_hand_x is None or last_hand_y is None:
            last_hand_x = hand_x
            last_hand_y = hand_y
            return

        dx = hand_x - last_hand_x
        dy = hand_y - last_hand_y

        # Prevent large jump when hand re-enters
        MAX_DELTA = 0.05
        if abs(dx) > MAX_DELTA:
            dx = 0
        if abs(dy) > MAX_DELTA:
            dy = 0

        #Remove jitter
        MIN_MOVEMENT = 0.003
        if abs(dx) < MIN_MOVEMENT:
            dx = 0
        if abs(dy) < MIN_MOVEMENT:
            dy = 0

        target_x = cursor_x + dx * screen_w * sensitivity
        target_y = cursor_y + dy * screen_h * sensitivity

        #smoothing
        cursor_x = cursor_x * (1 - SMOOTHING) + target_x * SMOOTHING
        cursor_y = cursor_y * (1 - SMOOTHING) + target_y * SMOOTHING

        #Precision cleanup
        cursor_x = round(cursor_x, 2)
        cursor_y = round(cursor_y, 2)

        MARGIN = 10
        cursor_x = max(MARGIN, min(screen_w - MARGIN, cursor_x))
        cursor_y = max(MARGIN, min(screen_h - MARGIN, cursor_y))

        pyautogui.moveTo(cursor_x, cursor_y)

        last_hand_x = hand_x
        last_hand_y = hand_y


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