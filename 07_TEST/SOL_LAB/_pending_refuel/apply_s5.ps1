# After the game is closed: backs up, then installs SolFuel, SolLife and their hooks. The jar is updated separately.
$p='C:\Users\JAMAL\Desktop\Sol'; $pend="$p\07_TEST\SOL_LAB\_pending_refuel"; $lab="$p\07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB\42\media"; $client="$lab\lua\client"; $jar="$lab\java\SolCombined.jar"
if (Get-CimInstance Win32_Process -Filter "name='java.exe' or name='ProjectZomboid64.exe'") { throw 'the game is running' }
$bk="$p\07_TEST\SOL_LAB\_backup\$(Get-Date -Format 'yyyyMMdd_HHmmss')_full_before_s5_s6"; New-Item -ItemType Directory -Force $bk | Out-Null
Copy-Item $client "$bk\client" -Recurse; Copy-Item $jar $bk
Copy-Item "$pend\SolFuel.lua" $client -Force
python "$pend\apply_s6_lua.py" $client; if ($LASTEXITCODE) { throw 'hooks' }
"backup: $bk"
