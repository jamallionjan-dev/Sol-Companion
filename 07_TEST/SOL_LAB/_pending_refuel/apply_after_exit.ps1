# After the game is closed. Backs up, then installs everything prepared since the first live test.
$p='C:\Users\JAMAL\Desktop\Sol'; $pend="$p\07_TEST\SOL_LAB\_pending_refuel"; $lab="$p\07_TEST\SOL_LAB\profile\Zomboid\mods\Sol_LAB\42\media"; $client="$lab\lua\client"; $jar="$lab\java\SolCombined.jar"
if (Get-CimInstance Win32_Process -Filter "name='java.exe' or name='ProjectZomboid64.exe'") { throw 'the game is running' }
$bk="$p\07_TEST\SOL_LAB\_backup\$(Get-Date -Format 'yyyyMMdd_HHmmss')_before_s4"; New-Item -ItemType Directory -Force $bk | Out-Null
Copy-Item "$client\SCDriving.lua","$client\SolGPS.lua","$client\SolActions.lua","$client\SolFuel.lua",$jar $bk
python "$pend\apply_s4_lua.py" "$client\SCDriving.lua"; if ($LASTEXITCODE) { throw 'SCDriving' }
python "$pend\apply_s4b_lua.py" $client; if ($LASTEXITCODE) { throw 'GPS' }
Copy-Item "$pend\SolNavLeg.lua" $client -Force
"backup: $bk"
