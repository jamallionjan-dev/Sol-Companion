# Sol one-click launcher (called by "PLAY SOL.bat"). Per user; never touches other mods' files.
$ErrorActionPreference = 'Continue'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Start-Transcript -Path (Join-Path $here 'sol_launcher_log.txt') -Force | Out-Null
Add-Type -AssemblyName PresentationFramework -ErrorAction SilentlyContinue
function Say($t) { Write-Host $t; try { [System.Windows.MessageBox]::Show($t, 'Sol') | Out-Null } catch {} }
if ($here -match '\\AppData\\Local\\Temp\\' -and $here -match '\.zip') {
  Say "Extract the zip first (right-click > Extract All), then run PLAY SOL.bat from the extracted folder.`nفك الملف أول (كبسة يمين > Extract All)، وبعدين شغّل PLAY SOL.bat من المجلد اللي طلع."
  exit 1
}
Get-ChildItem -Path $here -Recurse -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue   # files from a downloaded zip are marked; unmark them
if (-not (Test-Path (Join-Path $here 'python\pythonw.exe'))) {
  Say "python\pythonw.exe is missing (antivirus may have removed it). Restore it or re-extract the zip.`nملف python\pythonw.exe ناقص (يمكن الأنتي فايروس شالو). رجّعو أو فك الملف من جديد."
}
"Sol launcher " + (Get-Date) + "  folder=" + $here + "  user=" + $env:USERPROFILE
$zd = Join-Path $env:USERPROFILE 'Zomboid'
$mods = Join-Path $zd 'mods'
$src = Join-Path $here 'Zomboid\mods\Sol'
$dst = Join-Path $mods 'Sol'
New-Item -ItemType Directory -Force $mods, (Join-Path $zd 'Lua') | Out-Null
# 1) the mod: copy if missing or a different version (old one kept once as Sol.old)
$srcVer = (Select-String -Path (Join-Path $src '42\mod.info') -Pattern '^modversion=' -ErrorAction SilentlyContinue).Line
$dstVer = $null; if (Test-Path (Join-Path $dst '42\mod.info')) { $dstVer = (Select-String -Path (Join-Path $dst '42\mod.info') -Pattern '^modversion=').Line }
$fix = Join-Path $zd 'Lua\SolFixes_MAIN.txt'
if ($srcVer -ne $dstVer) {
  # the old copy is kept once OUTSIDE the mods folder (a second folder with the same mod id inside mods would be loaded too)
  $keep = Join-Path $zd 'SolBackups'; New-Item -ItemType Directory -Force $keep | Out-Null
  $tag = if ($dstVer) { ($dstVer -replace 'modversion=','') } else { 'old' }
  if (Test-Path $dst) { $old = Join-Path $keep ("Sol_" + $tag); if (-not (Test-Path $old)) { Move-Item $dst $old } else { Remove-Item -Recurse -Force $dst } }
  $stale = Join-Path $mods 'Sol.old'; if (Test-Path $stale) { $o2 = Join-Path $keep 'Sol_old_launcher'; if (-not (Test-Path $o2)) { Move-Item $stale $o2 } else { Remove-Item -Recurse -Force $stale } }
  Copy-Item -Recurse $src $dst
  # the feature switches belong to the version: the new file replaces the old one (old one kept beside the backups)
  if (Test-Path $fix) { Copy-Item $fix (Join-Path $keep ("SolFixes_MAIN_" + $tag + ".txt")) -Force }
  Copy-Item (Join-Path $here 'Zomboid\Lua\SolFixes_MAIN.txt') $fix -Force
  Write-Host "Sol $srcVer installed / انركّب"
}
if (-not (Test-Path $fix)) { Copy-Item (Join-Path $here 'Zomboid\Lua\SolFixes_MAIN.txt') $fix }
# 2) enable ZombieBuddy + Sol in the mod list (backup once)
$list = Join-Path $mods 'default.txt'
if (-not (Test-Path $list)) { Set-Content -Path $list -Encoding ascii -Value "VERSION = 1,`r`n`r`nmods`r`n{`r`n}`r`n`r`nmaps`r`n{`r`n}" }
$txt = Get-Content -Raw $list
if (-not (Test-Path "$list.before_sol")) { Copy-Item $list "$list.before_sol" }
foreach ($id in 'ZombieBuddy','Sol') {
  if ($txt -notmatch ('mod\s*=\s*\W?' + $id + '\s*,')) {
    $txt = [regex]::Replace($txt, '(?s)(mods\s*\{)(.*?)(\r?\n\})', { param($m) $m.Groups[1].Value + $m.Groups[2].Value + "`r`n    mod = $id," + $m.Groups[3].Value }, 1)
  }
}
Set-Content -Path $list -Value $txt -Encoding ascii -NoNewline
# ZombieBuddy subscribed?
$steam = (Get-ItemProperty 'HKCU:\Software\Valve\Steam' -ErrorAction SilentlyContinue).SteamPath
$zb = $false
if ($steam) {
  $libs = @("$steam")
  $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
  if (Test-Path $vdf) { $libs += (Select-String -Path $vdf -Pattern '"path"\s+"([^"]+)"').Matches | ForEach-Object { $_.Groups[1].Value -replace '\\','\' } }
  foreach ($l in $libs) { if (Test-Path (Join-Path $l 'steamapps\workshop\content\108600\3619862853')) { $zb = $true } }
}
if (-not $zb) {
  Write-Host "Subscribe to ZombieBuddy (page opening) / اشترك بـ ZombieBuddy (عم تنفتح الصفحة)"
  if (-not $env:SOL_PLAY_DRYRUN) { Start-Process 'steam://url/CommunityFilePage/3619862853' }
}
# 3) the mind, hidden; its service waits for the game and stops the mind when the game closes (single instance)
$pyw = Join-Path $here 'python\pythonw.exe'
$svc = Join-Path $here 'SolMind\sol_mind_service.pyw'
if (-not $env:SOL_PLAY_DRYRUN) { Start-Process -FilePath $pyw -ArgumentList "`"$svc`"" -WorkingDirectory (Join-Path $here 'SolMind') -WindowStyle Hidden }
# 4) the game
if (-not $env:SOL_PLAY_DRYRUN) { Start-Process 'steam://rungameid/108600' }
Write-Host "Starting Project Zomboid... / عم تشتغل اللعبة..."
