@echo off
chcp 65001 >nul
title R.O.N.Y — Atualizacao
setlocal

set "RONY_DIR=%~dp0"
set "VENV_PY=%RONY_DIR%venv\Scripts\python.exe"
set "VENV_PIP=%RONY_DIR%venv\Scripts\pip.exe"
set "FRONTEND_DIR=%RONY_DIR%frontend"

cls
echo.
echo  +======================================================+
echo  ^|   R.O.N.Y — Atualizacao                             ^|
echo  +======================================================+
echo.

if not exist "%VENV_PY%" (
    echo  [ERRO] Rony nao instalado. Execute INSTALAR.bat primeiro.
    pause
    exit /b 1
)

:: ── Dependencias Python ───────────────────────────────────────
echo  [1/3] Atualizando dependencias Python...
"%VENV_PIP%" install -r "%RONY_DIR%requirements.txt" --upgrade --quiet
if errorlevel 1 (
    echo  [AVISO] Algumas dependencias nao atualizaram.
) else (
    echo  [OK] Dependencias atualizadas.
)
echo.

:: ── Frontend ──────────────────────────────────────────────────
echo  [2/3] Atualizando interface grafica...
node --version >nul 2>&1
if errorlevel 1 (
    echo  [AVISO] Node.js nao encontrado. Frontend nao atualizado.
) else (
    pushd "%FRONTEND_DIR%"
    call npm install --silent 2>nul
    call npm run build 2>nul
    if errorlevel 1 (
        echo  [AVISO] Build do frontend falhou.
    ) else (
        echo  [OK] Interface recompilada.
    )
    popd
)
echo.

:: ── Atalho ────────────────────────────────────────────────────
echo  [3/3] Atualizando atalho...
"%VENV_PY%" "%RONY_DIR%_setup\criar_atalho.py" 2>nul
echo  [OK] Atalho atualizado.
echo.

echo  +======================================================+
echo  ^|   Atualizacao concluida! Reinicie o Rony.           ^|
echo  +======================================================+
echo.
pause
