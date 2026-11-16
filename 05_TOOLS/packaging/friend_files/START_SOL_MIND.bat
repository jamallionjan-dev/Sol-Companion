@echo off
chcp 65001 >nul
title Sol Mind
cd /d "%~dp0SolMind"
set "PY=%~dp0python\python.exe"
if not exist "%PY%" set "PY=python"
echo Sol Mind is running... keep this window open while you play.
echo عقل سول شغّال... خلّي هالشباك مفتوح طول ما إنت عم تلعب.
:loop
"%PY%" sol_mind.py
echo Sol Mind stopped, restarting in 5 s (close this window to stop).
timeout /t 5 >nul
goto loop
