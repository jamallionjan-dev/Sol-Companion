"""secret_loadout: "عطيني سلاحي السري" -> Sol puts exact copies of Jamal's two firearms into HER inventory: every part installed
(EFZ's own build code + TWRuntime.applyTree, or the vanilla parts), the magazine full, a round chambered, his spare magazines full,
and 500 rounds of each weapon's own round. The loadout is global: the shipped SolSecretLoadoutData.lua (media/lua/shared), else
Sol_SecretLoadout.txt in the Zomboid/Lua folder, else captured once, silently, the next time he carries two firearms. No save order,
not in any panel or help; her death does not touch it (no ModData, no forget hook in SolLife). Game closed only.
In place and idempotent: every edit is skipped when it is already there.
  Lua : SolSecretLoadout.lua copied; SolSecretLoadoutData.lua into ../shared (never an empty one over a filled one);
        switch "secret_loadout" in SolAuthority.A.FIXES and secret_loadout=on in SolFixes_LAB.txt; a keep note in SolLife's death wipe.
  Mind: chat_service.py one VERB_MAP line (sol_secret give) and secret_reply (her line from the game's answer only);
        model_router.py one card action secret_loadout with its examples.
usage: apply_s74_secret_loadout.py <client dir> <sol_mind dir>      (either may be '-' to skip that side)"""
import os, shutil, sys
CL, MIND = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
NL, CRLF = chr(10), chr(13) + chr(10)

def edit(path, old, new):
    t = open(path, encoding="utf-8", newline="").read()
    nl = CRLF if CRLF in t else NL
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in t: return
    assert t.count(old) == 1, (os.path.basename(path), t.count(old), old[:70])
    open(path, "w", encoding="utf-8", newline="").write(t.replace(old, new))

def has_lines(path):
    if not os.path.exists(path): return False
    return '"w1.type=' in open(path, encoding="utf-8", errors="replace").read()

if CL != "-":
    src = open(os.path.join(HERE, "SolSecretLoadout.lua"), encoding="ascii").read()
    assert 'M.VERSION = "0.1.0"' in src
    shutil.copy(os.path.join(HERE, "SolSecretLoadout.lua"), os.path.join(CL, "SolSecretLoadout.lua"))
    shared = os.path.normpath(os.path.join(CL, "..", "shared"))
    os.makedirs(shared, exist_ok=True)
    data_src, data_dst = os.path.join(HERE, "SolSecretLoadoutData.lua"), os.path.join(shared, "SolSecretLoadoutData.lua")
    if not os.path.exists(data_dst) or (has_lines(data_src) and open(data_src, encoding="ascii").read() != open(data_dst, encoding="utf-8").read()):
        shutil.copy(data_src, data_dst)                                       # a folded (filled) staged file replaces; an empty one never does
    A = os.path.join(CL, "SolAuthority.lua")
    if '"secret_loadout"' not in open(A, encoding="utf-8").read():
        edit(A, "A.FIXES = {" + NL, "A.FIXES = {" + NL + '    "secret_loadout",' + NL)
    life = os.path.join(CL, "SolLife.lua")
    if os.path.exists(life):
        edit(life, '    if type(forgetBook) == "function" then pcall(forgetBook) end' + NL,
             '    if type(forgetBook) == "function" then pcall(forgetBook) end' + NL +
             "    -- secret_loadout is kept on purpose: shipped data + Sol_SecretLoadout.txt, no ModData, no forget hook (SolSecretLoadout.KEEP_ON_DEATH)" + NL)
    fix = os.path.join(CL, "..", "..", "..", "..", "..", "..", "Lua", "SolFixes_LAB.txt")
    if os.path.exists(fix) and "secret_loadout=" not in open(fix, encoding="utf-8").read():
        with open(fix, "a", encoding="utf-8", newline="") as h: h.write("secret_loadout=on" + CRLF)

if MIND != "-":
    CS = os.path.join(MIND, "chat_service.py")
    give_all = '    (r"(أعطيني|اعطيني|ناوليني|هاتي|رجعي لي|أرجعي لي|ارجعي لي)\\s*(كل شيء|كل شي|كلشي|كل ما معك|كل ما في حقيبتك|الكل)", ("sol_give", "all")),' + NL
    secret = ('    (r"(?:سلاح(?:ي|اتي)|(?:ا|أ|إ)?سلحتي|(?:ال)?سلاح(?:ين)?)\\s+(?:ال)?سرّ?(?:ي|يّ)(?:ة|ه|ين|يين)?(?![\\u0621-\\u064A])", ("sol_secret", "give")),'
              '   # secret_loadout' + NL)
    edit(CS, give_all, secret + give_all)
    edit(CS, "def role_reply(option, r):" + NL,
         "def secret_reply(r):" + NL +
         '    """secret_loadout: her answer from the game\'s reply only (the model never words it)."""' + NL +
         '    if not isinstance(r, dict) or r.get("ok") is None: return "لحظة."' + NL +
         '    reason = str(r.get("reason") or "")' + NL +
         '    if r.get("ok") and reason.startswith("given:"):' + NL +
         '        head, _, rest = reason.partition(";")' + NL +
         '        kv = dict(p.partition("=")[::2] for p in rest.split(";") if p)' + NL +
         '        line = "تكرم، السلاحين معي." if head == "given:2" else "تكرم، سلاح واحد معي، التاني ما زبط معي هلأ."' + NL +
         '        if kv.get("heavy") == "1": line += " بس صرت شايلة تقيل كتير."' + NL +
         '        return line' + NL +
         '    if reason == "no_sol": return "ما فيني هلأ، استنى شوي."' + NL +
         '    if reason == "failed": return "ما زبط معي هلأ، جرب كمان شوي."' + NL +
         '    return "مش لاقية شي بهالاسم هلأ."' + NL + NL +
         "def role_reply(option, r):" + NL)
    edit(CS, '                if args["action"] == "sol_role": self._forced = role_reply(args.get("option"), r)' + NL,
         '                if args["action"] == "sol_role": self._forced = role_reply(args.get("option"), r)' + NL +
         '                if args["action"] == "sol_secret": self._forced = secret_reply(r)' + NL)
    MR = os.path.join(MIND, "model_router.py")
    edit(MR, '    "why":           ("يسأل ليش فشل آخر شي", None),' + NL,
         '    "why":           ("يسأل ليش فشل آخر شي", None),' + NL +
         '    "secret_loadout": ("تعطيه نسخة من سلاحه السري: سلاحين بكل قطعهن ومخازن مليانة وذخيرة", "عطيني سلاحي السري"),' + NL)
    edit(MR, '("عنا شو بالمكان", "survey"))' + NL,
         '("عنا شو بالمكان", "survey"),' + NL +
         '            ("جيبيلي سلاحي السري", "secret_loadout"), ("بدي أسلحتي السرية", "secret_loadout"))' + NL)
print("applied")
