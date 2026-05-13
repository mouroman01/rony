@echo off
setlocal
title R.O.N.Y

set "RONY_DIR=%~dp0"
set "VENV_PY=%RONY_DIR%venv\Scripts\python.exe"
set "SETUP_DIR=%RONY_DIR%_setup"

set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

cd /d "%RONY_DIR%"

echo.
echo ======================================================
echo   R.O.N.Y - Responsive Omni-lingual Neural sYstem
echo ======================================================
echo.

if not exist "%VENV_PY%" (
    echo [ERRO] Ambiente virtual nao encontrado:
    echo        %VENV_PY%
    echo.
    echo Execute INSTALAR.bat ou rode:
    echo   python -m venv venv
    echo   venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

if not exist "%RONY_DIR%.env" (
    echo [AVISO] Arquivo .env nao encontrado.
    if exist "%RONY_DIR%.env.example" (
        copy "%RONY_DIR%.env.example" "%RONY_DIR%.env" >nul
        echo [OK] .env criado a partir de .env.example
    )
    echo Configure suas chaves de API no arquivo .env quando quiser usar IA.
    echo.
)

if not exist "%RONY_DIR%captures" mkdir "%RONY_DIR%captures" 2>nul
if not exist "%RONY_DIR%rostos" mkdir "%RONY_DIR%rostos" 2>nul

echo [RONY] Iniciando...
echo Para encerrar: Ctrl+C ou feche esta janela.
echo.

"%VENV_PY%" "%RONY_DIR%main.py"
set "RONY_EXIT=%ERRORLEVEL%"

echo.
echo [RONY] Encerrado. Codigo: %RONY_EXIT%
if not "%RONY_EXIT%"=="0" (
    echo.
    echo O R.O.N.Y encontrou um erro ao iniciar.
)
pause
exit /b %RONY_EXIT%
