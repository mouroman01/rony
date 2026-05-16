@echo off
setlocal
set "RONY_DIR=%~dp0"
set "VENV_PY=%RONY_DIR%venv\Scripts\python.exe"
set "VENV_PYW=%RONY_DIR%venv\Scripts\pythonw.exe"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

cd /d "%RONY_DIR%"

if not exist "%VENV_PY%" (
    echo [ERRO] Ambiente virtual nao encontrado. Execute INSTALAR.bat.
    pause
    exit /b 1
)

if not exist "%RONY_DIR%.env" (
    if exist "%RONY_DIR%.env.example" (
        copy "%RONY_DIR%.env.example" "%RONY_DIR%.env" >nul
    )
)

:: Cria pastas necessárias
if not exist "%RONY_DIR%captures" mkdir "%RONY_DIR%captures" 2>nul
if not exist "%RONY_DIR%rostos"   mkdir "%RONY_DIR%rostos"   2>nul

:: Inicia sem janela de console (pythonw = sem terminal)
:: Log salvo em %LOCALAPPDATA%\Rony\rony.log para diagnóstico
set "LOG_DIR=%LOCALAPPDATA%\Rony"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" 2>nul

if exist "%VENV_PYW%" (
    start "" /B "%VENV_PYW%" "%RONY_DIR%main.py" >> "%LOG_DIR%\rony.log" 2>&1
) else (
    start "" /B "%VENV_PY%"  "%RONY_DIR%main.py" >> "%LOG_DIR%\rony.log" 2>&1
)

exit /b 0
