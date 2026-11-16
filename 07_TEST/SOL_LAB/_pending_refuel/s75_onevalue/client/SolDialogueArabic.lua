-- SolDialogueArabic.lua - v0.9.4
-- Central Arabic localization bridge for Sol / Living Fellows dialogue.
-- ASCII-only source: Arabic is stored as \uXXXX escapes for SolText.
SolDialogueArabic = SolDialogueArabic or {}
local M = SolDialogueArabic

local exact = nil
local patterns = nil
local cache = {}
local cacheCount = 0

local fallback = {
    ["vehicle.hotwire.success"] = "\u0627\u0634\u062A\u063A\u0644\u062A. \u0627\u0644\u0633\u064A\u0627\u0631\u0629 \u062C\u0627\u0647\u0632\u0629\u060C \u064A\u0644\u0627 \u0646\u062A\u062D\u0631\u0643.",
    ["vehicle.hotwire.failure"] = "\u0645\u0627 \u0632\u0628\u0637\u062A \u0647\u0627\u0644\u0645\u0631\u0629. \u062E\u0644\u064A\u0646\u064A \u0623\u0631\u062C\u0639 \u0623\u062C\u0631\u0628 \u0644\u0645\u0627 \u064A\u0643\u0648\u0646 \u0627\u0644\u0648\u0636\u0639 \u0623\u0647\u062F\u0649.",
    ["downtime.tv.learn"] = "\u0627\u0633\u062A\u0646\u064A \u0634\u0648\u064A\u060C \u0647\u0627\u0644\u0645\u0639\u0644\u0648\u0645\u0629 \u0645\u0645\u0643\u0646 \u062A\u0641\u064A\u062F\u0646\u0627. \u062E\u0644\u064A\u0646\u064A \u0623\u0631\u0643\u0632 \u0641\u064A\u0647\u0627.",
    ["downtime.tv.comment"] = "\u063A\u0631\u064A\u0628 \u0646\u0634\u0648\u0641 \u0634\u064A \u0645\u0646 \u0627\u0644\u062D\u064A\u0627\u0629 \u0627\u0644\u0642\u062F\u064A\u0645\u0629 \u0643\u0623\u0646\u0647 \u0645\u0627 \u062A\u063A\u064A\u0631 \u0634\u064A\u0621.",
    ["fishing.cast"] = "\u0631\u0645\u064A\u062A \u0627\u0644\u0633\u0646\u0627\u0631\u0629. \u0647\u0644\u0623 \u0628\u062F\u0646\u0627 \u0634\u0648\u064A\u0629 \u0635\u0628\u0631.",
    ["fishing.bite"] = "\u0641\u064A \u0634\u064A \u0639\u0645 \u064A\u0633\u062D\u0628! \u062E\u0644\u064A\u0646\u064A \u0623\u0645\u0633\u0643\u0647\u0627 \u0628\u0647\u062F\u0648\u0621.",
    ["fishing.catch"] = "\u0645\u0633\u0643\u062A\u0647\u0627! \u0645\u0645\u062A\u0627\u0632\u060C \u0635\u0627\u0631 \u0639\u0646\u0627 \u0623\u0643\u0644 \u0632\u064A\u0627\u062F\u0629.",
    ["fishing.lost"] = "\u0631\u0627\u062D\u062A \u0645\u0646\u064A. \u0628\u0633\u064A\u0637\u0629\u060C \u0645\u0646\u062C\u0631\u0628 \u0645\u0631\u0629 \u062B\u0627\u0646\u064A\u0629.",
    ["fishing.trash"] = "\u0645\u0648 \u0633\u0645\u0643\u0629... \u0637\u0644\u0639\u062A \u062E\u0631\u062F\u0629. \u0628\u0646\u0638\u0641 \u0627\u0644\u0633\u0646\u0627\u0631\u0629 \u0648\u0645\u0646\u0639\u064A\u062F.",
    ["reading.choose"] = "\u0644\u0642\u064A\u062A \u0634\u064A \u064A\u0633\u062A\u0627\u0647\u0644 \u0627\u0644\u0642\u0631\u0627\u0621\u0629. \u0631\u062D \u0622\u062E\u062F\u0647 \u0645\u0639\u064A \u0648\u0623\u0631\u062C\u0639\u0647 \u0644\u0645\u0627 \u0623\u062E\u0644\u0635.",
    ["reading.progress"] = "\u0627\u0644\u0643\u062A\u0627\u0628 \u0639\u0645 \u064A\u062E\u0644\u064A\u0646\u064A \u0623\u0641\u0643\u0631. \u0628\u062F\u064A \u0623\u0643\u0645\u0644 \u0634\u0648\u064A \u0642\u0628\u0644 \u0645\u0627 \u0623\u062D\u0643\u0645 \u0639\u0644\u064A\u0647.",
    ["reading.finished"] = "\u062E\u0644\u0635\u062A\u0647. \u0641\u064A \u0643\u0645 \u0641\u0643\u0631\u0629 \u0641\u064A\u0647 \u062A\u0633\u062A\u0627\u0647\u0644 \u0646\u0631\u062C\u0639 \u0646\u062D\u0643\u064A \u0639\u0646\u0647\u0627.",
    ["reading.philosophy"] = "\u0623\u062D\u064A\u0627\u0646\u064B\u0627 \u0627\u0644\u0643\u0644\u0627\u0645 \u0627\u0644\u0628\u0633\u064A\u0637 \u0628\u064A\u062E\u0644\u064A\u0646\u0627 \u0646\u0641\u0643\u0631 \u0628\u0623\u0634\u064A\u0627\u0621 \u0623\u0643\u0628\u0631 \u0645\u0646 \u0627\u0644\u0644\u064A \u0642\u062F\u0627\u0645\u0646\u0627.",
    ["banter.interior.dread"] = "\u0641\u064A \u0634\u064A \u0628\u0647\u0627\u0644\u0645\u0643\u0627\u0646 \u0645\u0648 \u0645\u0631\u064A\u062D\u0646\u064A. \u062E\u0644\u064A\u0643 \u0642\u0631\u064A\u0628 \u0648\u062E\u0644\u064A\u0646\u0627 \u0646\u0646\u062A\u0628\u0647 \u0644\u0644\u0632\u0648\u0627\u064A\u0627.",
    ["banter.interior.panic_onset"] = "\u0627\u0633\u062A\u0646\u0649 \u0634\u0648\u064A... \u0646\u0641\u0633\u064A \u0633\u0631\u064A\u0639 \u0648\u0625\u064A\u062F\u064A \u0639\u0645 \u062A\u0631\u062C\u0641. \u062E\u0644\u064A\u0643 \u0642\u0631\u064A\u0628 \u0645\u0646\u064A.",
    ["banter.interior.panic_recovery"] = "\u062A\u0645\u0627\u0645\u060C \u0631\u062C\u0639 \u0646\u0641\u0633\u064A \u0637\u0628\u064A\u0639\u064A. \u0623\u0646\u0627 \u062C\u0627\u0647\u0632\u0629 \u0646\u0643\u0645\u0644.",
    ["banter.interior.nicotine"] = "\u0623\u0639\u0635\u0627\u0628\u064A \u0645\u0634\u062F\u0648\u062F\u0629 \u0634\u0648\u064A. \u0625\u0630\u0627 \u0644\u0642\u064A\u0646\u0627 \u062F\u062E\u0627\u0646 \u0628\u0627\u0644\u0637\u0631\u064A\u0642 \u062E\u0628\u0631\u0646\u064A.",
}

local broad = {
    { "^vehicle%.", "\u062A\u0645\u0627\u0645\u060C \u0623\u0646\u0627 \u0645\u0646\u062A\u0628\u0647\u0629 \u0644\u0644\u0633\u064A\u0627\u0631\u0629. \u062E\u0644\u064A\u0646\u0627 \u0646\u062A\u0635\u0631\u0641 \u062E\u0637\u0648\u0629 \u062E\u0637\u0648\u0629." },
    { "^downtime%.", "\u0645\u0646\u064A\u062D \u0646\u0627\u062E\u062F \u0644\u062D\u0638\u0629 \u0647\u062F\u0648\u0621. \u0623\u0646\u0627 \u0628\u062E\u064A\u0631." },
    { "^fishing%.", "\u062E\u0644\u064A\u0646\u0627 \u0646\u0647\u062F\u0649 \u0648\u0646\u062C\u0631\u0628 \u0645\u0631\u0629 \u062B\u0627\u0646\u064A\u0629." },
    { "^reading%.", "\u0627\u0644\u0642\u0631\u0627\u0621\u0629 \u0639\u0645 \u062A\u0639\u0637\u064A\u0646\u064A \u0634\u064A \u0623\u0641\u0643\u0631 \u0641\u064A\u0647." },
    { "^banter%.", "\u0623\u0646\u0627 \u0647\u0648\u0646 \u0645\u0639\u0643. \u0627\u0644\u062D\u0643\u064A \u0634\u0648\u064A \u0628\u064A\u062E\u0641\u0641 \u062B\u0642\u0644 \u0647\u0627\u0644\u062F\u0646\u064A\u0627." },
    { "^player_hit%.", "\u0627\u0646\u062A\u0628\u0650\u0647! \u0623\u0646\u0627 \u0645\u0639\u0643\u060C \u0644\u0627 \u062A\u0636\u0631\u0628\u0646\u064A \u0628\u0627\u0644\u063A\u0644\u0637." },
    { "^danger%.", "\u0641\u064A \u062E\u0637\u0631 \u0642\u0631\u064A\u0628. \u062E\u0644\u064A\u0643 \u0645\u0646\u062A\u0628\u0647 \u0648\u0623\u0646\u0627 \u0645\u0639\u0643." },
    { "^combat%.", "\u0623\u0646\u0627 \u062C\u0627\u0647\u0632\u0629. \u062E\u0644\u064A\u0646\u0627 \u0646\u0646\u0647\u064A \u0627\u0644\u062E\u0637\u0631 \u0628\u062F\u0648\u0646 \u062A\u0647\u0648\u0631." },
    { "^stress%.", "\u0623\u062D\u062A\u0627\u062C \u062F\u0642\u064A\u0642\u0629 \u0623\u0631\u062A\u0628 \u0623\u0641\u0643\u0627\u0631\u064A\u060C \u0648\u0628\u0639\u062F\u0647\u0627 \u0646\u0643\u0645\u0644." },
    { "^joy%.", "\u0647\u0627\u064A \u0623\u062D\u0633\u0646 \u0623\u062E\u0628\u0627\u0631 \u0633\u0645\u0639\u062A\u0647\u0627 \u0645\u0646 \u0641\u062A\u0631\u0629." },
    { "^grief%.", "\u0644\u0633\u0647 \u0627\u0644\u0645\u0648\u0636\u0648\u0639 \u0645\u0648\u062C\u0639\u0646\u064A. \u0628\u0633 \u0623\u0646\u0627 \u0645\u0648\u062C\u0648\u062F\u0629 \u0645\u0639\u0643." },
    { "^lastwords%.", "\u0625\u0630\u0627 \u0635\u0627\u0631 \u0627\u0644\u0623\u0633\u0648\u0623\u060C \u0644\u0627 \u062A\u0646\u0633\u0627\u0646\u064A. \u0628\u0633 \u0644\u0633\u0647 \u0645\u0627 \u062E\u0644\u0635\u0646\u0627." },
    { "^work%.", "\u062E\u0644\u064A\u0646\u064A \u0623\u062E\u0644\u0635 \u0647\u0627\u0644\u0634\u063A\u0644\u0629 \u0623\u0648\u0644\u060C \u0648\u0628\u0639\u062F\u0647\u0627 \u0645\u0646\u0642\u0631\u0631 \u0627\u0644\u062E\u0637\u0648\u0629 \u0627\u0644\u062C\u0627\u064A\u0629." },
    { "^supply%.", "\u062E\u0644\u064A\u0646\u0627 \u0646\u0634\u0648\u0641 \u0634\u0648 \u0646\u0627\u0642\u0635\u0646\u0627 \u0648\u0646\u0631\u062A\u0628 \u0623\u063A\u0631\u0627\u0636\u0646\u0627." },
    { "^needs%.", "\u0641\u064A \u0634\u063A\u0644\u0629 \u0645\u062D\u062A\u0627\u062C\u062A\u0647\u0627. \u062E\u0644\u064A\u0646\u0627 \u0646\u0623\u0645\u0646\u0647\u0627 \u0644\u0645\u0627 \u064A\u0635\u064A\u0631 \u0627\u0644\u0637\u0631\u064A\u0642 \u0622\u0645\u0646." },
    { "^team%.", "\u0623\u0646\u0627 \u0645\u0639 \u0627\u0644\u0641\u0631\u064A\u0642. \u0642\u0644 \u0644\u064A \u0634\u0648 \u0627\u0644\u062E\u0637\u0629." },
    { "^rescue%.", "\u0623\u0646\u0627 \u062C\u0627\u064A\u0629 \u0644\u0639\u0646\u062F\u0643. \u0627\u0628\u0642\u064E \u0628\u0645\u0643\u0627\u0646 \u0622\u0645\u0646 \u0642\u062F\u0631 \u0645\u0627 \u062A\u0642\u062F\u0631." },
    { "^weather%.", "\u0627\u0644\u062C\u0648 \u0639\u0645 \u064A\u062A\u063A\u064A\u0631. \u062E\u0644\u064A\u0646\u0627 \u0646\u0636\u0644 \u0645\u0646\u062A\u0628\u0647\u064A\u0646." },
    { "^ambient%.", "\u0643\u0644 \u0634\u064A\u0621 \u0647\u0627\u062F\u0626 \u062D\u0627\u0644\u064A\u064B\u0627. \u0623\u0646\u0627 \u0645\u0646\u062A\u0628\u0647\u0629." },
    { "^medical%.", "\u062E\u0644\u064A\u0646\u0627 \u0646\u0647\u062A\u0645 \u0628\u0627\u0644\u0625\u0635\u0627\u0628\u0629 \u0642\u0628\u0644 \u0645\u0627 \u062A\u0633\u0648\u0621." },
    { "^nickname%.", "\u0627\u0644\u0627\u0633\u0645 \u0645\u0648 \u0627\u0644\u0645\u0647\u0645... \u0627\u0644\u0645\u0647\u0645 \u0645\u064A\u0646 \u0648\u0627\u0642\u0641 \u0645\u0639\u0643 \u0648\u0642\u062A \u0627\u0644\u0634\u062F\u0629." },
    { "^conversation%.", "\u0623\u0646\u0627 \u0645\u0639\u0643. \u062E\u0644\u064A\u0646\u0627 \u0646\u062D\u0643\u064A \u0628\u0647\u062F\u0648\u0621." },
}

local defaultLine = "\u0623\u0646\u0627 \u0645\u0639\u0643. \u062E\u0644\u064A\u0646\u0627 \u0646\u0643\u0645\u0644 \u0628\u0647\u062F\u0648\u0621."

local function escPattern(s)
    return (string.gsub(s, "([%(%)%.%%%+%-%*%?%[%]%^%$])", "%%%1"))
end

local function templatePattern(template)
    local out, slots, pos = { "^" }, {}, 1
    while true do
        local a, b, n = string.find(template, "%%(%d)", pos)
        if not a then
            out[#out + 1] = escPattern(string.sub(template, pos))
            break
        end
        out[#out + 1] = escPattern(string.sub(template, pos, a - 1))
        out[#out + 1] = "(.-)"
        slots[#slots + 1] = tonumber(n)
        pos = b + 1
    end
    out[#out + 1] = "$"
    return table.concat(out), slots
end

local function fillArabic(template, slots, captures)
    return (string.gsub(template, "%%(%d)", function(n)
        local wanted = tonumber(n)
        for i = 1, #slots do
            if slots[i] == wanted then return tostring(captures[i] or "") end
        end
        return "%" .. n
    end))
end

-- how many placeholders (%1..%9) a text has, so a template is fetched with its own placeholders as arguments
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
    exact, patterns = {}, {} if SolDialogueLines and SolDialogueLines.merge then SolDialogueLines.merge(exact, patterns, templatePattern) end
    local sc = SurvivorCompanion
    local ui = type(sc) == "table" and sc.UI or nil
    local original = type(ui) == "table" and ui.solTextOriginal or nil
    if type(original) ~= "function" or type(SolLF_AR) ~= "table" then return end
    for key, ar in pairs(SolLF_AR) do
        local ok, en = false, nil
        if type(ar) == "string" then ok, en = englishTemplate(original, key, ar) end
        if ok and type(en) == "string" and en ~= "" and en ~= key and type(ar) == "string" then
            if string.find(en, "%%[1-9]") then
                local p, slots = templatePattern(en)
                patterns[#patterns + 1] = { pattern = p, slots = slots, ar = ar }
            else
                exact[en] = ar
            end
        end
    end
end

local function fallbackFor(topic)
    topic = tostring(topic or "")
    if fallback[topic] then return fallback[topic] end
    for i = 1, #broad do
        if string.find(topic, broad[i][1]) then return broad[i][2] end
    end
    return defaultLine
end

function M.localize(topic, line)
    if type(line) ~= "string" or line == "" then return line, "invalid" end
    if string.find(line, "\\u06", 1, true) or string.find(line, "\\uFB", 1, true) then
        return line, "already_arabic"
    end
    local cached = cache[line]
    if cached ~= nil then return cached, "cache" end
    build()
    local result = exact and exact[line] or nil
    if result == nil and patterns then
        for i = 1, #patterns do
            local p = patterns[i]
            local captures = { string.match(line, p.pattern) }
            if captures[1] ~= nil then
                result = fillArabic(p.ar, p.slots, captures)
                break
            end
        end
    end
    -- No real translation: keep the authored English line. The old topic
    -- fallback replaced every untranslated sentence with one generic Arabic
    -- line, so Sol appeared to say the same thing all the time, and those
    -- fallback strings used \u escapes that Lua 5.1 does not decode, which is
    -- what printed raw "u0623..." in the window.
    if result == nil then if SolDialogueLines and SolDialogueLines.miss then SolDialogueLines.miss(topic, line) end
        cache[line] = line
        cacheCount = cacheCount + 1
        if cacheCount > 2048 then cache, cacheCount = {}, 0 end
        return line, "no_translation"
    end
    cache[line] = result
    cacheCount = cacheCount + 1
    if cacheCount > 2048 then cache, cacheCount = {}, 0 end
    return result, "exact"
end

function M.reset()
    exact, patterns, cache, cacheCount = nil, nil, {}, 0
end

return M
