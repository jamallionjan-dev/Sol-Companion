"""s96 leg_yield (switch place_leg_arrive): a leg walk yields only to a NEW order, not to the same standing order.
Live 2026-11-11 10:36-10:37 (DebugLog 2026-11-11_10-19): "رتّبي الأغراض" at home. Sol is a resident on base_duty; SolSort's walks
go through SolPlace legs while Living Fellows' order stays "base_duty" and its command serial moves on its own (duty work).
s85's yield rule (order not move_to + serial moved) read that as "someone else ordered her":
  10:37:31.583 / 10:37:38.358 / 10:37:41.772  [SolPlace] walk to 7427,8238 ended by another order (base_duty): not walked again
  10:36:48.718 / 10:37:34.998  [SolSort] cannot reach cardboardbox 7405,8250 / crate 7426,8238 after 2 attempts
With the fix: sendLeg also remembers LF's order name; a leg yields only when the order name changed since the leg was sent
(his "stay" during a move_to leg, or any order replacing base_duty). The same order with a new serial goes on walking.
Switch off: SolPlace exactly as before s85. Needs s85 applied. Game closed only. In place, idempotent.
usage: apply_s96_leg_yield.py <client dir>"""
import os, sys
CL = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)
def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: print("kept " + new[:60]); return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:80])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new)); print("edited " + new[:60])
P = os.path.join(CL, "SolPlace.lua")
edit(P, "if plaOn() then local _, serial = lfOrder(solActor()); R.serial = serial end",
        "if plaOn() then local o_, serial = lfOrder(solActor()); R.serial = serial; R.order = o_ end   -- s96: and the order's name")
edit(P, "local foreign = order ~= nil and order ~= \"move_to\" and R.serial ~= nil and serial ~= nil and serial ~= R.serial" + NL,
        "local foreign = order ~= nil and order ~= \"move_to\" and R.serial ~= nil and serial ~= nil and serial ~= R.serial" + NL +
        "        and (R.order == nil or order ~= R.order)   -- s96 leg_yield: the same standing order (base_duty) with a new serial is not a new order" + NL)
print("s96 leg_yield applied")
