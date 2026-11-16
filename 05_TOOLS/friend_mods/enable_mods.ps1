# Turns on Jamal's mod list on this PC: same mods, same order. Run by "ENABLE MODS.bat".
#  1. refuses while the game is running
#  2. finds every installed mod (all Steam libraries' Workshop folders for app 108600, and Zomboid\mods)
#  3. installs the fix mod SolFixDGVEyes into Zomboid\mods, only if this PC's "Viewpoint Eyes" HUD file is the one the
#     fix was made from (a newer HUD mod must not be shadowed by an old copy)
#  4. keeps a copy of the current mod list, then writes the new one: Jamal's mods that are installed here, in his order
#  5. Viewpoint 0.1.7 signature problem: only if this PC has exactly that Viewpoint.jar and its .zbs file, it ASKS
#     before moving the .zbs aside (ZombieBuddy then relies on the player's own Allow, as with older Viewpoint versions)
#  6. writes a report (missing mods with their Workshop links) and opens it
# -DryRun: does everything except writing; -ListPath <file>: write the list to that file instead (for a test).
param([switch]$DryRun, [string]$ListPath = '')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$here = Split-Path -Parent $PSCommandPath
$zd = Join-Path $env:USERPROFILE 'Zomboid'
$modsDir = Join-Path $zd 'mods'
$list = if ($ListPath) { $ListPath } else { Join-Path $modsDir 'default.txt' }
$report = New-Object System.Collections.Generic.List[string]
function Say($en, $ar) { Write-Host $en; $report.Add($ar) }

if (-not $DryRun -and (Get-Process ProjectZomboid64, ProjectZomboid32 -ErrorAction SilentlyContinue)) {
    Write-Host 'Close Project Zomboid first, then run this again.' -ForegroundColor Yellow
    Write-Host 'سكّر اللعبة أول وبعدين شغّل الملف مرة تانية.'
    exit 1
}

# ---- what Jamal has, and the checks made when the package was built
$rows = Get-Content (Join-Path $here 'modlist.tsv') -Encoding UTF8 | Where-Object { $_ -and -not $_.StartsWith('#') } | ForEach-Object {
    $p = $_ -split "`t"; [pscustomobject]@{ Id = $p[0]; Ws = $p[1]; Name = $p[2] }
}
$check = @{}
Get-Content (Join-Path $here 'check.txt') -Encoding UTF8 | ForEach-Object { $k, $v = $_ -split '=', 2; if ($v) { $check[$k] = $v } }

# ---- Steam libraries
$libs = New-Object System.Collections.Generic.List[string]
$steam = (Get-ItemProperty 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue).SteamPath
if ($steam) {
    $libs.Add(($steam -replace '/', '\'))
    $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
    if (Test-Path $vdf) { Select-String -Path $vdf -Pattern '"path"\s+"([^"]+)"' | ForEach-Object { $libs.Add(($_.Matches[0].Groups[1].Value -replace '\\\\', '\')) } }
}
$wsRoots = $libs | Select-Object -Unique | ForEach-Object { Join-Path $_ 'steamapps\workshop\content\108600' } | Where-Object { Test-Path $_ }
if (-not $wsRoots) { Say 'Steam Workshop folder for Project Zomboid not found.' 'ما لقيت مجلد مودات الـWorkshop تبع اللعبة.' }

# ---- installed mods: id -> folder
$have = @{}
function Scan($root) {
    Get-ChildItem -Path $root -Filter 'mod.info' -Recurse -Depth 6 -File -ErrorAction SilentlyContinue | ForEach-Object {
        $m = Select-String -LiteralPath $_.FullName -Pattern '^\s*id\s*=\s*\\?(.+?)\s*$' | Select-Object -First 1   # literal: folder names like "[NUDE]"
        if ($m) { $id = $m.Matches[0].Groups[1].Value; if (-not $have.ContainsKey($id)) { $have[$id] = $_.DirectoryName } }
    }
}
foreach ($r in $wsRoots) { Scan $r }
if (Test-Path $modsDir) { Scan $modsDir }

# ---- the fix mod
$hudOk = $false
foreach ($r in $wsRoots) {
    $hud = Join-Path $r '3838246684\mods\DGVViewpointEyes\42\media\lua\client\DGVE_Blocks.lua'
    if (Test-Path $hud) { $hudOk = ((Get-FileHash $hud -Algorithm SHA256).Hash.ToLower() -eq $check['hud_sha256']) }
}
$fixInstalled = $false
if (-not $have.ContainsKey('DGVViewpointEyes4222Patch')) {
    Say 'Viewpoint Eyes HUD mod not installed: the fix mod is not needed.' 'مود الواجهة Viewpoint Eyes مش منزّل عندك، فما في داعي لمود التصليح.'
} elseif (-not $hudOk) {
    Say 'Your Viewpoint Eyes HUD mod is a different version: the fix mod was NOT installed (it would cover the newer file).' 'نسخة مود الواجهة Viewpoint Eyes عندك غير النسخة اللي انعمل عليها التصليح، فما ركّبت مود التصليح حتى ما يغطّي على الملف الأحدث.'
} else {
    if (-not $DryRun) {
        $dst = Join-Path $modsDir 'SolFixDGVEyes'
        if (Test-Path $dst) { Remove-Item -Recurse -Force $dst }
        New-Item -ItemType Directory -Force $modsDir | Out-Null
        Copy-Item -Recurse (Join-Path $here 'SolFixDGVEyes') $dst
    }
    $have['SolFixDGVEyes'] = Join-Path $modsDir 'SolFixDGVEyes'
    $fixInstalled = $true
    Say 'Installed the fix mod SolFixDGVEyes.' 'ركّبت مود التصليح SolFixDGVEyes.'
}

# ---- the list
$on = @(); $missing = @()
foreach ($r in $rows) { if ($have.ContainsKey($r.Id)) { $on += $r.Id } else { $missing += $r } }
$block = ($on | ForEach-Object { "    mod = $_," }) -join "`r`n"
$text = if (Test-Path $list) { [System.IO.File]::ReadAllText($list) } else { "VERSION = 1,`r`n`r`nmods`r`n{`r`n}`r`n`r`nmaps`r`n{`r`n}`r`n" }
$rx = New-Object System.Text.RegularExpressions.Regex('(mods\s*\{\r?\n)(.*?)(\})', [System.Text.RegularExpressions.RegexOptions]::Singleline)
if (-not $rx.IsMatch($text)) { $text = "VERSION = 1,`r`n`r`nmods`r`n{`r`n}`r`n`r`nmaps`r`n{`r`n}`r`n" }
$new = $rx.Replace($text, { param($m) $m.Groups[1].Value + $block + "`r`n" + $m.Groups[3].Value }, 1)
if (-not $DryRun) {
    if (Test-Path $list) { Copy-Item $list ($list + '.before_jamal_' + (Get-Date -Format 'yyyyMMdd_HHmmss')) }
    New-Item -ItemType Directory -Force (Split-Path -Parent $list) | Out-Null
    [System.IO.File]::WriteAllText($list, $new, (New-Object System.Text.UTF8Encoding($false)))
}
Say ("Mods turned on: {0} of {1}." -f $on.Count, $rows.Count) ("انفعّل {0} مود من {1}، بنفس ترتيب قائمة جمال." -f $on.Count, $rows.Count)
if (-not $have.ContainsKey('Sol')) { Say 'Sol is not installed: run the Sol package (PLAY SOL.bat) first, then this file again.' 'مود سول مش منزّل: شغّل ملف سول (PLAY SOL.bat) أول، وبعدين هالملف مرة تانية.' }
if ($missing.Count) {
    Say ("{0} mods are not installed on this PC and were left out (links in the report)." -f $missing.Count) ("في {0} مود مش منزّلين عندك، وما انحطّوا بالقائمة. اشترك فيهم من هالروابط وشغّل الملف مرة تانية:" -f $missing.Count)
    foreach ($r in $missing) {
        if ($r.Ws -eq 'local') { $report.Add(("  {0}  ({1})  مش من الـWorkshop: بيجي مع ملف سول" -f $r.Name, $r.Id)) }
        else { $report.Add(("  {0}  ({1})  https://steamcommunity.com/sharedfiles/filedetails/?id={2}" -f $r.Name, $r.Id, $r.Ws)) }
    }
}

# ---- Viewpoint 0.1.7 signature
foreach ($r in $wsRoots) {
    $jar = Join-Path $r '3809306528\mods\Viewpoint\42\media\java\client\Viewpoint.jar'
    $zbs = $jar + '.zbs'
    if ((Test-Path $jar) -and (Test-Path $zbs) -and ((Get-FileHash $jar -Algorithm SHA256).Hash.ToLower() -eq $check['viewpoint_bad_sha256'])) {
        Write-Host ''
        Write-Host 'Your Viewpoint is the 0.1.7 release whose signature file does not match its author''s Steam profile.' -ForegroundColor Yellow
        Write-Host 'ZombieBuddy then refuses to load Viewpoint and the game can crash at start. Many players fixed it by moving'
        Write-Host 'the file Viewpoint.jar.zbs aside; ZombieBuddy then asks you to Allow the Viewpoint file yourself.'
        Write-Host 'نسخة Viewpoint عندك فيها ملف توقيع غلط، فـ ZombieBuddy بيرفض يحمّلو. الحل: نشيل ملف التوقيع ونخلّي ZombieBuddy يسألك توافق.'
        $a = if ($DryRun) { 'n' } else { Read-Host 'Move Viewpoint.jar.zbs aside? / أشيل ملف التوقيع؟ (y/n)' }
        if ($a -match '^(y|yes|ن|نعم|اي|إي)$') {
            Move-Item $zbs ($zbs + '.removed') -Force
            Say 'Moved Viewpoint.jar.zbs aside (renamed to .removed). The next Viewpoint update brings a new one.' 'شلت ملف توقيع Viewpoint (صار اسمو .removed). تحديث Viewpoint الجاي بيرجّع ملف جديد لحالو.'
        } else {
            Say 'Viewpoint signature file left as it is.' 'تركت ملف توقيع Viewpoint متل ما هو.'
        }
    }
}
$report.Add('')
$report.Add('بعد ما تفتح اللعبة: ZombieBuddy بيسألك توافق على ملفات الجافا الجديدة. علّم Allow، واترك Trust author فاضية.')
if ($DryRun) { Write-Host '(dry run: nothing written)'; $report | ForEach-Object { Write-Host $_ }; exit 0 }
$rep = Join-Path $here '..\نتيجة التفعيل.txt'
[System.IO.File]::WriteAllLines($rep, $report, (New-Object System.Text.UTF8Encoding($true)))
Start-Process notepad.exe -ArgumentList ('"' + (Resolve-Path $rep) + '"')
Write-Host 'Done. The report opened in Notepad.' -ForegroundColor Green
