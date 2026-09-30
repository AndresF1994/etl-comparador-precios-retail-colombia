@echo off
REM Corrida diaria del pipeline ETL (programar con schtasks, ver README)
cd /d "%~dp0"
if not exist data\logs mkdir data\logs
set PYTHONIOENCODING=utf-8
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd"') do set HOY=%%i
.venv\Scripts\python.exe -m src.pipeline >> data\logs\pipeline_%HOY%.log 2>&1
