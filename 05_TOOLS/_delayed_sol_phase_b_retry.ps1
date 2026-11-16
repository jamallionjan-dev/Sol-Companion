$ErrorActionPreference='SilentlyContinue'
Start-Sleep -Seconds 20
$targets=Get-CimInstance Win32_Process | Where-Object {$_.Name -eq 'python.exe' -and $_.CommandLine -match 'chatgpt_bridge_server\.py'}
foreach($p in $targets){Stop-Process -Id $p.ProcessId -Force}
Start-Sleep -Milliseconds 800
$py=Join-Path $HOME 'AppData\Local\Programs\Python\Python312\python.exe'
$server=Join-Path $HOME 'Desktop\Sol\03_CHATGPT_BRIDGE\chatgpt_bridge\chatgpt_bridge_server.py'
Start-Process -FilePath $py -ArgumentList $server -WindowStyle Hidden
