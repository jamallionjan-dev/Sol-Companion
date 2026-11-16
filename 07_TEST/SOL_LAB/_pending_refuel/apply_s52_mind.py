"""Everything she can do goes on the model's card, from one table, and the old word list backs up an "unknown". usage: apply_s52_mind.py <sol_mind dir>"""
import os, re, sys
M = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)
P = os.path.join(M, "model_router.py")
t = open(P, encoding="utf-8", newline="").read()
nl = CRLF if CRLF in t else NL
start = t.index("CARD_ACTIONS = {")
end = t.index("}" + nl, start) + 1 + len(nl)
TABLE = '''CARD_ACTIONS = {
    "sol_headlights": ("ضو السيارة", "شغلي ضو السيارة", "option: on أو off"),
    "sol_toggle_light": ("ضو الغرفة، أقرب مفتاح ضو", "ضوي الغرفة", None),
    "sol_engine": ("محرك السيارة", "شغلي السيارة", "option: on أو off"),
    "sol_horn": ("زمور السيارة", "زمري", "option: once أو drive أو stop"),
    "sol_car_wait": ("تطفي السيارة وتستنى جواها", "طفي السيارة وستنيني", None),
    "sol_gps_clear": ("تشيل الوجهة من الخريطة", "امسحي الوجهة", None),
    "sol_forget": ("تنسى الأوامر اللي فاتت", "انسي اللي قلتو", None),
    "sol_role": ("تشتغل شغلة بالقاعدة", "قطعي حطب", "option: farmer أو woodcutter"),
    "sol_cook": ("تطبخ", "طبخي بيض", "option: شو تطبخ بالإنكليزي مثل egg"),
    "sol_cook_and_serve": ("تطبخ وتجيب الأكل للاعب", "طبخيلي بيض وجيبيلي ياه", "option: شو تطبخ"),
    "sol_plan_cancel": ("تلغي الطبخة أو الخطة الشغالة", "لغي الطبخة", None),
    "sol_eat": ("تاكل من شنطتها", "كلي", None),
    "sol_drink": ("تشرب مي من شنطتها", "اشربي", None),
    "sol_give": ("تعطي اللاعب من أغراضها", "اعطيني مي", "option: all أو mine أو water أو food أو اسم الغرض"),
    "sol_fetch": ("تجيب شي من مكان قريب", "جيبي أكل", "option: food أو water أو book أو book:read"),
    "sol_read": ("تقرأ كتاب من شنطتها", "اقرئي", None),
    "sol_attack_nearest": ("تهاجم أقرب زومبي", "اقتليه", None),
    "guard": ("تحرس المكان", "احرسي", None),
    "hold_fire": ("ما تطلق نار", "لا تطلقي", None),
    "fire_at_will": ("تطلق نار بحرية", "اطلقي النار", None),
    "set_move_mode": ("طريقة مشيها", "اركضي", "option: مشي أو ركض أو تسلل"),
    "set_scavenge": ("تدور على مؤن", "فتشي", "option: on أو off"),
    "sol_equip_best": ("تمسك أحسن سلاح معها", "مسكي سلاحك", "option: melee أو gun"),
    "sol_reload": ("تعبي سلاحها", "ذخري سلاحك", None),
    "sol_bandage_player": ("تضمد جرح اللاعب", "ضمديني", None),
    "sol_replace_bandage": ("تغير ضمادها", "غيري ضمادك", None),
    "sol_take_pill": ("تاخد حبة دوا", "خدي مسكن", "option: اسم الدوا"),
    "sol_go_inside": ("تفوت لأقرب بناية", "فوتي جوا", "option: home للبيت"),
    "sol_goto": ("تمشي لمكان معروف", "روحي عالبيت مشي", "option: اسم المكان"),
    "sol_rest": ("ترتاح على تخت أو بالأرض", "ارتاحي", None),
    "sol_wash": ("تتغسل", "تغسلي", None),
    "sol_fill_water": ("تعبي قنينة مي", "عبي قنينة مي", None),
    "sol_open_door": ("تفتح أقرب باب", "افتحي الباب", None),
    "sol_close_door": ("تسكر أقرب باب", "سكري الباب", None),
    "sol_open_window": ("تفتح أو تسكر أقرب شباك", "افتحي الشباك", None),
    "sol_stove_on": ("تشغل الغاز", "شغلي الغاز", None),
    "sol_stove_off": ("تطفي الغاز", "طفي الغاز", None),
}
# reported by the game but not orders: panel settings, or the same thing as a card line, or used only by the Mind
NOT_ORDERS = {"sol_fuel", "sol_plan_status", "sol_drive", "sol_take_wheel", "board_vehicle", "exit_vehicle", "sol_sit_beside", "open_inventory", "bandage", "set_hold_fire", "set_follow_fan_out", "set_allow_overload", "set_ride_with_player"}
'''.replace(NL, nl)
t = t[:start] + TABLE + t[end:]
a = '''    known = {a.get("id") for a in actions or [] if a.get("enabled", True)}
    for cid, (meaning, phrase, note) in CARD_ACTIONS.items():
        if cid in known or not actions:
            lines.append('''.replace(NL, nl)
b = '''    for cid, (meaning, phrase, note) in CARD_ACTIONS.items():
        if True:
            lines.append('''.replace(NL, nl)
assert t.count(a) == 1
t = t.replace(a, b)
compile(t, P, "exec")
C = os.path.join(M, "chat_service.py")
c = open(C, encoding="utf-8", newline="").read()
cn = CRLF if CRLF in c else NL
a1 = '''        ids = {a.get("id") for a in acts if a.get("enabled", True)}
'''.replace(NL, cn)
b1 = '''        ids = {a.get("id") for a in acts} | set(MR.CARD_ACTIONS)                  # not "enabled now": the game says itself why something cannot be done
'''.replace(NL, cn)
a2 = '''        if action == "unknown" or (action != "none" and action not in MR.COMMANDS and action not in ids):
'''.replace(NL, cn)
b2 = '''        if action == "unknown":
            for aid, opt in action_intents(text) or []:                          # the model did not place it: the plain word list still knows these
                r = resolve_and_run(self.dir, aid, opt, mem, snap)
                self._remember_action(aid, opt)
                done_line("wordlist", aid, "accepted", r)
                return action_receipt_note(r) or random.choice(("تكرم.", "ماشي."))
''' + a2.replace(cn, NL)
b2 = b2.replace(NL, cn)
for x, y in ((a1, b1), (a2, b2)):
    assert c.count(x) == 1, x[:60]
    c = c.replace(x, y)
compile(c, C, "exec")
open(P, "w", encoding="utf-8", newline="").write(t)
open(C, "w", encoding="utf-8", newline="").write(c)
print("applied")
