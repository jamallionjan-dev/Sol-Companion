"""File mailbox helpers: atomic writes (tmp + replace) and tolerant reads."""
import os
import time

from codec import CodecError, parse_file, render_file


def write_frame(path, frame, retries=40, delay=0.025):
    text = render_file(frame)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="ascii", newline="\n") as f:
        f.write(text)
    for _ in range(retries):
        try:
            os.replace(tmp, path)
            return True
        except PermissionError:
            time.sleep(delay)
    try:
        os.remove(tmp)
    except OSError:
        pass
    return False


def read_frame(path):
    """Returns (frame, None) or (None, reason)."""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            text = f.read()
    except FileNotFoundError:
        return None, "missing"
    except OSError:
        return None, "locked"
    try:
        return parse_file(text), None
    except CodecError as e:
        return None, str(e)
