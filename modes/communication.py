import math
import time
import cv2

# ── Tuning constants ──────────────────────────────────────────────────
_HOLD       = 10     # consecutive matching frames to lock-in a word
_COOLDOWN   = 1.5    # seconds before the next word can be accepted
_SHOW_SEC   = 3.0    # how long confirmed word stays on screen
_MISS_TOL   = 3      # frames of no detection before tracking resets
_FINGER_THR = 0.02   # extension-distance margin (non-thumb fingers)
_THUMB_THR  = 0.01   # extension-distance margin (thumb)

# ── Module-level state ────────────────────────────────────────────────
_track_gesture = None    # gesture currently being tracked
_track_count   = 0       # consecutive frames of _track_gesture
_miss_count    = 0       # frames since last matching detection
_last_time     = 0.0     # timestamp of last accepted word
_word          = ""      # currently displayed (confirmed) word
_word_time     = 0.0     # when _word was set

# ── ASL gesture table ────────────────────────────────────────────────
#  (thumb, index, middle, ring, pinky)  True = extended, None = don't care
_SIGNS = {
    "STOP":   (True,  True,  True,  True,  True),
    "YES":    (True,  False, False, False, False),
    "NO":     (True,  True,  False, False, False),
    "HELP":   (None,  True,  False, False, True),
    "THANKS": (True,  False, False, False, True),
}

# ── Low-level helpers ────────────────────────────────────────────────

def _dist(a, b):
    return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def _finger_up(tip, base, wrist):
    return _dist(tip, wrist) > _dist(base, wrist) + _FINGER_THR


def _thumb_up(lm):
    # Thumb moves laterally – compare tip (4) vs CMC (2) distance from wrist
    return _dist(lm[4], lm[0]) > _dist(lm[2], lm[0]) + _THUMB_THR


def _classify(lm):
    """Return the ASL word matching the current hand shape, or *None*."""
    state = (
        _thumb_up(lm),
        _finger_up(lm[8],  lm[6],  lm[0]),    # index
        _finger_up(lm[12], lm[10], lm[0]),     # middle
        _finger_up(lm[16], lm[14], lm[0]),     # ring
        _finger_up(lm[20], lm[18], lm[0]),     # pinky
    )
    for name, sig in _SIGNS.items():
        if all(s is None or s == v for s, v in zip(sig, state)):
            return name
    return None


# ── Drawing helpers ──────────────────────────────────────────────────

def _centered(img, text, cx, cy, scale, color, thick):
    """Draw *text* horizontally centred on (*cx*, *cy*)."""
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thick)
    cv2.putText(img, text, (cx - tw // 2, cy + th // 2),
                cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def _hud(frame, word):
    """Draw the recognised word at bottom-centre of the frame."""
    h, w = frame.shape[:2]
    bar = 60
    top = h - bar

    # semi-transparent dark strip
    ov = frame.copy()
    cv2.rectangle(ov, (0, top), (w, h), (12, 12, 12), -1)
    cv2.addWeighted(ov, 0.72, frame, 0.28, 0, frame)
    cv2.line(frame, (0, top), (w, top), (255, 212, 0), 2)

    # ── show word centred ──
    if word:
        cx, cy = w // 2, top + bar // 2
        _centered(frame, word, cx, cy, 1.3, (0, 0, 0), 6)
        _centered(frame, word, cx, cy, 1.3, (100, 255, 80), 3)


# ── Public entry point ───────────────────────────────────────────────

def run_communication_mode(hand_landmarks, frame=None):
    """Process one camera frame for communication mode.

    *hand_landmarks* may be ``None`` when no hand is visible; the overlay
    is still drawn so the confirmed word and sentence remain on screen.
    """
    global _track_gesture, _track_count, _miss_count
    global _last_time, _word, _word_time

    now = time.time()
    gesture = None
    progress = 0.0

    # ── classify current hand pose ──
    if hand_landmarks is not None:
        gesture = _classify(hand_landmarks.landmark)

    # ── tracking with jitter tolerance ──
    if gesture is not None:
        if gesture == _track_gesture:
            _track_count += 1
        else:
            _track_gesture = gesture
            _track_count = 1
        _miss_count = 0
    else:
        _miss_count += 1
        if _miss_count > _MISS_TOL:
            _track_gesture = None
            _track_count = 0

    # ── accept gesture when held long enough ──
    if (_track_gesture is not None
            and _track_count >= _HOLD
            and now - _last_time >= _COOLDOWN):
        _word = _track_gesture
        _word_time = now
        _last_time = now
        _track_gesture = None
        _track_count = 0

    # ── expire displayed word ──
    shown = _word if (now - _word_time < _SHOW_SEC) else ""

    # ── draw overlay ──
    if frame is not None:
        _hud(frame, shown)