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

:: Verificar cfdiclient con la API correcta
echo  Verificando cfdiclient...
"%VENV_PY%" -c "from cfdiclient import Autenticacion, DescargaMasiva, Fiel, SolicitaDescarga, VerificaSolicitudDescarga" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Instalando cfdiclient 1.5.9 (version estable)...
    "%VENV_PIP%" install cfdiclient==1.5.9 --quiet
    if %errorlevel% neq 0 (
        echo  [INFO] PyPI fallo, instalando desde GitHub...
        "%VENV_PIP%" install "git+https://github.com/luisiturrios1/python-cfdiclient.git@1.5.9" --quiet
    )
    "%VENV_PY%" -c "from cfdiclient import Autenticacion, DescargaMasiva, Fiel, SolicitaDescarga, VerificaSolicitudDescarga" >nul 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo  [ERROR] No se pudo instalar cfdiclient correctamente.
        echo.
        echo  Intenta manualmente en una terminal:
        echo    %VENV_PIP% install cfdiclient==1.5.9
        echo.
        "%VENV_PY%" -c "import cfdiclient; print('Version:', getattr(cfdiclient,'__version__','?')); print('Disponible:', [x for x in dir(cfdiclient) if not x.startswith('_')])"
        echo.
        pause
        exit /b 1
    )
    echo  [OK] cfdiclient 1.5.9 instalado.
)

:: Verificar pywebview
"%VENV_PY%" -c "import webview" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Instalando pywebview...
    "%VENV_PIP%" install pywebview --quiet
)

:: Verificar openpyxl
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
    "%VENV_PY%" -c "import cfdiclient; print('cfdiclient', getattr(cfdiclient,'__version__','?'))" 2>&1
    "%VENV_PY%" -c "import webview; print('pywebview OK')" 2>&1
    echo.
    echo  Opciones:
    echo  1. Ejecuta instalar_contasat.bat nuevamente.
    echo  2. Revisa el log: ..\contabilidad_sat\descarga_sat.log
    echo.
    pause
)
