"""Run only after the game is closed. Everything Sol says above her head is Arabic, or she says nothing: her line goes to her own bubble, never the game's English one.
Also stops the 307 "Missing arguments" warnings: the English templates are fetched with their own placeholders as arguments.
usage: apply_s34_lua.py <SCGameplayUtil.lua> <SCDialogue.lua> <SolDialogueArabic.lua> [<destination SolSpeechAR.lua>]"""
import os, shutil, sys
def patch(p, pairs):
    t = open(p, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    for a, b, *n in pairs:
        a, b = a.replace("\n", nl), b.replace("\n", nl)
        assert t.count(a) == (n[0] if n else 1), (p, a[:70], t.count(a))
        t = t.replace(a, b)
    open(p, "w", encoding="utf-8", newline="").write(t)
    print("applied to", p)
patch(sys.argv[1], [
("""    local line = tostring(textValue)
    local duration = U.speechDisplayMillis(line)
    if SolBubble and SolBubble.speak and SolBubble.speak(actor, line, duration) then return true end
""", """    local line = tostring(textValue)
    -- Sol: Arabic or nothing above her head. Her bubble is SolBubble; the game's own font cannot draw Arabic.
    if SolSpeechAR and type(SolSpeechAR.overhead) == "function" and SolSpeechAR.isSol(actor) then
        return SolSpeechAR.overhead(actor, line, U.speechDisplayMillis) == true
    end
    local duration = U.speechDisplayMillis(line)
    if SolBubble and SolBubble.speak and SolBubble.speak(actor, line, duration) then return true end
"""),
])
patch(sys.argv[2], [
("""    -- Native PZ ChatElement does not reliably render Arabic glyphs.
    -- Sol's custom transcript receives resolvedLine; native overhead stays authored.
    local overhead = utility and type(utility.say) == "function"
        and utility.say(actor, line) == true
""", """    -- Native PZ ChatElement cannot draw Arabic glyphs. For Sol the line above her head is the
    -- Arabic one: its translation, a short line for this topic, or nothing (SolSpeechAR). Other
    -- companions keep the authored line.
    local overheadLine = line
    if SolSpeechAR and type(SolSpeechAR.resolve) == "function" and SolSpeechAR.isSol(actor) then
        overheadLine = SolSpeechAR.resolve(actor, topic, resolvedLine)
        if overheadLine then resolvedLine = overheadLine end
    end
    local overhead = overheadLine ~= nil and utility and type(utility.say) == "function"
        and utility.say(actor, overheadLine) == true
"""),
])
patch(sys.argv[3], [
("""local function build()
    if exact ~= nil then return end
""", """-- how many placeholders (%1..%9) a text has, so a template is fetched with its own placeholders as arguments
local function placeholderCount(s)
    local top = 0
    for digit in string.gmatch(s, "%%(%d)") do
        local n = tonumber(digit)
        if n and n > top then top = n end
    end
    return top
end

-- the game's getText logs a "Missing arguments" warning for every template asked for without arguments
local function englishTemplate(original, key, ar)
    local top = placeholderCount(ar)
    if top == 0 then return pcall(original, key) end
    if top == 1 then return pcall(original, key, "%1") end
    if top == 2 then return pcall(original, key, "%1", "%2") end
    if top == 3 then return pcall(original, key, "%1", "%2", "%3") end
    if top == 4 then return pcall(original, key, "%1", "%2", "%3", "%4") end
    return false, nil                                                       -- more than getText takes (screen rows only)
end

local function build()
    if exact ~= nil then return end
"""),
("""        local ok, en = pcall(original, key)
""", """        local ok, en = false, nil
        if type(ar) == "string" then ok, en = englishTemplate(original, key, ar) end
"""),
])
if len(sys.argv) > 4:
    src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "SolSpeechAR.lua")
    shutil.copy(src, sys.argv[4]); print("copied", src, "->", sys.argv[4])
