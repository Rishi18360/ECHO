import pyautogui
import math
import time

# Screensize
screen_w, screen_h = pyautogui.size()

# Cursorstate
cursor_x, cursor_y = pyautogui.position()

# Trackingstate
last_hand_x = None
last_hand_y = None

# Sensitivity
sensitivity = 1.8

# Thresholds
DIST_THRESHOLD = 0.02
SLIDE_COOLDOWN = 1.5

last_slide_time = 0


#Helper Functions

def distance(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def finger_extended(tip, base, palm):
    return distance(tip, palm) > distance(base, palm) + DIST_THRESHOLD


def count_non_thumb_fingers(lm):
    palm = lm[0]
    count = 0
    fingers = [(8, 6), (12, 10), (16, 14), (20, 18)]

    for tip, base in fingers:
        if finger_extended(lm[tip], lm[base], palm):
            count += 1

    return count


#Presentation Mode

def run_presentation_mode(hand_landmarks):
    global last_hand_x, last_hand_y
    global cursor_x, cursor_y
    global last_slide_time

    lm = hand_landmarks.landmark
    finger_count = count_non_thumb_fingers(lm)
    current_time = time.time()

    #NEXT SLIDE-2 Fingers

    if finger_count == 2:
        if current_time - last_slide_time > SLIDE_COOLDOWN:
            pyautogui.press("right")
            last_slide_time = current_time

        #Reset tracking to avoid cursor jump
        last_hand_x = None
        last_hand_y = None
        return
    

    if finger_count == 3:
        if current_time - last_slide_time > SLIDE_COOLDOWN:
            pyautogui.press("left")
            last_slide_time = current_time

        #Reset tracking to avoid cursor jump
        last_hand_x = None
        last_hand_y = None
        return


    #CURSOR CONTROL — 1 Finger Only


    if finger_count == 1:

        index_tip = lm[8]
        hand_x = index_tip.x
        hand_y = index_tip.y

        if last_hand_x is None or last_hand_y is None:
            last_hand_x = hand_x
            last_hand_y = hand_y
            return

        dx = hand_x - last_hand_x
        dy = hand_y - last_hand_y

        cursor_x += dx * screen_w * sensitivity
        cursor_y += dy * screen_h * sensitivity

        # Safe margin to avoid PyAutoGUI fail-safe
        MARGIN = 10
        cursor_x = max(MARGIN, min(screen_w - MARGIN, cursor_x))
        cursor_y = max(MARGIN, min(screen_h - MARGIN, cursor_y))

        pyautogui.moveTo(cursor_x, cursor_y)

        last_hand_x = hand_x
        last_hand_y = hand_y

    else:
        # Reset when no valid gesture
        last_hand_x = None
        last_hand_y = None