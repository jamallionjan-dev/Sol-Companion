"""Sol Mind lives only as long as the game it serves."""
import os
import time

SYNCHRONIZE, WAIT_TIMEOUT = 0x00100000, 258
HEARTBEAT_STALE = 45.0


def process_alive(pid):
    """True while that process is running."""
    if not pid: return False
    import ctypes
    k = ctypes.windll.kernel32
    h = k.OpenProcess(SYNCHRONIZE, False, int(pid))
    if not h: return False
    try:
        return k.WaitForSingleObject(h, 0) == WAIT_TIMEOUT
    finally:
        k.CloseHandle(h)


class Watch:
    """With a pid, that process decides. Without one, the game's own heartbeat file does, once it has been seen beating."""
    def __init__(self, game_pid=0, heartbeat=None):
        self.pid, self.heartbeat, self.seen, self.started = int(game_pid or 0), heartbeat, False, time.time()

    def _beat_age(self):
        try: return time.time() - os.path.getmtime(self.heartbeat)
        except (OSError, TypeError): return None

    def game_is_gone(self):
        if self.pid: return not process_alive(self.pid)
        age = self._beat_age()
        if age is None: return False
        if age < HEARTBEAT_STALE and os.path.getmtime(self.heartbeat) >= self.started - HEARTBEAT_STALE: self.seen = True
        return self.seen and age >= HEARTBEAT_STALE
