@echo off
rem Turns on Jamal's mod list (same mods, same order) in this PC's Project Zomboid and installs the small fix mod
rem SolFixDGVEyes. Close the game first. Details: "README" next to this file.
setlocal
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0files\enable_mods.ps1"
echo.
pause
