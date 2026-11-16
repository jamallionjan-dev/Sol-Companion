# Viewpoint's debug option "Mark the vehicles' lamps" (debug.headlamps) draws red/cyan lines at every vehicle lamp.
# Its settings page (Debug/Views) only shows when the game runs in debug mode, so in the normal game it cannot be
# switched off from the settings window. This waits until the game is closed (Viewpoint rewrites the file while it
# runs), then sets the one line to false. Jamal asked for it on 2026-11-16.
# usage: powershell -ExecutionPolicy Bypass -File viewpoint_lamp_marks_off.ps1 [-MaxWaitMinutes 240]
param([int]$MaxWaitMinutes = 240)
$file = Join-Path $env:USERPROFILE 'Zomboid\viewpoint-live.properties'
$deadline = (Get-Date).AddMinutes($MaxWaitMinutes)
while ((Get-Process ProjectZomboid64 -ErrorAction SilentlyContinue) -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 3 }
if (Get-Process ProjectZomboid64 -ErrorAction SilentlyContinue) { Write-Output 'gave up: the game is still running'; exit 2 }
Start-Sleep -Seconds 4                                   # let the game finish writing its files
if (-not (Test-Path $file)) { Write-Output "not found: $file"; exit 1 }
$lines = [System.IO.File]::ReadAllLines($file)
$hit = 0
$out = foreach ($l in $lines) {
    if ($l -match '^debug\.headlamps=') { $hit++; 'debug.headlamps=false' } else { $l }
}
if ($hit -ne 1) { Write-Output "expected one debug.headlamps line, found $hit; nothing written"; exit 1 }
[System.IO.File]::WriteAllLines($file, $out)
Write-Output ('done at ' + (Get-Date -Format 'HH:mm:ss') + ': ' + ((Get-Content $file | Select-String '^debug\.headlamps=').Line))
