@echo off
setlocal EnableDelayedExpansion
title ContaSAT - Instalador v1.2

:: ============================================================
::  ContaSAT - Instalador Auto-descarga desde GitHub
::  Repositorio: https://github.com/HHuertaB/contadorcito
:: ============================================================

set "REPO_RAW=https://raw.githubusercontent.com/HHuertaB/contadorcito/main"
set "REPO_URL=https://github.com/HHuertaB/contadorcito"
set "INSTALL_DIR=%USERPROFILE%\ContaSAT"
set "LOG_FILE=%INSTALL_DIR%\logs\instalacion.log"
set "TASK_NAME=ContaSAT_DescargaMensual"
set "PYTHON_URL=https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe"
set "PYTHON_INSTALLER=%TEMP%\python_installer.exe"
set "PYTHON_CMD="

call :print_header
call :check_admin
call :check_internet
call :create_dirs
call :check_python
call :download_scripts
call :install_dependencies
call :register_task
call :create_shortcut
call :final_message
goto :eof


:: ============================================================
:print_header
cls
echo.
echo  +======================================================+
echo  ^|    ContaSAT - Instalador Automatico v1.2            ^|
echo  ^|    Gestion de CFDIs del SAT Mexico                  ^|
echo  ^|    github.com/HHuertaB/contadorcito                 ^|
echo  +======================================================+
echo.
echo  Carpeta : %INSTALL_DIR%
echo  Repo    : %REPO_URL%
echo  -------------------------------------------------------
echo.
goto :eof


:: ============================================================
:check_admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Ejecutar como Administrador.
    echo  Clic derecho sobre el archivo - Ejecutar como administrador
    pause
    exit /b 1
)
echo  [OK] Permisos de administrador confirmados.
goto :eof


:: ============================================================
:check_internet
echo.
echo  [1/7] Verificando conexion a internet...
curl --silent --max-time 10 --head "https://raw.githubusercontent.com" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Sin conexion o GitHub no responde.
    echo          Verifica tu red e intenta nuevamente.
    pause
    exit /b 1
)
echo  [OK] Conexion disponible. GitHub accesible.
goto :eof


:: ============================================================
:create_dirs
echo.
echo  [2/7] Creando carpetas...
if not exist "%INSTALL_DIR%"                   mkdir "%INSTALL_DIR%"
if not exist "%INSTALL_DIR%\efirma"           mkdir "%INSTALL_DIR%\efirma"
if not exist "%INSTALL_DIR%\contabilidad_sat" mkdir "%INSTALL_DIR%\contabilidad_sat"
if not exist "%INSTALL_DIR%\logs"             mkdir "%INSTALL_DIR%\logs"
if not exist "%INSTALL_DIR%\src"              mkdir "%INSTALL_DIR%\src"
echo  [OK] Carpetas creadas.
goto :eof


:: ============================================================
:check_python
echo.
echo  [3/7] Verificando Python...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
    set "PYTHON_CMD=python"
    echo  [OK] Python !PYVER! encontrado.
    goto :eof
)
py --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('py --version 2^>^&1') do set "PYVER=%%v"
    set "PYTHON_CMD=py"
    echo  [OK] Python !PYVER! encontrado.
    goto :eof
)
echo  [INFO] Descargando Python 3.12...
curl --max-time 120 --retry 2 -L "%PYTHON_URL%" -o "%PYTHON_INSTALLER%" --progress-bar
if %errorlevel% neq 0 (
    echo  [ERROR] No se pudo descargar Python. Instala desde python.org
    pause
    exit /b 1
)
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
del "%PYTHON_INSTALLER%" >nul 2>&1
set "PYTHON_CMD=python"
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "PATH=%%b;%PATH%"
echo  [OK] Python 3.12 instalado.
goto :eof


:: ============================================================
:download_scripts
echo.
echo  [4/7] Descargando archivos desde GitHub...
echo.
set "DOWNLOAD_OK=1"

call :download_one "src/descarga_cfdi_sat.py"    "Motor de descarga SAT"
call :download_one "src/contasat_gui.html"        "Interfaz grafica"
call :download_one "src/app.py"                   "Backend principal"
call :download_one "src/instalar_dependencias.py" "Instalador dependencias"
call :download_one "src/iniciar_contasat.bat"     "Lanzador de la aplicacion"

if "!DOWNLOAD_OK!"=="0" (
    echo.
    echo  [ERROR] Una o mas descargas fallaron.
    echo          Revisa el log: %LOG_FILE%
    pause
    exit /b 1
)
echo.
echo  [OK] Todos los archivos descargados.
goto :eof

:download_one
set "DL_FILE=%~1"
set "DL_LABEL=%~2"
set "DL_URL=%REPO_RAW%/%DL_FILE%"
set "DL_DEST=%INSTALL_DIR%\%DL_FILE:/=\%"
echo         %DL_LABEL% ...
curl --silent --show-error --max-time 30 --retry 3 --retry-delay 2 --retry-all-errors -L "%DL_URL%" -o "%DL_DEST%" 2>>"%LOG_FILE%"
if %errorlevel% neq 0 (
    echo         [ERROR] Fallo la descarga: %DL_LABEL%
    set "DOWNLOAD_OK=0"
    goto :eof
)
for %%s in ("%DL_DEST%") do (
    if %%~zs LSS 100 (
        echo         [ERROR] Archivo invalido o 404: %DL_LABEL%
        set "DOWNLOAD_OK=0"
    ) else (
        echo         [OK] %DL_LABEL% (%%~zs bytes)
    )
)
goto :eof


:: ============================================================
:install_dependencies
echo.
echo  [5/7] Instalando dependencias Python...
for %%p in (pywebview cfdiclient openpyxl lxml schedule) do (
    echo         %%p ...
    %PYTHON_CMD% -m pip install %%p --quiet --upgrade >> "%LOG_FILE%" 2>&1
    if !errorlevel! equ 0 (
        echo         [OK] %%p
    ) else (
        echo         [WARN] %%p - ver log
    )
)
echo  [OK] Dependencias instaladas.
goto :eof


:: ============================================================
:register_task
echo.
echo  [6/7] Registrando tarea mensual automatica...
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
schtasks /Create /TN "%TASK_NAME%" /TR ""%INSTALL_DIR%\src\iniciar_contasat.bat"" /SC MONTHLY /D 1 /ST 08:00 /RU "%USERNAME%" /RL HIGHEST /F >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] Tarea: dia 1 de cada mes a las 08:00
) else (
    echo  [WARN] No se pudo registrar la tarea. Configura manualmente.
)
goto :eof


:: ============================================================
:create_shortcut
echo.
echo  [7/7] Creando acceso directo en el Escritorio...
set "SHORTCUT=%USERPROFILE%\Desktop\ContaSAT.lnk"
set "PS1=%TEMP%\cs_shortcut.ps1"
(
    echo $s = (New-Object -COM WScript.Shell^).CreateShortcut('%SHORTCUT%'^)
    echo $s.TargetPath = '%INSTALL_DIR%\src\iniciar_contasat.bat'
    echo $s.WorkingDirectory = '%INSTALL_DIR%\src'
    echo $s.Description = 'ContaSAT - Gestion de CFDIs del SAT'
    echo $s.WindowStyle = 1
    echo $s.Save(^)
) > "%PS1%"
powershell -ExecutionPolicy Bypass -File "%PS1%" >nul 2>&1
del "%PS1%" >nul 2>&1
if exist "%SHORTCUT%" (
    echo  [OK] Acceso directo creado en el Escritorio.
) else (
    echo  [INFO] Acceso directo no se pudo crear automaticamente.
)
goto :eof


:: ============================================================
:final_message
echo.
echo  +======================================================+
echo  ^|           INSTALACION COMPLETADA                    ^|
echo  +======================================================+
echo.
echo  LEE este resumen ANTES de cerrar la ventana.
echo.
echo  -------------------------------------------------------
echo  ARCHIVOS INSTALADOS EN: %INSTALL_DIR%\src
echo  -------------------------------------------------------
if exist "%INSTALL_DIR%\src\app.py"                   echo  [OK] app.py
if exist "%INSTALL_DIR%\src\contasat_gui.html"        echo  [OK] contasat_gui.html
if exist "%INSTALL_DIR%\src\descarga_cfdi_sat.py"     echo  [OK] descarga_cfdi_sat.py
if exist "%INSTALL_DIR%\src\instalar_dependencias.py" echo  [OK] instalar_dependencias.py
if exist "%INSTALL_DIR%\src\iniciar_contasat.bat"     echo  [OK] iniciar_contasat.bat
echo.
echo  -------------------------------------------------------
echo  CONFIGURACION DEL SISTEMA
echo  -------------------------------------------------------
echo  Carpeta de instalacion : %INSTALL_DIR%
echo  Tarea automatica       : Dia 1 de cada mes - 08:00 hrs
echo  Log de instalacion     : %LOG_FILE%
echo  Repositorio            : %REPO_URL%
echo.
echo  -------------------------------------------------------
echo  PROXIMOS PASOS
echo  -------------------------------------------------------
echo.
echo  1. Revisa que todos los archivos aparezcan como [OK].
echo     Si alguno falla, ejecuta el instalador nuevamente.
echo.
echo  2. Abre ContaSAT desde el acceso directo del Escritorio.
echo     Si hay algun error al abrir, la ventana mostrara
echo     el mensaje exacto en lugar de cerrarse sola.
echo.
echo  3. En Configuracion escribe tu RFC.
echo.
echo  4. Copia tu e.firma (.cer y .key) a:
echo       %INSTALL_DIR%\efirma\
echo.
echo  5. En Descarga SAT carga tu e.firma y descarga tus CFDIs.
echo.
echo  -------------------------------------------------------
echo  Presiona cualquier tecla para cerrar esta ventana.
echo  -------------------------------------------------------
echo.
pause >nul
goto :eof
