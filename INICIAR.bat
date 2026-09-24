@echo off
cd /d "%~dp0"
echo Abrindo http://localhost:8765 ...
start "" http://localhost:8765/index.html
python -m http.server 8765
