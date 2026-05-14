@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title R.O.N.Y — Instalacao

cls
echo.
echo  +======================================================+
echo  ^|   R.O.N.Y  ^|  Responsive Omni-lingual Neural sYstem  ^|
echo  ^|   Instalador v1.0  ^|  github.com/rony                 ^|
echo  +======================================================+
echo.

set "RONY_DIR=%~dp0"
set "VENV_DIR=%RONY_DIR%venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"
set "FRONTEND_DIR=%RONY_DIR%frontend"
set "SETUP_DIR=%RONY_DIR%_setup"
set "ERROS=0"

:: ════════════════════════════════════════════════════════════
::  PASSO 1 — Python
:: ════════════════════════════════════════════════════════════
echo  [1/6] Verificando Python...

python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [ERRO] Python nao encontrado no PATH!
    echo.
    echo  Instale o Python 3.11 ou superior:
    echo  https://www.python.org/downloads/
    echo.
    echo  IMPORTANTE: marque "Add Python to PATH" durante a instalacao!
    echo.
    pause
    exit /b 1
)

:: Verifica versao minima (3.10)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
for /f "tokens=1,2 delims=." %%a in ("%PY_VER%") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)
if %PY_MAJOR% LSS 3 (
    echo  [ERRO] Python %PY_VER% encontrado. Requer Python 3.10+
    echo  Baixe em: https://www.python.org/downloads/
    pause
    exit /b 1
)
if %PY_MAJOR% EQU 3 if %PY_MINOR% LSS 10 (
    echo  [ERRO] Python %PY_VER% encontrado. Requer Python 3.10+
    echo  Baixe em: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Verifica se e versao do Windows Store (problematica)
python -c "import sys; exit(0 if sys.executable and 'WindowsApps' not in sys.executable else 1)" >nul 2>&1
if errorlevel 1 (
    echo.
    echo  [AVISO] Python do Windows Store detectado!
    echo  Recomendamos instalar o Python diretamente de python.org
    echo  para evitar problemas com permissoes e microfone.
    echo.
    echo  Continuar mesmo assim? [S/N]
    set /p CONTINUAR=  Opcao:
    if /i "!CONTINUAR!" NEQ "S" exit /b 1
)

echo  [OK] Python %PY_VER%
echo.

:: ════════════════════════════════════════════════════════════
::  PASSO 2 — Ambiente virtual
:: ════════════════════════════════════════════════════════════
echo  [2/6] Configurando ambiente virtual...

if not exist "%VENV_DIR%" (
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo  [ERRO] Falha ao criar ambiente virtual.
        set ERROS=1
    ) else (
        echo  [OK] Ambiente virtual criado.
    )
) else (
    echo  [OK] Ambiente virtual ja existe.
)
echo.

:: ════════════════════════════════════════════════════════════
::  PASSO 3 — Dependencias Python
:: ════════════════════════════════════════════════════════════
echo  [3/6] Instalando dependencias Python...
echo  (Isso pode levar alguns minutos na primeira vez)
echo.

"%VENV_PY%" -m pip install --upgrade pip --quiet
"%VENV_PIP%" install -r "%RONY_DIR%requirements.txt" --no-warn-script-location
if errorlevel 1 (
    echo.
    echo  [AVISO] Alguns pacotes falharam. Tentando continuar...
    set ERROS=1
) else (
    echo.
    echo  [OK] Dependencias instaladas.
)
echo.

:: ════════════════════════════════════════════════════════════
::  PASSO 3b — PyAudio (microfone)
:: ════════════════════════════════════════════════════════════
echo  Verificando PyAudio (microfone)...

"%VENV_PY%" -c "import pyaudio" >nul 2>&1
if errorlevel 1 (
    echo  Instalando PyAudio...
    "%VENV_PIP%" install pyaudio --quiet 2>nul
    if errorlevel 1 (
        "%VENV_PIP%" install pipwin --quiet
        "%VENV_PY%" -m pipwin install pyaudio --quiet 2>nul
        if errorlevel 1 (
            echo  [AVISO] PyAudio nao instalado automaticamente.
            echo  O Rony funcionara sem microfone (modo texto apenas).
            echo  Para instalar manualmente: venv\Scripts\pipwin install pyaudio
        ) else (
            echo  [OK] PyAudio instalado via pipwin.
        )
    ) else (
        echo  [OK] PyAudio instalado.
    )
) else (
    echo  [OK] PyAudio ja instalado.
)
echo.

:: ════════════════════════════════════════════════════════════
::  PASSO 3c — Permissao e configuracao do microfone
:: ════════════════════════════════════════════════════════════
echo  Configurando microfone automaticamente...

"%VENV_PY%" -c "
import json, os, pathlib, sys
try:
    import pyaudio
    p = pyaudio.PyAudio()
    candidatos = []
    virtuais = ['mapper', 'mapeador', 'primario', 'primary', 'driver de captura']
    for i in range(p.get_device_count()):
        d = p.get_device_info_by_index(i)
        if d['maxInputChannels'] > 0:
            nome = d['name'].lower()
            eh_virtual = any(v in nome for v in virtuais)
            candidatos.append((i, d['name'], eh_virtual))
    p.terminate()
    reais = [(i, n) for i, n, v in candidatos if not v]
    escolhido_idx, escolhido_nome = (reais[0] if reais else candidatos[0]) if candidatos else (None, 'desconhecido')
    local = os.environ.get('LOCALAPPDATA') or str(pathlib.Path.home() / 'AppData' / 'Local')
    cfg_path = pathlib.Path(local) / 'Rony' / 'data' / 'rony_config.json'
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    dados = json.loads(cfg_path.read_text(encoding='utf-8')) if cfg_path.exists() else {}
    dados['mic_device_index'] = escolhido_idx
    cfg_path.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Microfone configurado: [{escolhido_idx}] {escolhido_nome}')
except Exception as e:
    print(f'Aviso: nao foi possivel configurar microfone automaticamente ({e})')
" 2>nul

:: Garante permissao de microfone no registro do Windows
reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone" /v "Value" /t REG_SZ /d "Allow" /f >nul 2>&1
echo  [OK] Permissao de microfone garantida.
echo.

:: ════════════════════════════════════════════════════════════
::  PASSO 4 — Frontend (Node.js + Vite)
:: ════════════════════════════════════════════════════════════
echo  [4/6] Configurando interface grafica...

set "NODE_OK=0"
node --version >nul 2>&1
if not errorlevel 1 set "NODE_OK=1"

if "%NODE_OK%"=="1" (
    for /f "tokens=*" %%v in ('node --version 2^>^&1') do set NODE_VER=%%v
    echo  [OK] Node.js !NODE_VER! encontrado.
    echo  Instalando dependencias do frontend...
    pushd "%FRONTEND_DIR%"
    call npm install --silent 2>nul
    if errorlevel 1 (
        echo  [AVISO] npm install falhou.
    ) else (
        echo  Compilando interface...
        call npm run build 2>nul
        if errorlevel 1 (
            echo  [AVISO] Build do frontend falhou. Modo dev sera usado.
        ) else (
            echo  [OK] Interface compilada com sucesso.
        )
    )
    popd
) else (
    echo  [AVISO] Node.js nao encontrado.
    echo  A interface 3D requer Node.js: https://nodejs.org
    echo  O Rony pode funcionar sem ela (linha de comando apenas).
)
echo.

:: ════════════════════════════════════════════════════════════
::  PASSO 5 — Configuracao (.env e wizard)
:: ════════════════════════════════════════════════════════════
echo  [5/6] Configuracao inicial...

if not exist "%RONY_DIR%.env" (
    if exist "%RONY_DIR%.env.example" (
        copy "%RONY_DIR%.env.example" "%RONY_DIR%.env" >nul
        echo  [OK] Arquivo .env criado.
    )
)

:: Verifica se ja foi configurado (config fica em AppData)
"%VENV_PY%" -c "
import json, os, pathlib
local = os.environ.get('LOCALAPPDATA') or str(pathlib.Path.home() / 'AppData' / 'Local')
cfg = pathlib.Path(local) / 'Rony' / 'data' / 'rony_config.json'
try:
    d = json.loads(cfg.read_text())
    print('ok' if d.get('nom_utilisateur','') not in ('','Romano','') else 'novo')
except:
    print('novo')
" > "%TEMP%\rony_status.txt" 2>nul
set /p RONY_STATUS=<"%TEMP%\rony_status.txt"

if "%RONY_STATUS%"=="novo" (
    echo  Iniciando assistente de configuracao...
    echo.
    "%VENV_PY%" "%SETUP_DIR%\setup_wizard.py"
    if errorlevel 1 (
        echo  [AVISO] Configuracao nao concluida. Execute _setup\setup_wizard.py depois.
    )
) else (
    echo  [OK] Rony ja configurado.
)
echo.

:: ════════════════════════════════════════════════════════════
::  PASSO 6 — Atalho na area de trabalho
:: ════════════════════════════════════════════════════════════
echo  [6/6] Criando atalho na area de trabalho...

"%VENV_PY%" "%SETUP_DIR%\criar_atalho.py" 2>nul
if errorlevel 1 (
    echo  [AVISO] Atalho nao criado (sem permissao ou win32com ausente).
) else (
    echo  [OK] Atalho criado na area de trabalho.
)
echo.

:: ════════════════════════════════════════════════════════════
::  RESUMO FINAL
:: ════════════════════════════════════════════════════════════
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
echo    - Ou use o atalho na area de trabalho (se criado)
echo.
echo  Configuracoes importantes:
echo    - Chaves de API:     .env
echo    - Reconfigurar:      _setup\setup_wizard.py
echo.
if "%ERROS%"=="1" (
    echo  [AVISO] Alguns componentes opcionais nao foram instalados.
    echo  O Rony funcionara com funcionalidades reduzidas.
    echo  Veja os avisos acima para mais detalhes.
    echo.
)
pause
