@echo off
title ContaSAT
cd /d "%~dp0"

echo.
echo  ContaSAT - Iniciando...
echo  -------------------------------------------------------
echo.

set "VENV_PY=%~dp0..\venv\Scripts\python.exe"
set "VENV_PIP=%~dp0..\venv\Scripts\pip.exe"

if not exist "%VENV_PY%" (
    echo  [ERROR] Entorno virtual no encontrado.
    echo          Ejecuta instalar_contasat.bat nuevamente.
    pause
    exit /b 1
)

if not exist "%~dp0app.py" (
    echo  [ERROR] No se encontro app.py.
    echo          Ejecuta instalar_contasat.bat nuevamente.
    pause
    exit /b 1
)

echo  Verificando dependencias...

:: satcfdi
"%VENV_PY%" -c "from satcfdi.models import Signer; from satcfdi.pacs.sat import SAT, TipoDescargaMasivaTerceros" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Instalando satcfdi...
    "%VENV_PIP%" install satcfdi --quiet
    "%VENV_PY%" -c "from satcfdi.models import Signer" >nul 2>&1
    if %errorlevel% neq 0 (
        echo  [ERROR] No se pudo instalar satcfdi.
        echo          Verifica tu conexion a internet y ejecuta instalar_contasat.bat.
        pause
        exit /b 1
    )
)

:: pywebview
"%VENV_PY%" -c "import webview" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Instalando pywebview...
    "%VENV_PIP%" install pywebview --quiet
)

:: openpyxl
"%VENV_PY%" -c "import openpyxl" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Instalando openpyxl...
    "%VENV_PIP%" install openpyxl --quiet
)

echo  [OK] Dependencias verificadas.
echo.
echo  [OK] Abriendo ContaSAT...
echo.

"%VENV_PY%" app.py

if %errorlevel% neq 0 (
    echo.
    echo  -------------------------------------------------------
    echo  [ERROR] ContaSAT cerro con un error (codigo: %errorlevel%)
    echo  -------------------------------------------------------
    echo.
    echo  Diagnostico:
    "%VENV_PY%" --version
    "%VENV_PY%" -c "import satcfdi; print('satcfdi: OK')" 2>&1
    "%VENV_PY%" -c "import webview; print('pywebview: OK')" 2>&1
    echo.
    echo  Opciones:
    echo  1. Ejecuta instalar_contasat.bat nuevamente.
    echo  2. Revisa el log: ..\contabilidad_sat\descarga_sat.log
    echo.
    pause
)
