"""far_meta: far arrival also for a vehicle the game keeps "in meta" (his Bradley in the save of 2026-11-10 19:47, row 6; a SmallCar, row 9).
Game closed only. In place and idempotent; for a lab with apply_s65 (far_car) and apply_s72_far_arrival (the arrival inside the loaded area).
Plan: DOCS/PLAN_spatial_awareness.md 12.

What "in meta" is (javap of 42.22.2, confirmed): a vehicle whose chunk unloads while BaseVehicle.shouldUpdateInMeta() is true (engine
running, alarm active or siren on) is kept alive by VirtualVehicleManager (IsoChunk.removeFromWorld -> addToMeta), and its row is saved
with inMeta = 1 (VehiclesDB2$VehicleBuffer.set). Any vehicle can be kept so, a KI5 one, the Bradley or a helicopter alike; nothing in the
KI5 or AviationCore Lua stores vehicles anywhere else.

The jar (SolCarsNearCore): a car kept in meta keeps the verdict in_meta and gets a 16th field, its own row's verdict.
This (SolFar.lua):
  parseCars   reads that 16th field (metaVerdict)
  choose      a car kept in meta counts with its row's verdict ONLY when the arrival inside the loaded area is there
              (solCarArriveRequest); it then always comes that way, never by the old outside move (which refuses it: in_meta)
  carsAnswer  the same, so what she says about the cars around her matches what she can bring
Without the new jar (no 16th field) or without SolCarArriveRequest, nothing changes: such a car is skipped and she comes on foot,
"جاية مشي، بدي ..." (the Mind's own line; nothing about why).
usage: apply_s76_far_meta.py <client dir>"""
import os, sys
NL, CRLF = chr(10), chr(13) + chr(10)

def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:90])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))

SF = [
    ('loaded = f[11] == "1", verdict = f[12] }\n',
     'loaded = f[11] == "1", verdict = f[12], metaVerdict = f[16] }       -- far_meta: f[16] only for a car kept in meta\n'),
    ("""        if c.loaded or c.x == nil then return end
""", """        if c.loaded or c.x == nil then return end
        if c.verdict == "in_meta" then                                           -- far_meta: kept running far away; only the inside arrival brings it
            if c.metaVerdict == nil or type(rawget(_G, "solCarArriveRequest")) ~= "function" then return end
            local m = {}
            for k, v in pairs(c) do m[k] = v end
            m.verdict, m.meta = c.metaVerdict, true
            c = m
        end
"""),
    ("kind = kindOf(c.script), mine = mine }\n", "kind = kindOf(c.script), mine = mine, meta = c.meta == true }\n"),
    ("""    log("car for the trip: " .. tostring(best.id) .. " " .. tostring(best.script) .. (best.mine and " (hers)" or ""))
""", """    log("car for the trip: " .. tostring(best.id) .. " " .. tostring(best.script) .. (best.mine and " (hers)" or "") .. (best.meta and " (kept in meta)" or ""))
"""),
    ("""        local v = startable(c, hasKey) and "ok" or c.verdict                    -- her own key counts
""", """        local cv = c
        if c.verdict == "in_meta" and c.metaVerdict ~= nil and type(rawget(_G, "solCarArriveRequest")) == "function" then cv = { verdict = c.metaVerdict, keyId = c.keyId } end   -- far_meta
        local v = startable(cv, hasKey) and "ok" or cv.verdict                  -- her own key counts
"""),
]

def client(cl):
    for o, n in SF: edit(os.path.join(cl, "SolFar.lua"), o, n)

if __name__ == "__main__":
    client(sys.argv[1])
    print("far_meta applied")
