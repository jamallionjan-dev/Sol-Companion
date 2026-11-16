from pathlib import Path
import hashlib
import shutil

ROOT = Path(__file__).resolve().parents[3]
upstream = Path(r'C:\Program Files (x86)\Steam\steamapps\workshop\content\108600\3783444342\mods\AviationCore\42\media\lua\client\AviationCore\Flight\FlightRuntime.lua')
work = ROOT / '01_WORK/Sol/42/media/lua/client'
lab = ROOT / '07_TEST/SOL_LAB/profile/Zomboid/mods/Sol_LAB/42/media/lua/client'
backup = ROOT / '08_RUNTIME_TEST/s137_explicit_pilot'
backup.mkdir(parents=True, exist_ok=True)
text = upstream.read_text(encoding='utf-8-sig')
assert text.count('local playerObj = getPlayer()') == 2
header = '''-- Local Sol compatibility copy; original AviationCore FlightRuntime retained below.
-- Only the movement/correction pilot lookup is changed. See DOCS/S137_EXPLICIT_PILOT.md.
local activeMods = getActivatedMods()
if not (activeMods:contains("AviationCore") or activeMods:contains("\\\\AviationCore")) then return end
local function solFlightPilot()
    local gps = rawget(_G, "SolHeliGPS")
    if gps and type(gps.runtimePilot) == "function" then return gps.runtimePilot() end
    return getPlayer()
end
'''
patched = header + text.replace('local playerObj = getPlayer()', 'local playerObj = solFlightPilot()') + '\nSolAviationRuntimeBridgeReady = true\n'
source = (work / 'SolHeliGPS.lua').read_text(encoding='utf-8-sig')
start = source.index('local function flightRuntimeCaller()')
end = source.index('local function wrapInput()', start)
replacement = '''-- Explicit AviationCore call-site adapter; no debug library or global player proxy.
function H.runtimePilot()
    if H.active and enabled() then
        local context = pilotContext()
        if context then
            if not H._runtimeBridgeRoutedLogged then
                H._runtimeBridgeRoutedLogged = true
                log("FlightRuntime pilot bridge routed local pilot to Sol")
            end
            return context.sol
        end
    end
    return getPlayer()
end

reportRuntimeBridgeOutcome = function()
    if not H._runtimeBridgeRoutedLogged then log("explicit FlightRuntime pilot handoff not observed") end
end

function H.installRuntimePlayerProxy()
    H._runtimeBridgeRoutedLogged = false
    H._runtimeBridgeInstalledAt = nowMs()
    H._runtimeBridgeWatchdogLogged = false
    log("explicit AviationCore pilot adapter armed; no global getPlayer replacement")
    return true
end

function H.restoreRuntimePlayerProxy()
    H._runtimeBridgeRoutedLogged = false
    return true
end

'''
source = source[:start] + replacement + source[end:]
for name, client in [('WORK', work), ('LAB', lab)]:
    dest = backup / (name + '_SolHeliGPS.before.lua')
    if not dest.exists(): shutil.copy2(client / 'SolHeliGPS.lua', dest)
    (client / 'SolHeliGPS.lua').write_text(source, encoding='utf-8')
    override = client / 'AviationCore/Flight/FlightRuntime.lua'
    override.parent.mkdir(parents=True, exist_ok=True)
    override.write_text(patched, encoding='utf-8')
(backup / 'upstream.sha256').write_text(hashlib.sha256(upstream.read_bytes()).hexdigest(), encoding='ascii')
shutil.copy2(upstream, backup / 'FlightRuntime.upstream.lua')
print('Installed explicit pilot lookup at two AviationCore call sites; upstream retained with SHA256')
