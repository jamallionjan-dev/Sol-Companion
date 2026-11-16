from pathlib import Path
import sys, re

root = Path(r"C:\Users\JAMAL\Desktop\Sol")
work = root / "01_WORK" / "Sol" / "42" / "media" / "lua"
tools = root / "05_TOOLS"
rows = []

def ck(name, cond):
    rows.append((name, bool(cond)))

pages = (work/"client"/"SolPages.lua").read_text(encoding="utf-8", errors="replace")
aui = (work/"client"/"SolArabicUI.lua").read_text(encoding="utf-8", errors="replace")
dlg = (work/"client"/"SCDialogue.lua").read_text(encoding="utf-8", errors="replace")
cmd = (work/"client"/"SCCommands.lua").read_text(encoding="utf-8", errors="replace")
dal = (work/"client"/"SolDialogueArabic.lua").read_text(encoding="utf-8", errors="replace")
py = (tools/"sol_mind"/"sol_link.py").read_text(encoding="utf-8", errors="replace")
js = (tools/"sol_link"/"Sol_Link.user.js").read_text(encoding="utf-8", errors="replace")

ck("tickbox_self_arg6", "a[1], a[2], tb)" in pages)
ck("arabic_ui_v030", 'ARABIC_UI_VERSION = "0.3.0"' in aui)
ck("arabic_module_required", 'require "SolDialogueArabic"' in aui)
ck("arabic_sc_text_global", "local s = U.translate(key, ...)" in aui and "if U.translateDepth > 0 then" not in aui)
ck("dialogue_localizer", "function M.localize(topic, line)" in dal)
ck("dialogue_reverse_map", "ui.solTextOriginal" in dal)

m = re.search(r'function Dialogue\.emitResolved\(actor, topic, line, options\)(.*?)\nend', dlg, re.S)
ck("emit_function_found", bool(m))
if m:
    body = m.group(1)
    ck("emit_localized", "local resolvedLine = line" in body)
    ck("emit_return_localized", "return true, resolvedLine, {" in body)
    ck("emit_native_line_preserved", "utility.say(actor, line)" in body)
    ck("emit_duration_localized", "speechDisplayMillis(resolvedLine)" in body)

ck("talk_localized_before_finish",
   "local transcriptResult = result" in cmd and
   "accepted and transcriptResult or nil" in cmd)

for label, data in (("py", py), ("js", js)):
    ck(label+"_dom_v151",
       "SOL_LINK_DOM_V151" in data and 'document.querySelectorAll("main section")' in data)
    ck(label+"_no_empty_post",
       "SOL_LINK_NO_EMPTY_POST_V151" in data and
       'if (!text) { await req("POST", "/heard", { text: "", diag }); return; }' in data)

ck("py_server_empty_guard",
   "SOL_LINK_EMPTY_GUARD_V151" in py and
   "if not text.strip():" in py and
   "empty_reply" in py)



failed = [n for n,v in rows if not v]
for n,v in rows:
    print(("PASS " if v else "FAIL ") + n)
print(f"TOTAL={len(rows)} PASS={len(rows)-len(failed)} FAIL={len(failed)}")
sys.exit(1 if failed else 0)
