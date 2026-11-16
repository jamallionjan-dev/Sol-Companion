"""s153 (game side): the settings window shows what the Mind saved after a one-press connection to his own server
(provider Custom, the address that answered, the model), so a later Save keeps it. Wording of the Custom entry.
usage: apply_s153_settings_ui.py <client dir>. Exact old->new; "kept" when already applied."""
import os, sys
CLIENT = sys.argv[1]
NL, CRLF = chr(10), chr(13) + chr(10)
p = os.path.join(CLIENT, "SolSettings.lua")
text = open(p, encoding="utf-8", newline="").read(); nl = CRLF if CRLF in text else NL
def edit(old, new):
    global text
    old, new = old.replace(NL, nl), new.replace(NL, nl)
    if new in text: print("kept SolSettings.lua"); return
    if text.count(old) != 1: raise RuntimeError(("SolSettings.lua", "expected one exact source block", text.count(old), old[:60]))
    text = text.replace(old, new); print("edited SolSettings.lua")
edit('''        s.code = (st.code ~= nil and st.code ~= "") and st.code or (s.status == "ok" and "saved" or "unknown_error")
    end
''', '''        s.code = (st.code ~= nil and st.code ~= "") and st.code or (s.status == "ok" and "saved" or "unknown_error")
        -- s153: the Mind connected to his own server (phone): show what it saved, so Save keeps it
        if (s.code == "models_ok" or s.code == "test_ok") and st.provider == "custom" then
            s.source = "api"; s.provider = "custom"
            if st.base and st.base ~= "" then
                s.base = st.base
                if self.customBaseBox then self.customBaseBox:setText(st.base) end
            end
            if st.model and st.model ~= "" then s.model = st.model end
            self:updateWidgets()
        end
    end
''')
edit('''    { id = "custom", name = "Custom URL (iPhone)" },''', '''    { id = "custom", name = "Phone / own server (iPhone, Android)" },''')
edit('''self:drawText("Custom API URL", RC.customBaseLabel[1]''', '''self:drawText("Address from the phone app (IP:port is enough)", RC.customBaseLabel[1]''')
open(p, "w", encoding="utf-8", newline="").write(text)
print("s153 settings window applied")
