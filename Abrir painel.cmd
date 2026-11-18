@echo off
cd /d "%~dp0"
if exist "trabalho\Painel.pyw" (
    start "" pythonw.exe -X utf8 "trabalho\Painel.pyw" 2>nul
    if errorlevel 1 (
        python.exe -X utf8 "tools\painel_ccc.py"
    )
) else (
    python.exe -X utf8 "tools\painel_ccc.py"
)
