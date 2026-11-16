-- SolTheme.lua - one look for everything Sol draws outside her own windows: the same palette as her windows (dark navy panels, blue borders,
-- near-white text) and the same rounded corners. Everything is built from drawRect strips, so it needs no textures:
--   SolTheme.c                  the palette ({ r, g, b } in 0..1)
--   SolTheme.rounded(ui, x, y, w, h, r, fill, a, border, ba)   a rounded rectangle with a 1 px border
--   SolTheme.panel(ui, x, y, w, h)                              the standard Sol panel (menus, dialogs, bubbles)
--   SolTheme.disc(ui, cx, cy, r, fill, a, border, ba)           a filled circle with a border ring
--   SolTheme.arrow(ui, cx, cy, size, angle, fill, outline)      an arrow head pointing along angle (radians; 0 = right, pi/2 = down on screen)
SolTheme = SolTheme or {}
local T = SolTheme
T.VERSION = "0.1.0"
T.c = {
    bg      = { 0.031, 0.078, 0.118 },     -- #08141e
    panel   = { 0.075, 0.153, 0.220 },     -- #132738
    line    = { 0.173, 0.286, 0.380 },     -- #2c4961
    border  = { 0.165, 0.561, 0.843 },     -- #2a8fd7
    text    = { 0.937, 0.957, 0.976 },     -- #eff4f9
    num     = { 0.376, 0.690, 0.941 },     -- #60b0f0
    green   = { 0.125, 0.816, 0.376 },     -- #20d060
    yellow  = { 0.878, 0.690, 0.188 },     -- #e0b030
    red     = { 0.878, 0.439, 0.376 },     -- #e07060
}
local function rect(ui, x, y, w, h, a, c)
    if w > 0 and h > 0 then ui:drawRect(x, y, w, h, a, c[1], c[2], c[3]) end
end
-- a filled rounded rectangle: a middle band plus one strip per row of each corner
local function fillRounded(ui, x, y, w, h, r, c, a)
    r = math.max(0, math.min(r, math.floor(math.min(w, h) / 2)))
    if r == 0 then rect(ui, x, y, w, h, a, c); return end
    rect(ui, x, y + r, w, h - 2 * r, a, c)
    for i = 0, r - 1 do
        local dy = r - i - 0.5
        local inset = math.floor(r - math.sqrt(r * r - dy * dy) + 0.5)
        rect(ui, x + inset, y + i, w - 2 * inset, 1, a, c)
        rect(ui, x + inset, y + h - 1 - i, w - 2 * inset, 1, a, c)
    end
end
function T.rounded(ui, x, y, w, h, r, fill, a, border, ba)
    if border then
        fillRounded(ui, x, y, w, h, r, border, ba or 1)
        fillRounded(ui, x + 1, y + 1, w - 2, h - 2, r - 1, fill, a or 1)
    else
        fillRounded(ui, x, y, w, h, r, fill, a or 1)
    end
end
function T.panel(ui, x, y, w, h)
    T.rounded(ui, x, y, w, h, 8, T.c.panel, 0.97, T.c.border, 0.9)
end
function T.disc(ui, cx, cy, r, fill, a, border, ba)
    local function disc(rr, c, al)
        for dy = -rr, rr do
            local half = math.floor(math.sqrt(math.max(0, rr * rr - dy * dy)) + 0.5)
            rect(ui, cx - half, cy + dy, 2 * half + 1, 1, al, c)
        end
    end
    if border then disc(r, border, ba or 1); disc(r - 2, fill, a or 1) else disc(r, fill, a or 1) end
end
-- a triangle by scanlines
local function fillTriangle(ui, p, c, a)
    local minY, maxY = math.huge, -math.huge
    for i = 1, 3 do minY = math.min(minY, p[i][2]); maxY = math.max(maxY, p[i][2]) end
    for y = math.floor(minY), math.ceil(maxY) do
        local yy = y + 0.5
        local lo, hi = math.huge, -math.huge
        for i = 1, 3 do
            local a1, b1 = p[i], p[i % 3 + 1]
            local y1, y2 = a1[2], b1[2]
            if (yy >= math.min(y1, y2)) and (yy < math.max(y1, y2)) and y1 ~= y2 then
                local x = a1[1] + (yy - y1) * (b1[1] - a1[1]) / (y2 - y1)
                lo = math.min(lo, x); hi = math.max(hi, x)
            end
        end
        if hi > lo then rect(ui, math.floor(lo + 0.5), y, math.max(1, math.floor(hi - lo + 0.5)), 1, a or 1, c) end
    end
end
function T.arrow(ui, cx, cy, size, angle, fill, outline)
    local function head(s, c)
        local ca, sa = math.cos(angle), math.sin(angle)
        local tip = { cx + ca * s, cy + sa * s }
        local back = s * 0.85
        local l = { cx - ca * back * 0.7 + sa * back * 0.75, cy - sa * back * 0.7 - ca * back * 0.75 }
        local r = { cx - ca * back * 0.7 - sa * back * 0.75, cy - sa * back * 0.7 + ca * back * 0.75 }
        fillTriangle(ui, { tip, l, r }, c, 1)
    end
    if outline then head(size + 2, outline) end
    head(size, fill)
end
print("[SolTheme] ready v" .. T.VERSION)
