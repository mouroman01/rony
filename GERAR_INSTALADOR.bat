@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title Gerar Instalador Rony

set "ROOT=%~dp0"
set "ISS=%ROOT%installer\Setup.iss"
set "OUTPUT=%ROOT%installer_output"

echo.
echo  +======================================================+
echo  ^|   R.O.N.Y  ^|  Gerando Instalador Setup.exe           ^|
echo  +======================================================+
echo.

:: ── Verifica Rony.exe ─────────────────────────────────────────
if not exist "%ROOT%release\Rony.exe" (
    echo  [AVISO] release\Rony.exe nao encontrado.
    echo  Execute GERAR_EXECUTAVEL.bat primeiro.
    echo.
    set /p CONT=  Continuar mesmo assim? [S/N]:
    if /i not "!CONT!"=="S" exit /b 1
)

:: ── Localiza Inno Setup (sem for loop) ───────────────────────
set "INNO="

set "P1=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
set "P2=%ProgramFiles%\Inno Setup 6\ISCC.exe"
set "P3=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
set "P4=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
set "P5=C:\Program Files\Inno Setup 6\ISCC.exe"

if exist "%P1%" set "INNO=%P1%"
if exist "%P2%" set "INNO=%P2%"
if exist "%P3%" set "INNO=%P3%"
if exist "%P4%" set "INNO=%P4%"
if exist "%P5%" set "INNO=%P5%"

if not defined INNO (
    echo  [ERRO] Inno Setup 6 nao encontrado.
    echo.
    echo  Baixe gratuitamente em:
    echo  https://jrsoftware.org/isdl.php
    echo.
    pause & exit /b 1
)

echo  [OK] Inno Setup: %INNO%

:: ── Cria pasta de saida ───────────────────────────────────────
if not exist "%OUTPUT%" mkdir "%OUTPUT%"

:: ── Compila o instalador ──────────────────────────────────────
echo.
echo  [BUILD] Compilando instalador...
echo.

"%INNO%" "%ISS%"

if errorlevel 1 (
    echo.
    echo  [ERRO] Falha ao gerar o instalador.
    pause & exit /b 1
)

:: ── Resultado ─────────────────────────────────────────────────
echo.
echo  [OK] Instalador gerado com sucesso!
echo.
echo  Arquivo gerado em:
echo  %OUTPUT%\
dir "%OUTPUT%\Rony_Setup*.exe" /b 2>nul
echo.
echo  Proximo passo:
echo    1. Crie um GitHub Release com a tag v1.0.0
echo    2. Anexe o Rony_Setup_1.0.0.exe ao release
echo    3. Atualize update_manifest.json com a URL
echo    4. git push - todos os Ronys instalados recebem a atualizacao
echo.
pause
endlocal
