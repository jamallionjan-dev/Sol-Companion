"""Run only after the game is closed. A long list costs only the rows on screen; capacity is not pushed past what the game allows; the action list is written at most once every few seconds.
usage: apply_s12_lua.py <SolChat.lua> <SolCarry.lua> <SolActions.lua>"""
import sys
def patch(p, pairs):
    t = open(p, encoding="utf-8", newline="").read()
    nl = "\r\n" if "\r\n" in t else "\n"
    for a, b in pairs:
        a, b = a.replace("\n", nl), b.replace("\n", nl)
        assert t.count(a) == 1, (p, a[:70], t.count(a))
        t = t.replace(a, b)
    open(p, "w", encoding="utf-8", newline="").write(t)
    print("applied to", p)
patch(sys.argv[1], [
("""            -- Itemized supplies table built from game data: item ; quantity ; category/location ; neutral colour.
            local rows, cur = {}, {}
""", """            -- Itemized supplies table built from game data: item ; quantity ; category/location ; neutral colour.
            local sum = #m.cps
            for i = 1, math.min(#m.cps, 256) do sum = (sum * 31 + m.cps[i]) % 1000000007 end
            local cacheKey = tostring(W) .. ":" .. tostring(#m.cps) .. ":" .. tostring(sum)
            self.cardCache = self.cardCache or {}
            local known = self.cardCache[cacheKey]
            if known then
                items[#items + 1] = { m = m, card = known.rows, y = y, w = known.w, h = known.h }
                y = y + known.h + GAP
            else
            local rows, cur = {}, {}
"""),
("""                local rowH = math.max(28, lineCount * 17 + 11)
                cardRows[#cardRows + 1] = { name = nameLines, count = count, detail = detailLines, color = color, h = rowH }
                h = h + rowH
            end
            items[#items + 1] = { m = m, card = cardRows, y = y, w = w, h = h }
            y = y + h + GAP
        else
""", """                local rowH = math.max(28, lineCount * 17 + 11)
                local colName = ""
                for _, cp in ipairs(color) do colName = colName .. string.char(cp) end
                cardRows[#cardRows + 1] = { name = nameLines, count = count, detail = detailLines, colName = colName, h = rowH, top = h - 16 }
                h = h + rowH
            end
            self.cardCache[cacheKey] = { rows = cardRows, w = w, h = h }
            items[#items + 1] = { m = m, card = cardRows, y = y, w = w, h = h }
            y = y + h + GAP
            end
        else
"""),
("""            local rowY = y + 8
            local nameW, countW = 200, 52
""", """            local nameW, countW = 200, 52
"""),
("""            for i, row in ipairs(it.card) do
                local ry = rowY
                if i > 1 then rect(self, x + 8, ry - 2, it.w - 16, 1, C.solLine) end
                local nameLines, count, detail, col = row.name or {}, row.count or {}, row.detail or {}, row.color or {}
                local colName = ""
                for _, cp in ipairs(col) do colName = colName .. string.char(cp) end
                local cc = COL[colName] or C.muted
""", """            -- only the rows inside the window: a table of hundreds costs the same as a table of twenty
            local card, low, high, listBottom = it.card, 1, #it.card, L[2] + L[4]
            while low < high do
                local mid = math.floor((low + high) / 2)
                if y + 8 + card[mid].top + card[mid].h < L[2] then low = mid + 1 else high = mid end
            end
            for i = low, #card do
                local row = card[i]
                local ry = y + 8 + row.top
                if ry > listBottom then break end
                if i > 1 then rect(self, x + 8, ry - 2, it.w - 16, 1, C.solLine) end
                local nameLines, count, detail = row.name or {}, row.count or {}, row.detail or {}
                local cc = COL[row.colName] or C.muted
"""),
("""                    T.drawLine(self, line, detailX, detailY + (lineNo - 1) * 17, detailW, { scale = 0.44, align = "right", r = cc[1], g = cc[2], b = cc[3] })
                end
                rowY = rowY + row.h
            end
""", """                    T.drawLine(self, line, detailX, detailY + (lineNo - 1) * 17, detailW, { scale = 0.44, align = "right", r = cc[1], g = cc[2], b = cc[3] })
                end
            end
"""),
])
patch(sys.argv[2], [
("""        if (usable(readings(s)) or 0) < want then call(inv, "setCapacity", want) end
""", """        local limit = math.min(want, 100)                                       -- the game refuses more than 100, and writes a warning each time it is asked
        local nowR = readings(s)
        if (usable(nowR) or 0) < want and (nowR.cap or 0) < limit then call(inv, "setCapacity", limit) end
"""),
("""    local ok = (r.max or 0) >= want and (usable(r) or 0) >= want
""", """    local ok = (r.max or 0) >= want and (usable(r) or 0) >= math.min(want, 100)
"""),
])
patch(sys.argv[3], [
("""    log(tostring(t.action) .. " " .. tostring(t.option or "") .. " -> " .. tostring(res) .. " " .. tostring(reason or ""))
    writeCatalog()
end
""", """    log(tostring(t.action) .. " " .. tostring(t.option or "") .. " -> " .. tostring(res) .. " " .. tostring(reason or ""))
    U._catalogDue = U._catalogDue or (nowMs() + 3000)                            -- several actions in a row write it once
end
"""),
("""    if tt - lastCat >= 120000 and U.solActor and U.solActor() then
        lastCat = tt
""", """    if ((U._catalogDue and tt >= U._catalogDue) or tt - lastCat >= 120000) and U.solActor and U.solActor() then
        lastCat, U._catalogDue = tt, nil
"""),
])
