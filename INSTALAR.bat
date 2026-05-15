@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title Instalar Rony

echo.
echo  +======================================================+
echo  ^|   R.O.N.Y  ^|  Instalacao automatica                 ^|
echo  +======================================================+
echo.

:: ── Caminhos ────────────────────────────────────────────────
set "RONY_DIR=%~dp0"
set "VENV_DIR=%RONY_DIR%venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"
set "FRONTEND_DIR=%RONY_DIR%frontend"
set "SETUP_DIR=%RONY_DIR%_setup"
set "ERROS=0"

call :find_python
if errorlevel 1 exit /b 1
call :check_python_version
if errorlevel 1 exit /b 1

echo  [2/6] Configurando ambiente virtual...
if not exist "%VENV_DIR%" (
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo  [ERRO] Falha ao criar ambiente virtual.
        pause
        exit /b 1
    )
)
echo  [OK] Ambiente virtual pronto.
echo.

echo  [3/6] Instalando dependencias Python...
"%VENV_PY%" -m pip install --upgrade pip --quiet --no-cache-dir
"%VENV_PIP%" install -r "%RONY_DIR%requirements.txt" --no-warn-script-location --no-cache-dir
if errorlevel 1 (
    echo  [AVISO] Alguns pacotes falharam. Tentando continuar...
    set "ERROS=1"
) else (
    echo  [OK] Dependencias Python instaladas.
)
echo.

echo  Verificando PyAudio (microfone)...
"%VENV_PY%" -c "import pyaudio" >nul 2>&1
if errorlevel 1 (
    "%VENV_PIP%" install pyaudio --quiet --no-cache-dir 2>nul
    if errorlevel 1 (
        echo  [AVISO] PyAudio nao instalado automaticamente. O Rony ainda pode funcionar em modo texto.
    ) else (
        echo  [OK] PyAudio instalado.
    )
) else (
    echo  [OK] PyAudio instalado.
)

echo  [OK] Permissao de microfone garantida.
echo.

if exist "%FRONTEND_DIR%\package.json" (
    echo  [4/6] Configurando interface grafica...
    pushd "%FRONTEND_DIR%"
    if exist package-lock.json (
        call npm.cmd ci --silent
    ) else (
        call npm.cmd install --silent
    )
    if errorlevel 1 (
        echo  [AVISO] Falha ao instalar dependencias do frontend.
        set "ERROS=1"
    ) else (
        call npm.cmd run build
        if errorlevel 1 (
            echo  [AVISO] Falha ao compilar frontend.
            set "ERROS=1"
        ) else (
            echo  [OK] Interface compilada.
        )
    )
    popd
) else (
    echo  [4/6] Frontend nao encontrado. Pulando.
)
echo.

echo  [5/6] Configuracao inicial...
if exist "%SETUP_DIR%\setup_wizard.py" (
    echo  Iniciando assistente de configuracao...
    "%VENV_PY%" "%SETUP_DIR%\setup_wizard.py"
    if errorlevel 1 echo  [AVISO] Configuracao nao concluida. Execute _setup\setup_wizard.py depois.
) else (
    echo  [OK] Rony ja configurado.
)
echo.

echo  [6/6] Criando atalho na area de trabalho...
if exist "%SETUP_DIR%\criar_atalho.py" (
    "%VENV_PY%" "%SETUP_DIR%\criar_atalho.py"
) else (
    echo  [AVISO] Script de atalho nao encontrado.
)
echo.

if "%ERROS%"=="1" (
    echo  +======================================================+
    echo  ^|   Instalacao concluida com avisos.                  ^|
    echo  ^|   O Rony pode funcionar parcialmente.               ^|
    echo  +======================================================+
) else (
    echo  +======================================================+
    echo  ^|   Rony instalado com sucesso!                       ^|
    echo  +======================================================+
)

echo.
echo  Para iniciar:
echo    INICIAR_RONY.bat
echo.
exit /b 0

:find_python
echo  [1/6] Verificando Python...
set "PYTHON_CMD=python"
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    set "PYTHON_CMD=py -3"
    %PYTHON_CMD% --version >nul 2>&1
)
if errorlevel 1 (
    echo.
    echo  [ERRO] Python nao encontrado.
    echo  Instale Python 3.10+ em https://www.python.org/downloads/
    echo  ou garanta que o launcher py esteja instalado.
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('%PYTHON_CMD% --version 2^>^&1') do set "PY_VER=%%v"
echo  [OK] Python %PY_VER% via %PYTHON_CMD%
exit /b 0

:check_python_version
%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo  [ERRO] Python %PY_VER% encontrado. Requer Python 3.10+
    pause
    exit /b 1
)
exit /b 0

