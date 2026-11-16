"""Reads a COPY of a save's vehicles.db and prints what each record says. Read-only.
Field order is BaseVehicle.save / VehiclePart.save from the game's bytecode (2026-11-09).
Usage: decode_vehicles.py <copy of vehicles.db> [x y [radius]]"""
import math, re, sqlite3, struct, sys

def u16(d, p): return struct.unpack_from(">H", d, p)[0]
def i32(d, p): return struct.unpack_from(">i", d, p)[0]
def f32(d, p): return struct.unpack_from(">f", d, p)[0]

PART = re.compile(rb"\x00([\x03-\x28])([A-Z][A-Za-z0-9_]+)([\x00\x01])")
TRAILER = 21     # condition i, wheelFriction f, mechanicSkillInstaller i, suspensionCompression f, suspensionDamping f, entity b

def header(d):
    """Everything before the parts, walking forward from the script name."""
    m = re.search(rb"\x00([\x03-\x40])(Base\.[A-Za-z0-9_]+|[A-Za-z0-9_]+\.[A-Za-z0-9_]+)", d[:120])
    if not m or m.end() - m.start(2) != m.group(1)[0]: return None
    p = m.end()
    h = {"script": m.group(2).decode()}
    h["skin"] = i32(d, p); p += 5
    h["front"], h["rear"], h["curFront"], h["curRear"], h["a"], h["b"] = [i32(d, p + 4 * k) for k in range(6)]; p += 24
    h["keyId"] = i32(d, p); p += 4
    h["keySpawned"] = d[p]; p += 1
    h["headlights"], h["created"] = d[p], d[p + 1]; p += 6
    h["partCount"] = u16(d, p); p += 2
    h["partsAt"] = p
    return h

def parts(d, start):
    """(name, offset of the name) for each part, accepted only when the fixed fields of the part before it are sane."""
    found, seen = [], set()
    for m in PART.finditer(d, start):
        if m.end(2) - m.start(2) != m.group(1)[0] or m.start() in seen: continue
        if found:
            t = m.start() - TRAILER
            if t < 0 or not (0 <= i32(d, t) <= 100) or not (0 <= i32(d, t + 8) <= 20): continue
        found.append((m.group(2).decode(), m.start()))
        seen.add(m.start())
    return found

def tail(d, start):
    """Scanned from the end: the last part's trailer, then four flag bytes, then four floats in 0..1 (rust and colour)."""
    for p in range(len(d) - 24, start, -1):
        if not all(d[p + k] in (0, 1) for k in range(4)): continue
        if not all(0 <= f32(d, p + 4 + 4 * k) <= 1.0001 for k in range(4)): continue
        t = p - TRAILER
        if t > start and 0 <= i32(d, t) <= 100 and 0 <= i32(d, t + 8) <= 20:
            return {"keyIsOnDoor": d[p], "hotwired": d[p + 1], "hotwiredBroken": d[p + 2], "keysInIgnition": d[p + 3], "rust": round(f32(d, p + 4), 2), "tailAt": p}
    return None

def decode(row):
    rid, x, y, in_meta, d = row
    h = header(d)
    if h is None: return {"id": rid, "x": x, "y": y, "error": "no script name"}
    h.update(id=rid, x=round(x, 1), y=round(y, 1), inMeta=in_meta, size=len(d))
    ps = parts(d, h["partsAt"])
    h["partsFound"] = len(ps)
    t = tail(d, h["partsAt"])
    h.update(t or {"tail": None})
    limit = (t or {}).get("tailAt", len(d))
    cond = {}
    for i, (name, at) in enumerate(ps):
        end = ps[i + 1][1] if i + 1 < len(ps) else limit
        if end - TRAILER > at: cond[name] = i32(d, end - TRAILER)
        if name == "GasTank":
            k = d.find(b"contentAmount", at, end)
            if k >= 0:
                vt = d[k + 13]
                h["fuelType"] = vt
                if k + 22 <= len(d) and vt == 1:
                    h["fuel"] = round(struct.unpack_from(">d", d, k + 14)[0], 2)
                else:
                    h["fuelRaw"] = d[k + 13:k + 23].hex()
            item = d[at + 2 + len(name):at + 2 + len(name) + 8].hex()
            h["gasHead"] = item
    h["engine"] = cond.get("Engine")
    h["battery"] = cond.get("Battery")
    h["tires"] = {k: v for k, v in cond.items() if k.startswith("Tire")}
    kb = struct.pack(">i", h["keyId"])
    hits = [m.start() for m in re.finditer(re.escape(kb), d)]
    h["keyIdHits"] = len(hits)                     # 1 = only the header; more = a key item carrying this id is stored in the car
    return h

if __name__ == "__main__":
    p = sys.argv[1].replace(chr(92), "/")
    c = sqlite3.connect("file:" + p + "?mode=ro", uri=True)
    rows = c.execute("select id,x,y,inMeta,data from vehicles").fetchall()
    out = [decode(r) for r in rows]
    if len(sys.argv) >= 4:
        cx, cy = float(sys.argv[2]), float(sys.argv[3])
        out.sort(key=lambda h: math.hypot(h["x"] - cx, h["y"] - cy))
    keep = ("id", "script", "x", "y", "inMeta", "keyId", "keySpawned", "keyIdHits", "keyIsOnDoor", "hotwired", "hotwiredBroken", "keysInIgnition", "fuel", "fuelRaw", "engine", "battery", "tires", "partCount", "partsFound", "rust", "error", "tail")
    for h in out: print({k: h[k] for k in keep if k in h})
