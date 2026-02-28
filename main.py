import cv2
import mediapipe as mp
import time
import math
import pyautogui
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.01

from modes.entertainment import run_entertainment_mode
from modes.presentation import run_presentation_mode

#INITIALIZE

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

mp_draw = mp.solutions.drawing_utils
cap = cv2.VideoCapture(0)

#APPSTATE

app_state = "menu"
current_mode = None

MODE_NAMES = {
    1: "PRESENTATION MODE",
    2: "ASSISTIVE MODE",
    3: "COMMUNICATION MODE",
    4: "ENTERTAINMENT MODE"
}

#Timing control
HOLD_TIME = 1.0
last_finger_count = None
gesture_start_time = None

#HELPER FUNCTIONS

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


#MAIN LOOP

while True:
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    key = cv2.waitKey(1) & 0xFF

    #MENU STATE
    if app_state == "menu":
        overlay = frame.copy()

        cv2.putText(overlay, "ECHO - Select Mode",
                    (50, 50), cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0, 255, 0), 2)

        cv2.putText(overlay, "1 Finger - Presentation",
                    (60, 120), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (255, 255, 255), 2)

        cv2.putText(overlay, "2 Fingers - Assistive",
                    (60, 160), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (255, 255, 255), 2)

        cv2.putText(overlay, "3 Fingers - Communication",
                    (60, 200), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (255, 255, 255), 2)

        cv2.putText(overlay, "4 Fingers - Entertainment",
                    (60, 240), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (255, 255, 255), 2)

        detected = None

        if result.multi_hand_landmarks:
            for hand in result.multi_hand_landmarks:
                mp_draw.draw_landmarks(
                    overlay, hand, mp_hands.HAND_CONNECTIONS
                )
                detected = count_non_thumb_fingers(hand.landmark)

        if detected in [1, 2, 3, 4]:

            cv2.putText(overlay,
                        f"Detected: {detected}",
                        (60, 300),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, (0, 255, 255), 2)

            if detected == last_finger_count:
                if time.time() - gesture_start_time >= HOLD_TIME:
                    current_mode = detected
                    app_state = "active"
                    last_finger_count = None
                    gesture_start_time = None
            else:
                last_finger_count = detected
                gesture_start_time = time.time()
        else:
            last_finger_count = None
            gesture_start_time = None

        cv2.putText(overlay,
                    "Hold gesture for 1 second",
                    (60, 340),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (200, 200, 200), 2)

        cv2.imshow("ECHO", overlay)

        if key == ord('q'):
            break

        continue

    #ACTIVE MODE

    cv2.putText(frame,
                f"MODE: {MODE_NAMES.get(current_mode)}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1, (0, 255, 0), 2)

    if result.multi_hand_landmarks:
        for hand in result.multi_hand_landmarks:
            mp_draw.draw_landmarks(
                frame, hand, mp_hands.HAND_CONNECTIONS
            )

          
            if current_mode == 1:
                run_presentation_mode(hand)

            if current_mode == 4:
                run_entertainment_mode(hand,frame)

    cv2.putText(frame,
                "ESC - Back | Q - Quit",
                (20, 460),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (255, 255, 255), 2)

    cv2.imshow("ECHO", frame)

    if key == 27:
        app_state = "menu"
        current_mode = None
    elif key == ord('q'):
        break

#CLEANUP

cap.release()
cv2.destroyAllWindows()