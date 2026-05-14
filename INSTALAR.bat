@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title R.O.N.Y - Instalacao

cls
echo.
echo  +======================================================+
echo  ^|   R.O.N.Y  ^|  Responsive Omni-lingual Neural sYstem  ^|
echo  ^|   Instalador v1.0  ^|  github.com/mouroman01/rony       ^|
echo  +======================================================+
echo.

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
"%VENV_PY%" -m pip install --upgrade pip --quiet
"%VENV_PIP%" install -r "%RONY_DIR%requirements.txt" --no-warn-script-location
if errorlevel 1 (
    echo  [AVISO] Alguns pacotes falharam. Tentando continuar...
    set "ERROS=1"
) else (
    echo  [OK] Dependencias instaladas.
)
echo.

echo  Verificando PyAudio (microfone)...
"%VENV_PY%" -c "import pyaudio" >nul 2>&1
if errorlevel 1 (
    "%VENV_PIP%" install pyaudio --quiet 2>nul
    if errorlevel 1 (
        echo  [AVISO] PyAudio nao instalado automaticamente. O Rony ainda pode funcionar em modo texto.
    ) else (
        echo  [OK] PyAudio instalado.
    )
) else (
    echo  [OK] PyAudio ja instalado.
)

reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone" /v "Value" /t REG_SZ /d "Allow" /f >nul 2>&1
echo  [OK] Permissao de microfone garantida.
echo.

echo  [4/6] Configurando interface grafica...
node --version >nul 2>&1
if errorlevel 1 (
    echo  [AVISO] Node.js nao encontrado. Frontend pre-compilado sera usado.
) else (
    pushd "%FRONTEND_DIR%"
    call npm.cmd install --silent 2>nul
    if not errorlevel 1 call npm.cmd run build 2>nul
    if errorlevel 1 (
        echo  [AVISO] Build do frontend falhou. Frontend pre-compilado sera usado.
    ) else (
        echo  [OK] Interface compilada.
    )
    popd
)
echo.

echo  [5/6] Configuracao inicial...
if not exist "%RONY_DIR%.env" (
    if exist "%RONY_DIR%.env.example" (
        copy "%RONY_DIR%.env.example" "%RONY_DIR%.env" >nul
        echo  [OK] Arquivo .env criado.
    )
)

"%VENV_PY%" -c "import json, os, pathlib; local=os.environ.get('LOCALAPPDATA') or str(pathlib.Path.home()/'AppData'/'Local'); cfg=pathlib.Path(local)/'Rony'/'data'/'rony_config.json'; print('ok' if cfg.exists() else 'novo')" > "%TEMP%\rony_status.txt" 2>nul
set /p RONY_STATUS=<"%TEMP%\rony_status.txt"
if "%RONY_STATUS%"=="novo" (
    echo  Iniciando assistente de configuracao...
    "%VENV_PY%" "%SETUP_DIR%\setup_wizard.py"
    if errorlevel 1 echo  [AVISO] Configuracao nao concluida. Execute _setup\setup_wizard.py depois.
) else (
    echo  [OK] Rony ja configurado.
)
echo.

echo  [6/6] Criando atalho na area de trabalho...
"%VENV_PY%" "%SETUP_DIR%\criar_atalho.py" 2>nul
if errorlevel 1 (
    echo  [AVISO] Atalho nao criado.
) else (
    echo  [OK] Atalho criado na area de trabalho.
)
echo.

echo  +======================================================+
if "%ERROS%"=="0" (
    echo  ^|   [OK] Instalacao concluida com sucesso!            ^|
) else (
    echo  ^|   [OK] Instalacao concluida com avisos.             ^|
)
echo  +======================================================+
echo.
echo  Como iniciar o Rony:
echo    - Clique duas vezes em: INICIAR_RONY.bat
echo    - Ou use o atalho na area de trabalho, se criado
echo.
pause
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
