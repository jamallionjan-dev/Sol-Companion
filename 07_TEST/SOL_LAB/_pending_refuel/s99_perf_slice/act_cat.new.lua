function U.actionCatalog(pre)       -- s99 perf_slice: pre = the pages already read (one a frame); nil = read them now, as before
    local out, seen = {}, {}
    for _, page in ipairs(PAGES) do
        local items
        if type(pre) == "table" then items = pre[page] else items = U.extractPage and U.extractPage(page) or nil end
