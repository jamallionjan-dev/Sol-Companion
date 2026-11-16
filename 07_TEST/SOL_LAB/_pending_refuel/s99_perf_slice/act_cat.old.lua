function U.actionCatalog()
    local out, seen = {}, {}
    for _, page in ipairs(PAGES) do
        local items = U.extractPage and U.extractPage(page) or nil
