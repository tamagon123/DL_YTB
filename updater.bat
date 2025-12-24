@echo off
timeout /t 2 > nul
del "c:\DATA\python\DLyoutube\.venv\Scripts\python.exe"
ren "c:\DATA\python\DLyoutube\.venv\Scripts\python.exe.new" "python.exe"
start "" "c:\DATA\python\DLyoutube\.venv\Scripts\python.exe"
del "updater.bat"
