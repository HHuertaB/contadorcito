@echo off
title ContaSAT
cd /d "%~dp0"

echo.
echo  ContaSAT - Iniciando...
echo  -------------------------------------------------------
echo.

:: Ruta del entorno virtual relativa a la carpeta src
set "VENV_PY=%~dp0..\venv\Scripts\python.exe"
set "VENV_PIP=%~dp0..\venv\Scripts\pip.exe"

:: Verificar que el entorno virtual exista
if not exist "%VENV_PY%" (
    echo  [ERROR] Entorno virtual no encontrado.
    echo.
    echo  Ejecuta instalar_contasat.bat nuevamente para crearlo.
    echo.
    pause
    exit /b 1
)

:: Verificar que app.py exista
if not exist "%~dp0app.py" (
    echo  [ERROR] No se encontro app.py.
    echo          Ejecuta instalar_contasat.bat nuevamente.
    pause
    exit /b 1
)

:: Verificar cfdiclient dentro del venv
echo  Verificando dependencias...
"%VENV_PY%" -c "from cfdiclient import Autenticacion, DescargaMasiva, Fiel, SolicitaDescarga, VerificaSolicitudDescarga" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Reinstalando cfdiclient en el entorno virtual...
    "%VENV_PIP%" install cfdiclient --force-reinstall --quiet
    "%VENV_PY%" -c "from cfdiclient import Autenticacion, DescargaMasiva, Fiel, SolicitaDescarga, VerificaSolicitudDescarga" >nul 2>&1
    if %errorlevel% neq 0 (
        echo  [ERROR] cfdiclient no funciona.
        echo          Ejecuta instalar_contasat.bat nuevamente.
        pause
        exit /b 1
    )
)

:: Verificar pywebview dentro del venv
"%VENV_PY%" -c "import webview" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [INFO] Instalando pywebview en el entorno virtual...
    "%VENV_PIP%" install pywebview --quiet
)

echo  [OK] Dependencias verificadas en el entorno virtual.
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
    "%VENV_PY%" -c "import cfdiclient; print('cfdiclient: OK')" 2>&1
    "%VENV_PY%" -c "import webview; print('pywebview: OK')" 2>&1
    echo.
    echo  Opciones:
    echo  1. Ejecuta instalar_contasat.bat nuevamente.
    echo  2. Revisa el log: ..\contabilidad_sat\descarga_sat.log
    echo.
    pause
)
