
import math
import time
 
 
class _LowPassFilter:
    __slots__ = ("_alpha", "_y", "_initialized")
 
    def __init__(self, alpha):
        self._set_alpha(alpha)
        self._y = 0.0
        self._initialized = False
 
    def _set_alpha(self, alpha):
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0.0, 1.0]")
        self._alpha = alpha
 
    def filter(self, value, alpha=None):
        if alpha is not None:
            self._set_alpha(alpha)
        if not self._initialized:
            self._y = value
            self._initialized = True
        else:
            self._y = self._alpha * value + (1.0 - self._alpha) * self._y
        return self._y
 
    @property
    def last_value(self):
        return self._y
 
 
class OneEuroFilter:
    """One Euro Filter for a single scalar signal.
 
    Parameters
    ----------
    min_cutoff : float
        Minimum cutoff frequency (Hz). Lower = smoother but more lag when
        the signal is nearly still. Typical range 0.5 - 2.0.
    beta : float
        Speed coefficient. Higher = the filter "opens up" (less smoothing,
        less lag) more aggressively as speed increases. Typical range
        0.001 - 1.0, tune to your unit scale.
    d_cutoff : float
        Cutoff frequency used for filtering the derivative (speed)
        estimate itself. 1.0 is fine for almost all use cases.
    """
 
    def __init__(self, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
 
        self._x_filter = _LowPassFilter(self._alpha(min_cutoff, 30.0))
        self._dx_filter = _LowPassFilter(self._alpha(d_cutoff, 30.0))
        self._last_time = None
 
    @staticmethod
    def _alpha(cutoff, freq):
        te = 1.0 / freq
        tau = 1.0 / (2 * math.pi * cutoff)
        return 1.0 / (1.0 + tau / te)
 
    def reset(self):
        """Call when tracking is lost/restarted so the next sample snaps
        in instantly instead of blending with a stale value."""
        self._x_filter._initialized = False
        self._dx_filter._initialized = False
        self._last_time = None
 
    def filter(self, value, timestamp=None):
        timestamp = time.time() if timestamp is None else timestamp
 
        if self._last_time is None:
            freq = 30.0  # sane default for the very first sample
        else:
            dt = timestamp - self._last_time
            freq = 1.0 / dt if dt > 1e-6 else 30.0
        self._last_time = timestamp
 
        prev_x = self._x_filter.last_value if self._x_filter._initialized else value
        dx = (value - prev_x) * freq
        edx = self._dx_filter.filter(dx, self._alpha(self.d_cutoff, freq))
 
        cutoff = self.min_cutoff + self.beta * abs(edx)
        return self._x_filter.filter(value, self._alpha(cutoff, freq))
 
 
class OneEuroFilter2D:
    """Convenience wrapper: one OneEuroFilter per axis for (x, y) points."""
 
    def __init__(self, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self._fx = OneEuroFilter(min_cutoff, beta, d_cutoff)
        self._fy = OneEuroFilter(min_cutoff, beta, d_cutoff)
 
    def reset(self):
        self._fx.reset()
        self._fy.reset()
 
    def filter(self, x, y, timestamp=None):
        timestamp = time.time() if timestamp is None else timestamp
        return self._fx.filter(x, timestamp), self._fy.filter(y, timestamp)
 