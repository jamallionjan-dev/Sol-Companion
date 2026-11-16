$ErrorActionPreference = 'Stop'
$root = 'C:\Users\JAMAL\Desktop\Sol'
$lab = Join-Path $root '07_TEST\SOL_LAB'
$profile = Join-Path $lab 'profile\Zomboid'
$client = Join-Path $profile 'mods\Sol_LAB\42\media\lua\client'
$combat = Join-Path $client 'SCCombat.lua'
$authority = Join-Path $client 'SolAuthority.lua'
$switches = Join-Path $profile 'Lua\SolFixes_LAB.txt'
$log = Get-ChildItem (Join-Path $profile 'Logs') -Filter '*DebugLog.txt' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (Get-Process -Name ProjectZomboid64,ProjectZomboid -ErrorAction SilentlyContinue) { throw 'Project Zomboid is running; close it before installing the LAB Lua patch.' }
if (-not $log -or ((Get-Date) - $log.LastWriteTime).TotalSeconds -lt 60) { throw 'LAB log is missing or recent; refusing to touch the active install.' }
$backup = Join-Path $lab '_backup\20261112_before_s119_retreat_fire'
if (Test-Path -LiteralPath $backup) { throw "Backup already exists: $backup" }
New-Item -ItemType Directory -Path $backup | Out-Null
Copy-Item -LiteralPath $combat,$authority,$switches -Destination $backup

$text = [IO.File]::ReadAllText($combat)
$old = @'
    local distance = math.sqrt(target.distanceSq or utility.distanceSq(actor, target.actor))
    local accepted, action
    if distance <= (utility.config("combatShoveDistance") or 1.35)
        and utility.sameFloor(actor, target.actor)
        and not lineBlockedByFriendly(actor, target.actor, player, snapshot, "melee") then
        -- One controlled shove buys the next movement decision room to turn.
        accepted = utility.move(actor, "walk", {
            action = "shove", target = target.actor, retreatCounter = true,
        })
        action = "retreat_shove"
    elseif weapon and weapon.equipped and weapon.ranged and weapon.ammo > 0
        and commands.holdFire ~= true and commands.combatDoctrine ~= "stealth"
        and distance >= (utility.config("combatRetreatCoverFireMinDistance") or 3.0)
'@
$new = @'
    local distance = math.sqrt(target.distanceSq or utility.distanceSq(actor, target.actor))
    local accepted, action
    local shoveDistance = utility.config("combatShoveDistance") or 1.35
    local coverMinDistance = utility.config("combatRetreatCoverFireMinDistance") or 3.0
    local fierceCloseFire = false
    local plans = rawget(_G, "SolCombatPlans")
    local authority = rawget(_G, "SolAuthority")
    if type(plans) == "table" and type(plans.current) == "function"
        and type(authority) == "table" and type(authority.on) == "function"
        and authority.on("retreat_close_fire") == true
        and plans.current(actor) == "fierce"
        and distance >= 0.75 and distance < coverMinDistance
        and weapon and weapon.equipped and weapon.ranged and weapon.ammo > 0
        and commands.holdFire ~= true and commands.combatDoctrine ~= "stealth"
        and distance <= math.max(1, tonumber(weapon.range) or 1)
        and (type(rawget(_G, "SolShootDiscipline")) ~= "table" or not SolShootDiscipline.on() or SolShootDiscipline.coverFireOk(actor, weapon, distance))
        and target.visible == true and target.obstructed ~= true
        and utility.sameFloor(actor, target.actor)
        and not lineBlockedByFriendly(actor, target.actor, player, snapshot) then
        fierceCloseFire = true
    end
    if distance <= shoveDistance and not fierceCloseFire
        and utility.sameFloor(actor, target.actor)
        and not lineBlockedByFriendly(actor, target.actor, player, snapshot, "melee") then
        -- One controlled shove buys the next movement decision room to turn.
        accepted = utility.move(actor, "walk", {
            action = "shove", target = target.actor, retreatCounter = true,
        })
        action = "retreat_shove"
    elseif weapon and weapon.equipped and weapon.ranged and weapon.ammo > 0
        and commands.holdFire ~= true and commands.combatDoctrine ~= "stealth"
        and (distance >= coverMinDistance or fierceCloseFire)
'@
if ($text.Contains($new)) { Write-Output 's119 code already installed'; }
elseif (-not $text.Contains($old)) { throw 'Expected retreat-counter block not found; no patch applied.' }
else { $text = $text.Replace($old,$new); [IO.File]::WriteAllText($combat,$text,[Text.UTF8Encoding]::new($false)); Write-Output 'patched SCCombat.lua'; }

$a = [IO.File]::ReadAllText($authority)
if (-not $a.Contains('"retreat_close_fire"')) {
    $needle = 'A.FIXES = {' + "`r`n"
    if (-not $a.Contains($needle)) { $needle = 'A.FIXES = {' + "`n" }
    if (-not $a.Contains($needle)) { throw 'SolAuthority fix list not found.' }
    $a = $a.Replace($needle, $needle + '    "retreat_close_fire", -- s119: fierce-plan counterfire down to 0.75 tiles while retreating' + "`r`n")
    [IO.File]::WriteAllText($authority,$a,[Text.UTF8Encoding]::new($false))
}
$sw = [IO.File]::ReadAllText($switches)
if ($sw -notmatch '(?m)^retreat_close_fire=') { [IO.File]::AppendAllText($switches,"`r`nretreat_close_fire=on`r`n",[Text.Encoding]::ASCII) }
elseif ($sw -notmatch '(?m)^retreat_close_fire=on\s*$') { $sw = [regex]::Replace($sw,'(?m)^retreat_close_fire=.*$','retreat_close_fire=on'); [IO.File]::WriteAllText($switches,$sw,[Text.Encoding]::ASCII) }

$check = [IO.File]::ReadAllText($combat)
if (-not $check.Contains('plans.current(actor) == "fierce"') -or -not $check.Contains('distance >= 0.75') -or -not $check.Contains('(distance >= coverMinDistance or fierceCloseFire)')) { throw 'Post-install source verification failed.' }
Write-Output "backup=$backup"
Write-Output 'switch=retreat_close_fire=on (SOL_LAB only)'
Write-Output 'release and Steam profile untouched'
