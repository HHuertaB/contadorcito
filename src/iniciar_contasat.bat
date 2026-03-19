@echo off
title ContaSAT
cd /d "%~dp0"

echo.
echo  ContaSAT - Iniciando...
echo  -------------------------------------------------------
echo.

:: Detectar Python
set "PYTHON="
python --version >nul 2>&1
if %errorlevel% equ 0 set "PYTHON=python"
if not defined PYTHON (
    py --version >nul 2>&1
    if %errorlevel% equ 0 set "PYTHON=py"
)
if not defined PYTHON (
    echo  [ERROR] Python no encontrado.
    echo          Ejecuta instalar_contasat.bat nuevamente.
    pause
    exit /b 1
)

:: Verificar app.py
if not exist "%~dp0app.py" (
    echo  [ERROR] No se encontro app.py en:
    echo          %~dp0
    echo          Ejecuta instalar_contasat.bat nuevamente.
    pause
    exit /b 1
)

:: Verificar e instalar dependencias si faltan
echo  Verificando dependencias...
%PYTHON% -c "from cfdiclient import Autenticacion, DescargaMasiva, Fiel, SolicitaDescarga, VerificaSolicitudDescarga" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Actualizando cfdiclient a la version mas reciente...
    %PYTHON% -m pip install "cfdiclient>=1.5.9" --upgrade --quiet
    if %errorlevel% neq 0 (
        echo  [ERROR] No se pudo instalar cfdiclient.
        echo          Verifica tu conexion a internet.
        pause
        exit /b 1
    )
)

%PYTHON% -c "import webview" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Instalando pywebview...
    %PYTHON% -m pip install pywebview --quiet
)

%PYTHON% -c "import openpyxl" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Instalando openpyxl...
    %PYTHON% -m pip install openpyxl --quiet
)

echo  [OK] Dependencias verificadas.
echo.
echo  [OK] Abriendo ContaSAT...
echo.

%PYTHON% app.py

if %errorlevel% neq 0 (
    echo.
    echo  -------------------------------------------------------
    echo  [ERROR] ContaSAT cerro con un error (codigo: %errorlevel%)
    echo  -------------------------------------------------------
    echo.
    echo  Informacion de diagnostico:
    %PYTHON% --version
    %PYTHON% -c "import cfdiclient; print('cfdiclient: OK')" 2>&1
    %PYTHON% -c "import webview; print('pywebview: OK')" 2>&1
    echo.
    echo  Si el problema persiste:
    echo  1. Ejecuta instalar_contasat.bat nuevamente
    echo  2. Revisa el log en: ..\contabilidad_sat\descarga_sat.log
    echo.
    pause
)
