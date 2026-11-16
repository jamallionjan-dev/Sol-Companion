"""spatial_access: read the real tiles of an area from the game's own map files (read-only) and write a fixture for the offline tests.
  lotheader  LOTH v1: tile names, width/height/minLevel/maxLevel, rooms (name, level, rects, objects), buildings (room ids)
  lotpack    LOTP v1: chunk table (int at 12 + index*8, index = (wx - cx*32)*32 + (wy - cy*32)), then per chunk
             for z in minLevel..maxLevel, x 0..7, y 0..7: int n; n == -1 -> int skip (this square and skip-1 more are empty);
             n > 1 -> int roomId, then n-1 tile indices into the header's tile list (IsoLot.load, 42.22.2 bytecode)
  tiles      media/tile_definitions/*.tiles.txt: per tileset 'file', 'size = cols,rows', per tile 'xy' and its properties
Only vanilla map data: things the player built or broke in his save are not in these files.
usage: python extract_place.py <x0> <y0> <x1> <y1> <z> <out.json>"""
import json, os, re, struct, sys
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid\media"
MAP = os.path.join(GAME, "maps", "Muldraugh, KY")
TDEF = os.path.join(GAME, "tile_definitions")
CELL, CH = 256, 8
KEEP = {"WallN", "WallW", "WallNW", "WallNTrans", "WallWTrans", "WallNWTrans", "DoorWallN", "DoorWallW", "doorN", "doorW", "WindowN", "WindowW",
        "windowN", "windowW", "HoppableN", "HoppableW", "TallHoppableN", "TallHoppableW", "collideN", "collideW", "solid", "solidtrans", "solidfloor",
        "container", "DoubleDoor", "GarageDoor", "CantClimb", "WallSE", "IsLow", "IsStairs", "StairsTopN", "StairsTopW"}

def load_tiles():
    props = {}
    for fn in sorted(os.listdir(TDEF)):
        if not fn.endswith(".tiles.txt"): continue
        cur, cols, tile = None, 8, None
        for line in open(os.path.join(TDEF, fn), encoding="utf-8", errors="replace"):
            s = line.strip()
            m = re.match(r"file = (\S+)", s)
            if m: cur = m.group(1); continue
            m = re.match(r"size = (\d+),(\d+)", s)
            if m: cols = int(m.group(1)); continue
            m = re.match(r"xy = (\d+),(\d+)", s)
            if m and cur: tile = "%s_%d" % (cur, int(m.group(1)) + int(m.group(2)) * cols); props.setdefault(tile, set()); continue
            m = re.match(r"([A-Za-z]+) =", s)
            if m and tile and m.group(1) in KEEP: props[tile].add(m.group(1))
    return props

def parse_header(path):
    b = open(path, "rb").read(); i = 8
    def rint():
        nonlocal i
        v = struct.unpack_from("<i", b, i)[0]; i += 4; return v
    def rstr():
        nonlocal i
        e = b.index(b"\n", i); s = b[i:e].decode("latin-1"); i = e + 1; return s
    tiles = [rstr() for _ in range(rint())]
    w, h, minL, maxL = rint(), rint(), rint(), rint()
    rooms = []
    for _ in range(rint()):
        name = rstr(); lvl = rint()
        rects = [(rint(), rint(), rint(), rint()) for _ in range(rint())]
        objs = [(rint(), rint(), rint()) for _ in range(rint())]
        rooms.append({"name": name, "level": lvl, "rects": rects})
    buildings = [[rint() for _ in range(rint())] for _ in range(rint())]
    return tiles, minL, maxL, rooms, buildings

def squares(cx, cy, x0, y0, x1, y1, z):
    tiles, minL, maxL, rooms, buildings = parse_header(os.path.join(MAP, "%d_%d.lotheader" % (cx, cy)))
    f = open(os.path.join(MAP, "world_%d_%d.lotpack" % (cx, cy)), "rb")
    out = {}
    for wx in range(x0 // CH, x1 // CH + 1):
        for wy in range(y0 // CH, y1 // CH + 1):
            if wx // 32 != cx or wy // 32 != cy: continue
            idx = (wx - cx * 32) * 32 + (wy - cy * 32)
            f.seek(12 + idx * 8); off = struct.unpack("<i", f.read(4))[0]; f.seek(off)
            skip = 0
            for lz in range(minL, maxL + 1):
                for x in range(CH):
                    for y in range(CH):
                        if skip > 0: skip -= 1; continue
                        n = struct.unpack("<i", f.read(4))[0]
                        if n == -1:
                            skip = struct.unpack("<i", f.read(4))[0]
                            if skip > 0: skip -= 1
                            continue
                        if n <= 1: continue
                        room = struct.unpack("<i", f.read(4))[0]
                        ids = struct.unpack("<%di" % (n - 1), f.read(4 * (n - 1)))
                        X, Y = wx * CH + x, wy * CH + y
                        if lz == z and x0 <= X <= x1 and y0 <= Y <= y1:
                            out[(X, Y)] = (room, [tiles[t] for t in ids])
    return out, rooms, buildings

def main():
    x0, y0, x1, y1, z = map(int, sys.argv[1:6]); dst = sys.argv[6]
    props = load_tiles()
    sq, roomsAll = {}, {}
    for cx in range(x0 // CELL, x1 // CELL + 1):
        for cy in range(y0 // CELL, y1 // CELL + 1):
            part, rooms, buildings = squares(cx, cy, x0, y0, x1, y1, z)
            bOf = {r: bi for bi, rs in enumerate(buildings) for r in rs}
            for (X, Y), (room, names) in part.items():
                p = set()
                for t in names: p |= props.get(t, set())
                rkey = None
                lx, ly = X - cx * CELL, Y - cy * CELL                       # 42.22 lotpacks carry -1: the room is the header rect holding the square
                for ri, r in enumerate(rooms):
                    if r["level"] == z and any(rx <= lx < rx + rw and ry <= ly < ry + rh for rx, ry, rw, rh in r["rects"]):
                        rkey = "%d_%d_%d" % (cx, cy, ri)
                        roomsAll[rkey] = {"name": r["name"], "building": "%d_%d_%d" % (cx, cy, bOf.get(ri, -1))}
                        break
                sq["%d,%d" % (X, Y)] = {"t": names, "p": sorted(p), "room": rkey}
    json.dump({"area": [x0, y0, x1, y1, z], "source": "lotpack (vanilla map, read-only)", "squares": sq, "rooms": roomsAll},
              open(dst, "w", encoding="utf-8"), indent=0, sort_keys=True)
    print("squares", len(sq), "rooms", len(roomsAll), "->", dst)

if __name__ == "__main__":
    main()
