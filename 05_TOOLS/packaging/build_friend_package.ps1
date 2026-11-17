# Builds the one-click friend package of Sol: mod + Sol Mind + bundled embeddable Python + launchers.
# usage: powershell -ExecutionPolicy Bypass -File build_friend_package.ps1   (output: 08_PUBLIC\Sol-<ver>.zip and Desktop\Sol-<ver>-for-friend.zip)
#   -ReleaseDir <01_WORK\RELEASE\SOL_<date>_<ver>>  build from a release folder (its Sol\ and SolFixes_MAIN.txt) instead of the installed mod
#   -PythonDir <folder>                              reuse an already unpacked embeddable Python 3.12 (PSF-signed files are checked) instead of the python.org zip
#   -NoDesktopCopy                                   do not copy the zip to the Desktop
param([string]$ReleaseDir = '', [string]$PythonDir = '', [switch]$NoDesktopCopy)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$files = Join-Path $PSScriptRoot 'friend_files'
$mod = Join-Path $env:USERPROFILE 'Zomboid\mods\Sol'                       # the installed release (build_release.py install)
$fixes = Join-Path $env:USERPROFILE 'Zomboid\Lua\SolFixes_MAIN.txt'
if ($ReleaseDir) { $mod = Join-Path $ReleaseDir 'Sol'; $fixes = Join-Path $ReleaseDir 'SolFixes_MAIN.txt' }
if (-not (Test-Path (Join-Path $mod '42\mod.info')) -or -not (Test-Path $fixes)) { throw "mod or switch file not found: $mod / $fixes" }
$ver = ((Get-Content (Join-Path $mod '42\mod.info')) -match '^modversion=') -replace 'modversion=',''
$out = Join-Path $root '08_PUBLIC'; $pkg = Join-Path $out 'Sol-Release'
# the Python folder may live inside the package folder that is about to be rebuilt: move it aside first
$pyStash = ''
if ($PythonDir) {
  if (-not (Test-Path (Join-Path $PythonDir 'pythonw.exe'))) { throw "no pythonw.exe in $PythonDir" }
  foreach ($n in 'python.exe','pythonw.exe','python312.dll') {
    $sig = Get-AuthenticodeSignature (Join-Path $PythonDir $n)
    if ($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notmatch 'Python Software Foundation') { throw "$n is not a PSF-signed file" }
  }
  $pyStash = Join-Path $env:TEMP ('sol_py_' + [guid]::NewGuid().ToString('N'))
  Copy-Item -Recurse $PythonDir $pyStash
}
if (Test-Path $pkg) { Remove-Item -Recurse -Force $pkg }
New-Item -ItemType Directory -Force "$pkg\Zomboid\mods", "$pkg\Zomboid\Lua", "$pkg\SolMind" | Out-Null
Copy-Item -Recurse $mod "$pkg\Zomboid\mods\Sol"
Get-ChildItem "$pkg\Zomboid\mods\Sol" -Recurse -File | Where-Object { $_.Name -match '\.bak$|\.bak_|\.pre_|\.orig$|\.tmp$|\.rej$' } | Remove-Item -Force   # no leftover backups
Copy-Item $fixes "$pkg\Zomboid\Lua\SolFixes_MAIN.txt"
Get-ChildItem (Join-Path $root '05_TOOLS\sol_mind') -File | Where-Object { $_.Extension -in '.py','.pyw' -or $_.Name -like '*.json.gz' } | Copy-Item -Destination "$pkg\SolMind"
# scrub: the LAN phone address becomes an optional env var (SOL_PINNED_TLS_HOST)
$prov = "$pkg\SolMind\providers.py"; $t = Get-Content -Raw -Encoding UTF8 $prov
$t = $t -replace "if target\.scheme == 'https' and target\.hostname == '192\.168\.0\.140' and target\.port == 11434:", "pinned = os.environ.get('SOL_PINNED_TLS_HOST', '')`n    if pinned and target.scheme == 'https' and target.hostname == pinned:"
if ($t -notmatch '(?m)^import os') { $t = "import os`n" + $t }
[IO.File]::WriteAllText($prov, $t, (New-Object Text.UTF8Encoding $false))
Get-ChildItem $files -File | Where-Object Name -ne 'python312._pth' | Copy-Item -Destination $pkg
# the texts carry the version of the mod they ship with
foreach ($f in Get-ChildItem $pkg -File -Include *.txt,*.md -Recurse -Depth 0) {
  $b = [IO.File]::ReadAllBytes($f.FullName)
  $bom = $b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF
  $raw = [IO.File]::ReadAllText($f.FullName, [Text.Encoding]::UTF8)
  $new = $raw -replace '(Sol|سول) 0\.\d+\.\d+', ('$1 ' + $ver)     # "Sol" in Latin or Arabic letters
  if ($new -ne $raw) { [IO.File]::WriteAllText($f.FullName, $new, (New-Object Text.UTF8Encoding $bom)) }
}
# bundled Python (official embeddable, sha256 checked against python.org's SPDX; or the PSF-signed folder given with -PythonDir)
if ($pyStash) {
  Move-Item $pyStash "$pkg\python"
} else {
  $pyZip = Join-Path $env:TEMP 'python-3.12.10-embed-amd64.zip'
  if (-not (Test-Path $pyZip)) { Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' -OutFile $pyZip }
  if ((Get-FileHash $pyZip -Algorithm SHA256).Hash -ne '4ACBED6DD1C744B0376E3B1CF57CE906F9DC9E95E68824584C8099A63025A3C3') { throw 'Python zip hash mismatch' }
  Expand-Archive $pyZip "$pkg\python" -Force
}
Copy-Item (Join-Path $files 'python312._pth') "$pkg\python\" -Force
Get-ChildItem "$pkg\python" -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force
# scrub check
# (case-sensitive: the Windows account name in a path, a LAN address, an e-mail. The first name in code comments and in the
#  kill-ledger labels of SolShootDiscipline / SolDamageProbe is code, not a path, and is left as it is.)
$hits = Get-ChildItem $pkg -Recurse -File -Include *.py,*.pyw,*.lua,*.txt,*.md,*.ps1,*.bat | Select-String -CaseSensitive -Pattern 'JAMAL|Users[\\/]+[Jj]amal|192\.168\.0\.|@gmail' -List   # 192.168.1.x = his own network; the README's example address is 192.168.1.20
if ($hits) { $hits | ForEach-Object { $_.Path }; throw 'personal data found' }
$zip = Join-Path $out "Sol-$ver.zip"; if (Test-Path $zip) { Remove-Item $zip }
Compress-Archive -Path $pkg -DestinationPath $zip
if (-not $NoDesktopCopy) { Copy-Item $zip (Join-Path ([Environment]::GetFolderPath('Desktop')) "Sol-$ver-for-friend.zip") -Force }
"built $zip"
