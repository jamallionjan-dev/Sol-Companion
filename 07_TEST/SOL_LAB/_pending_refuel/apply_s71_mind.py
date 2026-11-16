"""Mind: a question about the cars around far-away Sol is answered from HER surroundings.
Confirmed 2026-11-10 19:44 (sol_mind.log): "شو في سيارات حواليكي؟" -> model action=none -> the map/memory answer read the cars near
the PLAYER ("ما شايفة ولا سيارة حوالينا"); the far_car list (sol_far cars, read around her saved spot) sits in _far_order, which only
runs after the model path, so it never answered. The model still decides first: when it says "no action" (a question) and she is far,
the facts come from the game's list of cars around her. usage: apply_s71_mind.py <sol_mind dir>"""
import os, sys
p = os.path.join(sys.argv[1], "chat_service.py")
t = open(p, encoding="utf-8", newline="").read()
NL = "\r\n" if "\r\n" in t else "\n"
anchor = ("        said = MA.answer(text, snap, mem, lambda: self._station_list(), lambda: self._street_now(), GZ.load(), lambda: self._gardens())"
          "   # streets, towns, stations: from the map, never guessed" + NL)
block = ("        if _CARS_Q_RX.search(text or \"\") and _CARS_ASK_RX.search(text or \"\") and not _CARS_ORDER_RX.search(text or \"\"):   # far_car: her surroundings, not his" + NL +
         "            far_done = []" + NL +
         "            if self._far_cars(snap, far_done):" + NL +
         "                said = getattr(self, \"_forced\", None); self._forced = None" + NL +
         "                done_line(\"far_cars\", \"none\", \"-\", said)" + NL +
         "                return said" + NL)
if "far_cars\", \"none\"" not in t:
    assert t.count(anchor) == 1, "model none branch changed"
    t = t.replace(anchor, block + anchor)
open(p, "w", encoding="utf-8", newline="").write(t)
print("applied")
