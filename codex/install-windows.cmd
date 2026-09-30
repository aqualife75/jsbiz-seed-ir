@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto usepython
py -3 install.py --project "%~dp0..\my-seed-ir" --team "My Team" --with-deps
goto finish
:usepython
python install.py --project "%~dp0..\my-seed-ir" --team "My Team" --with-deps
:finish
if errorlevel 1 echo Installation failed. See the message above and the HTML guide.
pause
