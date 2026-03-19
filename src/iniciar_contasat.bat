@echo off
title ContaSAT
cd /d "%~dp0"

echo.
echo  ContaSAT v3.0 - Iniciando...
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

"%VENV_PY%" -c "import flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Instalando flask...
    "%VENV_PIP%" install flask --quiet
)

"%VENV_PY%" -c "from satcfdi.models import Signer" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Instalando satcfdi...
    "%VENV_PIP%" install satcfdi --quiet
)

"%VENV_PY%" -c "import openpyxl" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Instalando openpyxl...
    "%VENV_PIP%" install openpyxl --quiet
)

echo  [OK] Dependencias verificadas.
echo.
echo  [OK] Iniciando ContaSAT en http://localhost:5120
echo       El navegador se abrira automaticamente.
echo.
echo  Para cerrar ContaSAT cierra esta ventana.
echo  -------------------------------------------------------
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
    "%VENV_PY%" -c "import flask; print('flask:', flask.__version__)" 2>&1
    "%VENV_PY%" -c "import satcfdi; print('satcfdi OK')" 2>&1
    echo.
    echo  Opciones:
    echo  1. Ejecuta instalar_contasat.bat nuevamente.
    echo  2. Revisa el log: ..\contabilidad_sat\descarga_sat.log
    echo.
    pause
)
