-- s99 perf_slice: the same catalog over several frames: a page a frame, then the list, then the JSON a value at a time
-- (SolWorldScan's U.jsonEncodeJob, the same text as U.jsonEncode), then the file. At most CAT_SLICE_MS a frame plus the unit
-- that crosses it; reading one Living Fellows page is one unit.
local CAT_SLICE_MS = 4
local catJob = nil
local function catSliceOn() local A_ = rawget(_G, "SolAuthority"); return type(A_) == "table" and type(A_.on) == "function" and A_.on("perf_slice") == true end
local function catalogStep(budgetMs)
    local j = catJob
    local stopAt = nowMs() + budgetMs
    while true do
        if j.phase == "pages" then
            local page = PAGES[j.pi]
            if page == nil then j.phase = "build"
            else
                j.pi = j.pi + 1
                local okP, items = pcall(function() return U.extractPage and U.extractPage(page) or nil end)
                if not okP then return true end                                  -- as a failed actionCatalog: nothing written
                j.pre[page] = items
                return false                                                     -- one page a frame
            end
        elseif j.phase == "build" then
            local ok, cat = pcall(U.actionCatalog, j.pre)
            if not ok or not U.jsonEncode then return true end
            local doc = { v = 1, t = nowMs(), actions = cat }
            if type(U.jsonEncodeJob) == "function" then j.enc = U.jsonEncodeJob(doc); j.phase = "encode"
            else
                local okE, text = pcall(U.jsonEncode, doc)
                if not okE then return true end
                j.text, j.phase = text, "write"
            end
        elseif j.phase == "encode" then
            if j.enc.step(math.max(stopAt - nowMs(), 0)) then j.text, j.phase = j.enc.result(), "write" end
        elseif j.phase == "write" then
            local okw, w = pcall(getFileWriter, SNAP, true, false)
            if okw and w then w:write(j.text); w:close() end
            return true
        end
        if nowMs() >= stopAt then return false end
    end
end
U.writeActionCatalog = function() catJob = nil; return writeCatalog() end      -- a reply or a spawn wants it now: written at once, as before
