@echo off
title ContaSAT
cd /d "%~dp0"

echo Iniciando ContaSAT...
echo.

:: Verificar que Python este disponible
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python no encontrado.
        echo         Reinstala ContaSAT ejecutando instalar_contasat.bat
        echo.
        pause
        exit /b 1
    )
    set "PYTHON=py"
) else (
    set "PYTHON=python"
)

:: Verificar que app.py exista
if not exist "%~dp0app.py" (
    echo [ERROR] No se encontro app.py en: %~dp0
    echo         Reinstala ContaSAT ejecutando instalar_contasat.bat
    echo.
    pause
    exit /b 1
)

:: Verificar que pywebview este instalado
%PYTHON% -c "import webview" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Instalando pywebview...
    %PYTHON% -m pip install pywebview --quiet
)

:: Lanzar la aplicacion
echo [OK] Abriendo ContaSAT...
%PYTHON% app.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] ContaSAT cerro con un error (codigo: %errorlevel%)
    echo.
    echo Si el problema persiste, ejecuta instalar_contasat.bat nuevamente
    echo o revisa el log en: ..\contabilidad_sat\descarga_sat.log
    echo.
    pause
)
