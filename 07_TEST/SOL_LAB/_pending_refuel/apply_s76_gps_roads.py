"""gps_static_roads + gps_plain_words. Game closed only. In place and idempotent: every edit is skipped when it is already there.

gps_static_roads: the Living Fellows router builds its graph only from street pieces inside the start/goal box + 160 tiles,
  so a trip whose only road leaves that box (home -> 625 Dewey St runs south past y 11200) came back INCOMPLETE_MAP_DATA and
  the panel drew a straight line. SolStaticRoads.lua plans over the whole map's road graph (SolStaticRoadsData.lua, from the
  game's streets.xml + Sol_Trails) whenever the router gives up for that kind of reason; preview, drive and replans alike.
  A destination no road reaches gets a route to the nearest reachable road point (route.partial).
gps_plain_words: SolGPSWords.lua; the GPS panel's status line says a short plain phrase for every reason code
  ("player_stop" -> "وقّفنا"); the address book never draws an id as a place name. Codes stay in the log.

  copies   SolStaticRoads.lua, SolStaticRoadsData.lua, SolGPSWords.lua -> <client dir>
  edits    SolAuthority.lua  A.FIXES += "gps_static_roads", "gps_plain_words"
           SolGPS.lua        one hook line before the status line is drawn (Panel:prerender)
           SolAddressBook.lua the row's name goes through SolGPSWords.cleanName
           <Zomboid>/Lua/SolFixes_LAB.txt  gps_static_roads=on, gps_plain_words=on (only when missing)
usage: apply_s76_gps_roads.py <client dir>"""
import os, shutil, sys
CL = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)


def edit(path, old, new, done_marker):
    t = open(path, encoding="utf-8", newline="").read()
    if done_marker in t: return "kept"
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:80])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))
    return "edited"


assert os.path.isfile(os.path.join(CL, "SolAuthority.lua")), "not a Sol client dir: " + CL
for name, marker in (("SolStaticRoads.lua", 'M.VERSION = "0.1.0"'), ("SolGPSWords.lua", 'M.VERSION = "0.1.0"'),
                     ("SolStaticRoadsData.lua", "SolStaticRoadsData = {")):
    src = os.path.join(HERE, name)
    body = open(src, encoding="ascii").read()                    # pure ASCII, like every Sol Lua file
    assert marker in body, name
    shutil.copy(src, os.path.join(CL, name))
    print("copied", name)

A = os.path.join(CL, "SolAuthority.lua")
for fix in ("gps_plain_words", "gps_static_roads"):
    print("SolAuthority", fix, edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "%s",' % fix + NL, '"%s"' % fix))

GPS = os.path.join(CL, "SolGPS.lua")
anchor = '    txt(self, state, 10, MY + MH + 36, W - 20, 0.44, "right", sc)' + NL
hook = ('    do local Wd = rawget(_G, "SolGPSWords"); if type(Wd) == "table" and type(Wd.panelLine) == "function" then'
        ' local okW, sW, cW = pcall(Wd.panelLine, st, P, dest, pts, driving, failed, isAr(), state);'
        ' if okW and type(sW) == "string" then state = sW; if type(cW) == "table" then sc = cW end end end end   -- Sol fix gps_plain_words' + NL)
print("SolGPS", edit(GPS, anchor, hook + anchor, "Sol fix gps_plain_words"))

AB = os.path.join(CL, "SolAddressBook.lua")
old = 'text(self, shortName(e), CX + btnW + 8, y + 4, CW - btnW - 16, SCALE_TXT, "right", e.looted and MUTED or nil)'
new = ('text(self, (rawget(_G, "SolGPSWords") and SolGPSWords.cleanName) and SolGPSWords.cleanName(shortName(e), word(e.kind == "house" and "house" or (e.kind == "area" and "area" or "stash"))) or shortName(e),'
       ' CX + btnW + 8, y + 4, CW - btnW - 16, SCALE_TXT, "right", e.looted and MUTED or nil)   -- Sol fix gps_plain_words')
if os.path.exists(AB): print("SolAddressBook", edit(AB, old, new, "Sol fix gps_plain_words"))

fixfile = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
if os.path.exists(fixfile):
    have = open(fixfile, encoding="utf-8").read()
    with open(fixfile, "a", encoding="utf-8", newline="") as h:
        if have and not have.endswith(NL) and ("gps_static_roads=" not in have or "gps_plain_words=" not in have): h.write(CRLF)
        for fix in ("gps_static_roads", "gps_plain_words"):
            if fix + "=" not in have: h.write(fix + "=on" + CRLF); print("SolFixes_LAB", fix + "=on")
print("applied")
