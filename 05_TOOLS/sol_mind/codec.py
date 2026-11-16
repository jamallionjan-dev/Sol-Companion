"""Exact Python port of SCAIMailbox.lua (SOL_AI_FRAME_V1 codec).

Tags: N nil, B1/B0 bool, D<%.17g>; number, S<hexlen>:<HEX> string,
A<n>: array, M<n>: map. An empty table encodes as A0: (Lua classifies it as array).
"""
import math
import re

FORMAT = "SOL_AI_FRAME_V1"
PROTOCOL = "sol-ai-1"
SCHEMA = 1
MAX_CHARS = 131072
MAX_VALUES = 4096
MAX_DEPTH = 12
_DIGITS = re.compile(r"[0-9]+\Z")


class CodecError(ValueError):
    pass


def _enc(v, st, depth, out):
    if depth > MAX_DEPTH:
        raise CodecError("depth_limit")
    st[0] += 1
    if st[0] > MAX_VALUES:
        raise CodecError("value_limit")
    if v is None:
        out.append("N")
    elif isinstance(v, bool):
        out.append("B1" if v else "B0")
    elif isinstance(v, (int, float)):
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            raise CodecError("non_finite_number")
        out.append("D" + format(f, ".17g") + ";")
    elif isinstance(v, str):
        h = v.encode("utf-8").hex().upper()
        out.append("S%d:%s" % (len(h), h))
    elif isinstance(v, (list, tuple)):
        if any(x is None for x in v):
            raise CodecError("nil_in_array")  # Lua arrays cannot hold nil
        out.append("A%d:" % len(v))
        for x in v:
            _enc(x, st, depth + 1, out)
    elif isinstance(v, dict):
        v = {k: x for k, x in v.items() if x is not None}  # Lua drops nil-valued keys
        if not v:
            out.append("A0:")
            return
        keys = list(v.keys())
        for k in keys:
            if isinstance(k, bool) or not isinstance(k, (str, int, float)):
                raise CodecError("unsupported_key_type")
        keys.sort(key=lambda k: (1, 0.0, k) if isinstance(k, str) else (0, float(k), ""))
        out.append("M%d:" % len(keys))
        for k in keys:
            _enc(k, st, depth + 1, out)
            _enc(v[k], st, depth + 1, out)
    else:
        raise CodecError("unsupported_type_" + type(v).__name__)


def encode_body(frame):
    if not isinstance(frame, dict) or frame.get("protocol") != PROTOCOL:
        raise CodecError("protocol_mismatch")
    out = []
    _enc(frame, [0], 0, out)
    body = "".join(out)
    if len(body) > MAX_CHARS:
        raise CodecError("frame_too_large")
    return body


def _count(body, i, delim):
    j = body.find(delim, i)
    if j < 0:
        raise CodecError("delimiter_missing")
    raw = body[i:j]
    if not _DIGITS.match(raw):
        raise CodecError("invalid_count")
    return int(raw), j + 1


def _dec(body, i, st, depth):
    if depth > MAX_DEPTH:
        raise CodecError("depth_limit")
    st[0] += 1
    if st[0] > MAX_VALUES:
        raise CodecError("value_limit")
    if i >= len(body):
        raise CodecError("unexpected_end")
    tag = body[i]
    if tag == "N":
        return None, i + 1
    if tag == "B":
        b = body[i + 1:i + 2]
        if b == "1":
            return True, i + 2
        if b == "0":
            return False, i + 2
        raise CodecError("invalid_boolean")
    if tag == "D":
        j = body.find(";", i + 1)
        if j < 0:
            raise CodecError("number_terminator_missing")
        try:
            f = float(body[i + 1:j])
        except ValueError:
            raise CodecError("invalid_number")
        if math.isnan(f) or math.isinf(f):
            raise CodecError("invalid_number")
        return (int(f) if f.is_integer() and abs(f) < 2 ** 53 else f), j + 1
    if tag == "S":
        n, start = _count(body, i + 1, ":")
        if start + n > len(body):
            raise CodecError("string_length_invalid")
        h = body[start:start + n]
        if n % 2:
            raise CodecError("invalid_hex")
        try:
            return bytes.fromhex(h).decode("utf-8", "replace"), start + n
        except ValueError:
            raise CodecError("invalid_hex")
    if tag not in "AM":
        raise CodecError("invalid_tag")
    n, cur = _count(body, i + 1, ":")
    if n > MAX_VALUES:
        raise CodecError("container_limit")
    if tag == "A":
        res = []
        for _ in range(n):
            v, cur = _dec(body, cur, st, depth + 1)
            res.append(v)
        return res, cur
    res = {}
    for _ in range(n):
        k, cur = _dec(body, cur, st, depth + 1)
        if isinstance(k, bool) or not isinstance(k, (str, int, float)):
            raise CodecError("invalid_map_key")
        v, cur = _dec(body, cur, st, depth + 1)
        res[k] = v
    return res, cur


def decode_body(body):
    if len(body) > MAX_CHARS:
        raise CodecError("frame_too_large")
    frame, cur = _dec(body, 0, [0], 0)
    if cur != len(body):
        raise CodecError("trailing_data")
    if not isinstance(frame, dict) or frame.get("protocol") != PROTOCOL:
        raise CodecError("protocol_mismatch")
    return frame


def as_map(v):
    """Lua empty tables arrive as []; treat them as {}."""
    if isinstance(v, dict):
        return v
    return {}


def render_file(frame):
    return FORMAT + "\n" + encode_body(frame) + "\nEND\n"


def parse_file(text):
    """Mirror of readFrame(): returns frame or raises CodecError(reason)."""
    lines = text.splitlines()
    if not lines or (len(lines) < 2 and not lines[0]):
        raise CodecError("empty")
    if lines[0] != FORMAT:
        raise CodecError("format_mismatch")
    if len(lines) < 3 or lines[2] != "END":
        raise CodecError("incomplete_frame")
    return decode_body(lines[1])
