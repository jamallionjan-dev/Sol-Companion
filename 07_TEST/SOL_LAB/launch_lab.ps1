# Starts the lab game and Sol Mind together, or not at all.
# Refuses if a Sol Mind is running that started before its newest source file changed: the game would run against old code.
# -CheckOnly reports what it would do and starts nothing.
param(
    [switch]$CheckOnly,
    [string]$MindDirOverride
)

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$labRoot = $PSScriptRoot
$profileDir = Join-Path $labRoot 'profile\Zomboid'
$game = 'C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid'
$mindDir = if ([string]::IsNullOrWhiteSpace($MindDirOverride)) { Join-Path $root '05_TOOLS\sol_mind' } else { (Resolve-Path -LiteralPath $MindDirOverride -ErrorAction SilentlyContinue).Path }
if (-not $mindDir -or -not (Test-Path -LiteralPath (Join-Path $mindDir 'sol_mind.py')) -or -not (Test-Path -LiteralPath (Join-Path $mindDir 'model_router.py'))) {
    Write-Output 'REFUSED: the selected Sol Mind directory is missing sol_mind.py or model_router.py.'
    exit 12
}
$python = 'C:\Program Files\Python310\pythonw.exe'

# Refuse a false-positive lab run. Without this shared marker SolAuthority
# deliberately treats the profile as MAIN and ignores SolFixes_LAB.txt.
$labFlag = Join-Path $profileDir 'mods\Sol_LAB\42\media\lua\shared\SolLab.lua'
if (-not (Test-Path -LiteralPath $labFlag)) {
    Write-Output 'REFUSED: Sol_LAB is missing media/lua/shared/SolLab.lua; this profile would run MAIN switches, not LAB switches.'
    exit 10
}
$labFlagText = Get-Content -LiteralPath $labFlag -Raw
if ($labFlagText -notmatch 'SolLab\s*=\s*\{\s*active\s*=\s*true\s*\}') {
    Write-Output 'REFUSED: Sol_LAB SolLab.lua does not set SolLab.active=true.'
    exit 10
}
Write-Output 'LAB AUTHORITY OK (SolLab.active=true; SolFixes_LAB.txt will be used).'

# Prefer tasklist, but use PowerShell's process table if tasklist itself fails.
# A fallback is accepted only when a general Get-Process query proves that
# process enumeration works; never treat an inspection failure as a clear list.
$tasklistExe = Join-Path $env:WINDIR 'System32\tasklist.exe'
$gameProcesses = @()
try {
    $taskRows = @(& $tasklistExe /FO CSV /NH 2>&1)
    $tasklistExit = $LASTEXITCODE
    if ($tasklistExit -eq 0 -and -not (($taskRows -join "`n") -match '(?im)^ERROR:')) {
        $processRows = @($taskRows | ConvertFrom-Csv -Header ImageName,PID,SessionName,SessionNumber,MemUsage)
        $gameProcesses = @($processRows | Where-Object { $_.ImageName -match '^(java|javaw|ProjectZomboid64)\.exe$' })
    } else { throw 'tasklist returned an error' }
} catch {
    try {
        $allProcesses = @(Get-Process -ErrorAction Stop)
        if ($allProcesses.Count -eq 0) { throw 'Get-Process returned no rows; enumeration is unverified' }
        $gameProcesses = @($allProcesses | Where-Object { $_.ProcessName -match '^(java|javaw|ProjectZomboid64)$' })
        Write-Output 'tasklist failed; verified process list through Get-Process.'
    } catch {
        Write-Output 'REFUSED: tasklist and Get-Process could not verify the process list; refusing to risk a duplicate game instance.'
        exit 2
    }
}
if ($gameProcesses.Count -gt 0) {
    Write-Output ('REFUSED: a game process is already running: ' + (($gameProcesses | ForEach-Object { if ($_.ImageName) { $_.ImageName + ' PID ' + $_.PID } else { $_.ProcessName + ' PID ' + $_.Id } }) -join ', '))
    exit 2
}

# Sol Mind has a single-instance lock because two brains must never own the
# same mailbox. Check that lock before launching the game, not after it starts.
$probe = $null
try {
    $probe = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Parse('127.0.0.1'), 8768)
    $probe.Start()
    $probe.Stop()
    $probe = $null
} catch {
    if ($probe) { try { $probe.Stop() } catch {} }
    Write-Output 'REFUSED: Sol Mind port 8768 is already owned; refusing to start another LAB game without its matching brain.'
    exit 11
}

$newestSource = (Get-ChildItem $mindDir -Filter *.py -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1)
$minds = @()
$pythonProcesses = @(Get-Process -Name python,pythonw -ErrorAction SilentlyContinue)
try {
    $minds = @(Get-CimInstance Win32_Process -Filter "name like 'python%'" -ErrorAction Stop | Where-Object { $_.CommandLine -match 'sol_mind\.py' })
} catch {
    if ($pythonProcesses.Count -gt 0) {
        Write-Output 'REFUSED: cannot inspect Python command lines in this environment; close Python processes and retry so Sol Mind is not started twice.'
        exit 3
    }
    Write-Output 'Process command-line inspection unavailable; no Python processes are running, so Sol Mind can start safely.'
}
$stale = @($minds | Where-Object { $_.CreationDate -lt $newestSource.LastWriteTime })
if ($stale.Count -gt 0) {
    foreach ($m in $stale) {
        Write-Output ("REFUSED: Sol Mind PID {0} started {1}, before {2} changed at {3}. End it, then launch again." -f $m.ProcessId, $m.CreationDate, $newestSource.Name, $newestSource.LastWriteTime)
    }
    exit 3
}
$running = $minds.Count -gt 0
Write-Output ("Sol Mind: {0}" -f $(if ($running) { "current (PID $($minds[0].ProcessId))" } else { 'not running, will be started' }))
# Jamal 2026-11-10: update the release before every launch (build_release.py <version> install, then a release/<version> PR). Reminder only.
# Checklist before launch: release built, Mind card updated with every Mind change, every staged fix committed and pushed, DOCS updated (SOL_HANDOFF, SOL_LEDGER, SOL_CAPABILITIES).
$relInfo = 'C:\Users\JAMAL\Zomboid\mods\Sol\mod.info'
$labNewest = Get-ChildItem (Join-Path $profileDir 'mods\Sol_LAB\42\media') -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ((Test-Path $relInfo) -and $labNewest -and $labNewest.LastWriteTime -gt (Get-Item $relInfo).LastWriteTime) {
    Write-Output ("RELEASE REMINDER: the lab ({0}, {1}) is newer than the installed release; run build_release.py before launching." -f $labNewest.Name, $labNewest.LastWriteTime)
} else { Write-Output "Release: up to date with the lab." }

$modsOk = -not (Compare-Object (Get-Content (Join-Path $labRoot 'MODS_LAB_MIN.txt')) (Get-Content (Join-Path $profileDir 'mods\default.txt')))
if (-not $modsOk) {
    Write-Output 'REFUSED: the lab mod list differs from MODS_LAB_MIN.txt.'
    exit 4
}

# Every class, method and field Sol's Java names in the game must exist in this game build with the same type.
$linkCheck = Join-Path $root '05_TOOLS\sol_kahlua\linkcheck.py'
$solJar = Join-Path $profileDir 'mods\Sol_LAB\42\media\java\SolCombined.jar'
$linkOut = & ($python -replace 'pythonw\.exe$', 'python.exe') -I $linkCheck (Join-Path $game 'projectzomboid.jar') $solJar
if ($LASTEXITCODE -ne 0) {
    $linkOut | Write-Output
    Write-Output 'REFUSED: Sol''s Java does not match this game build.'
    exit 5
}
Write-Output ($linkOut | Select-Object -Last 1)

# A patch body runs inside the game's class: anything it calls in our jar must be public.
$accessOut = & ($python -replace 'pythonw\.exe$', 'python.exe') -I (Join-Path $root '05_TOOLS\sol_kahlua\patch_access_check.py') $solJar
if ($LASTEXITCODE -ne 0) {
    $accessOut | Write-Output
    Write-Output 'REFUSED: a patch in Sol''s Java calls something the game''s classes cannot reach.'
    exit 6
}
Write-Output ($accessOut | Select-Object -Last 1)

# Kahlua's tonumber casts its first argument to String when it gets a second one (BaseLib.java:419):
# tonumber(f()) with f returning two values crashes the game. Every such call must read tonumber((f())).
$luaClient = Join-Path $profileDir 'mods\Sol_LAB\42\media\lua\client'
$tonumberOut = & ($python -replace 'pythonw\.exe$', 'python.exe') -I (Join-Path $root '05_TOOLS\sol_kahlua\tonumber_check.py') $luaClient
if ($LASTEXITCODE -ne 0) {
    $tonumberOut | Select-Object -First 40 | Write-Output
    Write-Output 'REFUSED: a tonumber call in Sol''s Lua can receive two values and crash under Kahlua (run _pending_refuel\apply_s75_onevalue.py).'
    exit 7
}
Write-Output ($tonumberOut | Select-Object -Last 1)

# 2026-11-11: every Java method Sol's Lua calls by name must exist in the game jar with that many arguments
# (getAllCategoryRecurse("Weapon") with one argument failed every 2 s in play; B42 only has the two-argument form).
$jarcallOut = & ($python -replace 'pythonw\.exe$', 'python.exe') -I (Join-Path $root '05_TOOLS\sol_kahlua\jarcall_check.py') $luaClient
if ($LASTEXITCODE -ne 0) {
    $jarcallOut | Where-Object { $_ -like 'FAIL*' } | Select-Object -First 20 | Write-Output
    Write-Output 'REFUSED: Sol''s Lua calls a Java method with a number of arguments the game jar does not have.'
    exit 9
}
Write-Output ($jarcallOut | Select-Object -Last 1)

# Jamal's rule: the model entry card changes with every Mind change. Every action the Mind can run is on the card with an
# example, nothing on it is unhandled, it fits the budget, DOCS\SOL_MODEL_CARD.md matches it and the route replay passes.
$cardDoc = Join-Path $mindDir 'SOL_MODEL_CARD.md'
$cardArgs = @($mindDir, '--lua', $luaClient)
if (Test-Path -LiteralPath $cardDoc) { $cardArgs += @('--doc', $cardDoc) }
$cardOut = & ($python -replace 'pythonw\.exe$', 'python.exe') -I (Join-Path $root '05_TOOLS\sol_kahlua\card_check.py') @cardArgs
if ($LASTEXITCODE -ne 0) {
    $cardOut | Where-Object { $_ -match '^(FAILURES|WARNINGS|CARD_CHECK|  - )' } | Select-Object -First 60 | Write-Output
    Write-Output 'REFUSED: the model card is out of step with the Mind (fix the Mind''s card, then card_check.py <sol_mind> --write-doc).'
    exit 8
}
Write-Output ($cardOut | Select-Object -Last 1)

if ($CheckOnly) {
    Write-Output 'OK: would launch.'
    exit 0
}

# The game first, so Sol Mind can be told which process it belongs to and stop with it.
# Not SOL_LAB_LAUNCHER.bat: that one copies 01_WORK over the lab mod first.
$proc = Start-Process -FilePath "$game\jre64\bin\java.exe" -ArgumentList "@$labRoot\sol_lab.args" -WorkingDirectory $game -PassThru
Write-Output "Game started, PID $($proc.Id)"
if (-not $running) {
    $luaDir = Join-Path $profileDir 'Lua'
    # Keep the LAB brain's settings and DPAPI key vault attached to this isolated profile,
    # regardless of the LOCALAPPDATA value inherited from the launcher shell.
    $mindDataDir = Join-Path (Split-Path -Parent $profileDir) 'AppData\Local'
    New-Item -ItemType Directory -Force -Path $mindDataDir | Out-Null
    $mindStart = New-Object System.Diagnostics.ProcessStartInfo
    $mindStart.FileName = $python
    $mindStart.Arguments = "`"$mindDir\sol_mind.py`" --lua-dir `"$luaDir`" --headless --game-pid $($proc.Id)"
    $mindStart.WorkingDirectory = $mindDir
    $mindStart.UseShellExecute = $false
    $mindStart.EnvironmentVariables['LOCALAPPDATA'] = $mindDataDir
    $mindProc = [System.Diagnostics.Process]::Start($mindStart)
    Start-Sleep -Seconds 4
    $up = Get-Process -Id $mindProc.Id -ErrorAction SilentlyContinue
    if ($null -eq $up) { Write-Output 'WARNING: Sol Mind did not stay up.'; exit 5 }
    Write-Output "Sol Mind started, PID $($mindProc.Id), tied to the game"
}

# Keep this PowerShell session attached to the game. In managed launchers the
# child process can be stopped when the shell exits; waiting here keeps the
# interactive game alive until the player closes it. Sol Mind is tied to the
# same PID and exits with the game.
Write-Output "Lab is running (PID $($proc.Id)); this command waits until the game closes."
Wait-Process -Id $proc.Id -ErrorAction SilentlyContinue
Write-Output 'Lab game process ended.'
