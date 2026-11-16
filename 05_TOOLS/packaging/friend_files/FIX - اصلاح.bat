@echo off
chcp 65001 >nul
title Sol FIX - اصلاح
echo === Sol Mind service log (last lines) ===
if exist "%~dp0SolMind\sol_mind_service.log" powershell -NoProfile -Command "Get-Content -Tail 15 -Encoding UTF8 '%~dp0SolMind\sol_mind_service.log'"
if exist "%~dp0SolMind\sol_mind_log.txt" powershell -NoProfile -Command "Get-Content -Tail 15 -Encoding UTF8 '%~dp0SolMind\sol_mind_log.txt'"
echo.
echo === Running Sol Mind in this window (errors will show here) ===
echo === عم شغّل عقل سول بهالشباك، والأخطاء رح تبيّن هون ===
cd /d "%~dp0SolMind"
"%~dp0python\python.exe" sol_mind.py
pause
