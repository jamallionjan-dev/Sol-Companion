"""Writes SolGPSWords.lua: every GPS / drive reason code as a short plain phrase (Levantine Arabic + English).

Sol's Lua files are pure ASCII; Arabic is written as \\uXXXX escapes that SolText decodes when drawing.
    python gen_gps_words.py [out.lua]     default: 07_TEST/SOL_LAB/_pending_refuel/SolGPSWords.lua
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "07_TEST", "SOL_LAB", "_pending_refuel", "SolGPSWords.lua")

# phrase id -> (arabic, english, tone)   tone: bad (red), wait (yellow), calm (blue)
PHRASES = {
    "no_route":     ("ما لقيت طريق لهونيك", "No road found to there", "bad"),
    "far_from_road": ("نحنا بعاد عن أي طريق", "We are far from any road", "bad"),
    "dest_off_road": ("الوجهة بعيدة عن الطريق", "The destination is far from the road", "wait"),
    "too_far":      ("المشوار طويل كتير، اختار مكان أقرب", "Too far in one go, pick a closer place", "bad"),
    "getting_ready": ("لحظة، عم جهّز الطريق", "One moment, getting the route ready", "wait"),
    "horde_on_road": ("في زومبي عالطريق وما في لفّة آمنة", "Zombies on the road and no safe way round", "bad"),
    "partial":      ("ما في طريق بيوصل للعلامة، رح وصّل لأقرب نقطة عالطريق", "No road reaches the marker: going to the nearest road point", "wait"),
    "stopped":      ("وقّفنا", "Stopped", "calm"),
    "other_order":  ("وقّفت، طلبت شي تاني", "Stopped for your other request", "calm"),
    "new_place":    ("غيّرنا الوجهة", "Destination changed", "calm"),
    "danger_stop":  ("وقّفت، في خطر قريب", "Stopped: danger nearby", "wait"),
    "trip_cut":     ("انقطع المشوار، جرّب كمان مرة", "The trip was cut short, try again", "wait"),
    "no_driver":    ("ما في حدا ورا المقود", "Nobody is at the wheel", "bad"),
    "no_key":       ("ما معي مفتاح هالسيارة", "I have no key for this car", "bad"),
    "starting_car": ("عم حاول شغّل السيارة", "Trying to start the car", "wait"),
    "engine":       ("المحرك ما عم يشتغل", "The engine will not start", "bad"),
    "no_car":       ("ما في سيارة قريبة", "No car nearby", "bad"),
    "not_driving":  ("مش أنا عم سوق هلأ", "I am not driving right now", "calm"),
    "busy_driving": ("أنا عم سوق هلأ، وقّفني أول", "I am driving already, stop me first", "wait"),
    "cant_go":      ("ما قدرت إطلع بالسيارة هلأ", "I could not set off just now", "bad"),
    "road_shut":    ("الطريق مسكّر وما لقيت غيره", "The road is shut and I found no other", "bad"),
    "cant_turn":    ("ما قدرت لفّ هون", "I could not turn round here", "bad"),
    "road_not_seen": ("الطريق لسا ما بيّن، استنى شوي", "The road ahead is not ready yet, wait a little", "wait"),
    "cant_park":    ("ما قدرت صفّ هون", "I could not park here", "bad"),
    "door":         ("ما قدرت وصل لباب السيارة", "I could not reach the car door", "bad"),
    "to_wheel":     ("رايحة عالمقود...", "Going to the wheel...", "wait"),
    "to_door":      ("رايحة لباب السيارة...", "Walking to the car door...", "wait"),
    "no_wheel":     ("ما قدرت إقعد ورا المقود", "I could not take the wheel", "bad"),
    "no_tank":      ("ما لقيت خزان البنزين", "I could not find the fuel tank", "bad"),
    "no_can":       ("ما معي غالون", "I have no fuel can", "bad"),
    "no_pump":      ("ما في مضخة قريبة", "No pump nearby", "bad"),
    "pump_failed":  ("المضخة ما عطت بنزين", "The pump gave no fuel", "bad"),
    "no_power":     ("ما في كهربا بالمحطة", "The station has no power", "bad"),
    "wrong_fuel":   ("هاد مش بنزين", "That is not petrol", "bad"),
    "no_station":   ("ما بعرف محطة قريبة", "I know no station nearby", "bad"),
    "cant_refuel":  ("ما فيني عبّي هلأ", "I cannot refuel right now", "bad"),
    "fuel_trouble": ("في مشكلة بالبنزين", "Trouble with the fuel", "bad"),
    "open_map":     ("افتح الخريطة مرة، أو اختار الوجهة بالكبسة اليمين", "Open the map once, or right-click the destination", "wait"),
    "no_marker":    ("ما في علامة عالخريطة", "No marker on the map", "wait"),
    "no_dest":      ("اختار وجهة أول", "Pick a destination first", "wait"),
    "await_dest":   ("أنا ورا المقود، قلّي لوين", "I am at the wheel, tell me where to", "calm"),
    "board":        ("اركب من باب الراكب، ويلا", "Get in on the passenger side and we go", "calm"),
    "player_aboard": ("انزل شوي لأقعد ورا المقود، وبعدين اركب جنبي", "Step out so I can take the wheel, then sit by me", "wait"),
    "player_driver": ("إنت ورا المقود، انتقل للكرسي اللي جنبي", "You are at the wheel, move to the next seat", "wait"),
    "not_in_car":   ("مش براكبين سيارة", "We are not in a car", "wait"),
    "no_sol":       ("سول مش هون", "Sol is not here", "bad"),
    "where_exactly": ("ما عرفت وين بالضبط", "I could not tell where exactly", "bad"),
    "generic":      ("ما زبطت هالمرة", "That did not work this time", "bad"),
    # phases (English panel only showed the raw phase)
    "ph_planning":  ("عم خطّط الطريق", "Planning the route", "calm"),
    "ph_following": ("عم سوق", "Driving", "calm"),
    "ph_replanning": ("عم دوّر على طريق تاني", "Finding another way", "calm"),
    "ph_blocked":   ("الطريق مسكّر، عم استنى", "Road blocked, waiting", "wait"),
    "ph_streaming": ("عم استنى الطريق يبيّن", "Waiting for the road ahead", "wait"),
    "ph_arrived":   ("وصلنا", "Arrived", "calm"),
    "ph_turning":   ("عم لفّ", "Turning round", "calm"),
    "ph_approaching": ("عم قرّب", "Pulling in", "calm"),
    "ph_failed":    ("ما زبطت هالمرة", "That did not work this time", "bad"),
    "ph_stopped":   ("وقّفنا", "Stopped", "calm"),
    "ph_interrupted": ("انقطع المشوار", "Trip interrupted", "wait"),
    "ph_driving":   ("عم سوق", "Driving", "calm"),
}

CODES = {
    "no_route": "no_route", "NO_CONNECTED_ROUTE": "no_route", "INCOMPLETE_MAP_DATA": "no_route", "NO_ROAD_DATA": "no_route",
    "road_plan_failed": "no_route", "road_geometry_invalid": "no_route", "road_fingerprint_invalid": "no_route",
    "road_bridge_failed": "no_route", "road_routing_unavailable": "no_route", "no_street": "no_route", "no_way_round": "road_shut",
    "NO_ENTRY_CANDIDATE": "far_from_road", "road_source_unavailable": "far_from_road",
    "NO_EXIT_CANDIDATE": "dest_off_road", "BUDGET_EXCEEDED": "too_far",
    "DATA_NOT_READY": "getting_ready", "planner_unavailable": "getting_ready", "road_bridge_unavailable": "getting_ready",
    "planner_error": "generic", "NO_SAFE_ROAD_DETOUR": "horde_on_road", "LOCAL_ACCESS_BLOCKED": "horde_on_road",
    "invalid_road_avoidance": "horde_on_road", "PARTIAL_ROAD": "partial",
    "player_stop": "stopped", "stopped": "stopped", "stopping": "stopped", "released": "stopped", "actor_released": "stopped",
    "no_drive": "stopped", "player_order": "other_order", "follow_refused": "other_order", "new_destination": "new_place",
    "survival_priority": "danger_stop", "interrupted_by_load": "trip_cut", "driver_dead": "no_driver",
    "no_key": "no_key", "hotwiring": "starting_car", "engine_failed": "engine", "no_car": "no_car", "no_vehicle_near": "no_car",
    "not_driver": "not_driving", "not_driving": "not_driving", "drive_already_owned": "busy_driving",
    "drive_begin_failed": "cant_go", "bridge_failure": "cant_go", "driving_unavailable": "cant_go",
    "driving_supervisor_unavailable": "cant_go", "lf_unavailable": "cant_go", "no_job": "cant_go", "no_state": "cant_go",
    "no_actor_id": "cant_go", "actor_missing": "no_sol", "sol_not_available": "no_sol", "no_sol": "no_sol",
    "route_blocked": "road_shut", "turn_failed": "cant_turn", "streaming_stalled": "road_not_seen", "plan_timeout": "road_not_seen",
    "parking_approach_out_of_range": "cant_park", "parking_approach_rejected": "cant_park", "parking_approach_timeout": "cant_park",
    "parking_requires_arrived_drive": "cant_park", "park_error": "cant_park", "park_unavailable": "cant_park",
    "no_parking_area": "cant_park", "car_not_parked_at_base": "cant_park",
    "could_not_reach_door": "door", "moving_to_wheel": "to_wheel", "walking_to_door": "to_door", "cannot_take_wheel": "no_wheel",
    "no_gas_tank": "no_tank", "no_can": "no_can", "no_pump_near": "no_pump", "pump_too_far": "no_pump", "no_way_to_pump": "no_pump",
    "pump_failed": "pump_failed", "no_power": "no_power", "wrong_fuel": "wrong_fuel", "no_station_known": "no_station",
    "stations_unavailable": "no_station", "refuel_unavailable": "cant_refuel",
    "map_not_opened": "open_map", "no_marker": "no_marker", "no_destination": "no_dest", "await_destination": "await_dest",
    "board_passenger": "board", "player_aboard": "player_aboard", "player_is_driver": "player_driver",
    "not_in_vehicle": "not_in_car", "invalid_drive_goal": "where_exactly", "invalid_road_target": "where_exactly",
    "goal_position_unavailable": "where_exactly", "no_position": "where_exactly", "road_goal_unavailable": "where_exactly",
    "invalid_blocked_position": "road_shut",
    "planning": "ph_planning", "following": "ph_following", "replanning": "ph_replanning", "blocked": "ph_blocked",
    "streaming_wait": "ph_streaming", "arrived": "ph_arrived", "turning": "ph_turning", "approaching": "ph_approaching",
    "failed": "ph_failed", "interrupted": "ph_interrupted", "driving": "ph_driving",
}
# words inside an unknown code -> phrase (checked in this order)
KEYWORDS = [("stop", "stopped"), ("order", "other_order"), ("horde", "horde_on_road"), ("zomb", "horde_on_road"),
            ("route", "no_route"), ("road", "no_route"), ("street", "no_route"), ("path", "no_route"),
            ("fuel", "fuel_trouble"), ("gas", "fuel_trouble"), ("pump", "no_pump"), ("door", "door"), ("seat", "no_wheel"),
            ("wheel", "no_wheel"), ("board", "no_wheel"), ("park", "cant_park"), ("key", "no_key"), ("engine", "engine"),
            ("car", "no_car"), ("vehicle", "no_car"), ("marker", "no_marker"), ("map", "open_map")]


def esc(s):
    return "".join(c if ord(c) < 128 else "\\\\u%04X" % ord(c) for c in s)


def main():
    for k, v in CODES.items(): assert v in PHRASES, (k, v)
    for _, v in KEYWORDS: assert v in PHRASES, v
    L = []
    L.append("-- SolGPSWords.lua - generated by 05_TOOLS/sol_gps_roads/gen_gps_words.py; edit the generator, not this file.")
    L.append("-- What the GPS panel says for every drive / route reason code: a short plain phrase, never the code itself.")
    L.append("-- The codes stay in the log. Switch: gps_plain_words (off: the panel is exactly as before).")
    L.append("SolGPSWords = SolGPSWords or {}")
    L.append("local M = SolGPSWords")
    L.append('M.VERSION = "0.1.0"')
    L.append("M.TONE = { bad = { 0.94, 0.47, 0.43 }, wait = { 0.95, 0.71, 0.19 }, calm = { 0.29, 0.66, 1.0 } }")
    L.append("M.PHRASES = {")
    for k in sorted(PHRASES):
        a, e, t = PHRASES[k]
        L.append('    %s = { ar = "%s", en = "%s", tone = "%s" },' % (k, esc(a), e, t))
    L.append("}")
    L.append("M.CODES = {")
    for k in sorted(CODES): L.append('    %s = "%s",' % (k, CODES[k]))
    L.append("}")
    L.append("M.KEYWORDS = {")
    for w, p in KEYWORDS: L.append('    { "%s", "%s" },' % (w, p))
    L.append("}")
    L.append(LUA_BODY)
    text = "\n".join(L) + "\n"
    assert all(ord(c) < 128 for c in text)
    with open(OUT, "w", encoding="ascii", newline="\n") as h: h.write(text)
    print("wrote", OUT, len(PHRASES), "phrases", len(CODES), "codes")


LUA_BODY = r'''
function M.on()
    local A = rawget(_G, "SolAuthority")
    return type(A) == "table" and type(A.on) == "function" and A.on("gps_plain_words") == true
end

-- phrase id for any code: "no_route:INCOMPLETE_MAP_DATA" -> the detail first, then the base, then words inside it
function M.idFor(code)
    local s = tostring(code or "")
    local base, detail = string.match(s, "^([^:]+):(.+)$")
    if detail and M.CODES[detail] then return M.CODES[detail] end
    if base and M.CODES[base] then return M.CODES[base] end
    if M.CODES[s] then return M.CODES[s] end
    local low = string.lower(s)
    for i = 1, #M.KEYWORDS do
        if string.find(low, M.KEYWORDS[i][1], 1, true) then return M.KEYWORDS[i][2] end
    end
    return "generic"
end

-- text, colour
function M.say(code, ar)
    local p = M.PHRASES[M.idFor(code)] or M.PHRASES.generic
    return ar and p.ar or p.en, M.TONE[p.tone] or M.TONE.bad
end

-- true when a line shown to the player still carries a code, an id or coordinates
function M.isRaw(text)
    if type(text) ~= "string" then return false end
    local plain = string.gsub(text, "\\u%x%x%x%x", " ")
    if string.find(plain, "[%w]_[%w]") then return true end
    if string.find(plain, "%u%u+_") then return true end
    if string.find(plain, "%d+%s*,%s*%d+") then return true end
    if string.find(plain, ":%s*[%l_]+$") then return true end
    return false
end

-- a name about to be drawn (address book row): an id or a code becomes the plain fallback word
function M.cleanName(name, fallback)
    if not M.on() or not M.isRaw(name) then return name end
    return fallback or name
end

-- the panel's status line; nil keeps the panel's own line
function M.panelLine(st, P, dest, pts, driving, failed, ar, current)
    if not M.on() then return nil end
    st, P = type(st) == "table" and st or {}, type(P) == "table" and P or {}
    if st.reason and failed then
        local base = string.match(tostring(st.reason), "^([^:]+)") or ""
        if base == "no_route" and P.route and P.route.partial then return M.say("PARTIAL_ROAD", ar) end
        return M.say(st.reason, ar)
    end
    if not driving and dest and P.route and P.route.partial then return M.say("PARTIAL_ROAD", ar) end
    if not driving and dest and P.reason then return M.say(P.reason, ar) end
    if M.isRaw(current) or (not ar and type(current) == "string" and M.CODES[current]) then
        return M.say(st.phase or st.result or current, ar)
    end
    return nil
end
return M'''

if __name__ == "__main__":
    main()
