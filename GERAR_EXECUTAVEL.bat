@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
title Gerar Executavel Rony

set "ROOT=%~dp0"
set "VENV_PY=%ROOT%venv\Scripts\python.exe"
set "RELEASE=%ROOT%release"
set "BUILD_TMP=%ROOT%build_tmp"

echo.
echo  +======================================================+
echo  ^|   R.O.N.Y  ^|  Gerando Rony.exe (launcher)            ^|
echo  +======================================================+
echo.

:: ── Verifica venv ─────────────────────────────────────────────
if not exist "%VENV_PY%" (
    echo  [ERRO] venv nao encontrado. Execute INSTALAR.bat primeiro.
    pause & exit /b 1
)

if not exist "%ROOT%launcher.py" (
    echo  [ERRO] launcher.py nao encontrado.
    pause & exit /b 1
)

:: ── Instala PyInstaller ───────────────────────────────────────
echo  [1/4] Verificando PyInstaller...
"%VENV_PY%" -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Instalando PyInstaller...
    "%VENV_PY%" -m pip install pyinstaller --quiet --no-cache-dir
    if errorlevel 1 (
        echo  [ERRO] Falha ao instalar PyInstaller.
        pause & exit /b 1
    )
)
echo  [OK] PyInstaller pronto.

:: ── Frontend ─────────────────────────────────────────────────
echo.
echo  [2/4] Verificando frontend...
if exist "%ROOT%frontend\dist\index.html" (
    echo  [OK] frontend\dist encontrado.
) else (
    if exist "%ROOT%frontend\package.json" (
        echo  [INFO] Compilando frontend...
        pushd "%ROOT%frontend"
        if not exist "node_modules" npm install --silent
        npm run build
        popd
    ) else (
        echo  [AVISO] frontend nao encontrado. Continuando.
    )
)

:: ── Limpa builds anteriores ───────────────────────────────────
if exist "%BUILD_TMP%" rmdir /s /q "%BUILD_TMP%"
if not exist "%RELEASE%" mkdir "%RELEASE%"
if exist "%RELEASE%\Rony.exe" del /f /q "%RELEASE%\Rony.exe"

:: ── Compila launcher.py → Rony.exe ───────────────────────────
echo.
echo  [3/4] Compilando Rony.exe...
echo.

:: Verifica se tem icone
if exist "%ROOT%app.ico" (
    "%VENV_PY%" -m PyInstaller --onefile --noconsole --name Rony --distpath "%RELEASE%" --workpath "%BUILD_TMP%" --specpath "%BUILD_TMP%" --icon "%ROOT%app.ico" "%ROOT%launcher.py"
) else (
    "%VENV_PY%" -m PyInstaller --onefile --noconsole --name Rony --distpath "%RELEASE%" --workpath "%BUILD_TMP%" --specpath "%BUILD_TMP%" "%ROOT%launcher.py"
)

:: ── Limpeza ───────────────────────────────────────────────────
if exist "%BUILD_TMP%" rmdir /s /q "%BUILD_TMP%"

:: ── Resultado ─────────────────────────────────────────────────
echo.
echo  [4/4] Verificando resultado...
if exist "%RELEASE%\Rony.exe" (
    echo  [OK] Executavel gerado com sucesso!
    echo       %RELEASE%\Rony.exe
    echo.
    echo  Proximo passo: execute GERAR_INSTALADOR.bat
) else (
    echo  [ERRO] Rony.exe nao foi gerado. Verifique os erros acima.
    pause & exit /b 1
)

echo.
pause
endlocal
