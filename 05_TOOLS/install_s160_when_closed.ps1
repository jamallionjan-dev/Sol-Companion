# Installs s160 bank_first into Sol's Mind (05_TOOLS\sol_mind) once the game is closed, the way Jamal approved it on
# 2026-11-16 ("سكرت العبة ... كمل"): backup of the two Mind files first, then apply_s160_bank_first.py with the main
# profile's switch file. Never while the game runs: the Mind restarts with the game and reads the new code then.
param([int]$MaxWaitMinutes = 480)
$root = 'C:\Users\JAMAL\Desktop\Sol'
$mind = Join-Path $root '05_TOOLS\sol_mind'
$deadline = (Get-Date).AddMinutes($MaxWaitMinutes)
while ((Get-Process ProjectZomboid64 -ErrorAction SilentlyContinue) -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 3 }
if (Get-Process ProjectZomboid64 -ErrorAction SilentlyContinue) { Write-Output 'gave up: the game is still running'; exit 2 }
Start-Sleep -Seconds 6
$back = Join-Path $root ('03_BACKUPS\sol_mind_before_s160_' + (Get-Date -Format 'yyyyMMdd_HHmm'))
New-Item -ItemType Directory -Force $back | Out-Null
Copy-Item (Join-Path $mind 'chat_service.py'), (Join-Path $mind 'model_router.py') $back
& 'C:\Program Files\Python310\python.exe' -I (Join-Path $root '07_TEST\SOL_LAB\_pending_refuel\apply_s160_bank_first.py') $mind 'C:\Users\JAMAL\Zomboid\Lua\SolFixes_MAIN.txt' (Join-Path $root '07_TEST\SOL_LAB\profile\Zomboid\Lua\SolFixes_LAB.txt')
& 'C:\Program Files\Python310\python.exe' -m py_compile (Join-Path $mind 'chat_service.py') (Join-Path $mind 'model_router.py')
if ($LASTEXITCODE -eq 0) { Write-Output ('installed at ' + (Get-Date -Format 'HH:mm:ss') + '; backup ' + $back) } else { Write-Output 'COMPILE FAILED: restore from ' + $back; exit 1 }
