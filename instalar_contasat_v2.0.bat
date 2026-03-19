@echo off
setlocal EnableDelayedExpansion
title ContaSAT - Instalador v1.3

:: ============================================================
::  ContaSAT - Instalador Auto-descarga desde GitHub
::  Repositorio: https://github.com/HHuertaB/contadorcito
:: ============================================================

set "REPO_RAW=https://raw.githubusercontent.com/HHuertaB/contadorcito/main"
set "REPO_URL=https://github.com/HHuertaB/contadorcito"
set "INSTALL_DIR=%USERPROFILE%\ContaSAT"
set "VENV_DIR=%INSTALL_DIR%\venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"
set "LOG_FILE=%INSTALL_DIR%\logs\instalacion.log"
set "TASK_NAME=ContaSAT_DescargaMensual"
set "PYTHON_URL=https://www.python.org/ftp/python/3.12.4/python-3.12.4-amd64.exe"
set "PYTHON_INSTALLER=%TEMP%\python_installer.exe"
set "SYSTEM_PYTHON="

call :print_header
call :check_admin
call :check_internet
call :create_dirs
call :check_python
call :create_venv
call :install_dependencies
call :download_scripts
call :register_task
call :create_shortcut
call :final_message
goto :eof


:: ============================================================
:print_header
cls
echo.
echo  +======================================================+
echo  ^|    ContaSAT - Instalador Automatico v1.3            ^|
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
echo  [OK] Conexion disponible.
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
echo  [3/7] Verificando Python del sistema...

:: Buscar Python 3.10 o superior en el sistema
for %%v in (python python3 py) do (
    %%v --version >nul 2>&1
    if !errorlevel! equ 0 (
        for /f "tokens=2" %%n in ('%%v --version 2^>^&1') do (
            for /f "tokens=1,2 delims=." %%a in ("%%n") do (
                if %%a equ 3 if %%b GEQ 10 (
                    set "SYSTEM_PYTHON=%%v"
                    echo  [OK] Python %%n encontrado (%%v^).
                )
            )
        )
    )
)

if not defined SYSTEM_PYTHON (
    :: Intentar con cualquier Python 3 aunque sea menor a 3.10
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        set "SYSTEM_PYTHON=python"
        echo  [WARN] Python encontrado pero puede ser version menor a 3.10.
        echo         Se intentara crear el entorno virtual de todas formas.
    ) else (
        py --version >nul 2>&1
        if %errorlevel% equ 0 (
            set "SYSTEM_PYTHON=py"
            echo  [WARN] Python encontrado (launcher py^).
        ) else (
            echo  [INFO] Python no encontrado. Descargando Python 3.12...
            curl --max-time 120 --retry 2 -L "%PYTHON_URL%" -o "%PYTHON_INSTALLER%" --progress-bar
            if %errorlevel% neq 0 (
                echo  [ERROR] No se pudo descargar Python. Instala desde python.org
                pause
                exit /b 1
            )
            echo  [INFO] Instalando Python 3.12...
            "%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
            del "%PYTHON_INSTALLER%" >nul 2>&1
            set "SYSTEM_PYTHON=python"
            for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "PATH=%%b;%PATH%"
            echo  [OK] Python 3.12 instalado.
        )
    )
)
goto :eof


:: ============================================================
:create_venv
echo.
echo  [4/7] Configurando entorno virtual (venv)...

if exist "%VENV_PY%" (
    echo  [OK] Entorno virtual ya existe. Actualizando pip...
    "%VENV_PY%" -m pip install --upgrade pip --quiet >> "%LOG_FILE%" 2>&1
    goto :eof
)

echo         Creando entorno virtual en: %VENV_DIR%
%SYSTEM_PYTHON% -m venv "%VENV_DIR%"
if %errorlevel% neq 0 (
    echo  [ERROR] No se pudo crear el entorno virtual.
    echo          Asegurate de tener Python 3.10 o superior instalado.
    echo          Descarga Python desde: https://python.org
    pause
    exit /b 1
)

echo         Actualizando pip dentro del entorno virtual...
"%VENV_PY%" -m pip install --upgrade pip --quiet >> "%LOG_FILE%" 2>&1
echo  [OK] Entorno virtual listo en: %VENV_DIR%
goto :eof


:: ============================================================
:install_dependencies
echo.
echo  [5/7] Instalando dependencias en el entorno virtual...
echo         (Esto puede tardar unos minutos la primera vez^)
echo.

:: Instalar paquetes base del entorno virtual
for %%p in (pywebview openpyxl lxml schedule) do (
    echo         Instalando %%p ...
    "%VENV_PIP%" install %%p --quiet >> "%LOG_FILE%" 2>&1
    if !errorlevel! equ 0 (
        echo         [OK] %%p
    ) else (
        echo         [WARN] %%p - revisa el log: %LOG_FILE%
    )
)

:: satcfdi: libreria estable para descarga de CFDIs del SAT
echo         Instalando satcfdi ...
"%VENV_PIP%" install satcfdi --quiet >> "%LOG_FILE%" 2>&1
"%VENV_PY%" -c "from satcfdi.models import Signer; from satcfdi.pacs.sat import SAT" >nul 2>&1
if %errorlevel% neq 0 (
    echo         [ERROR] satcfdi no funciona. Revisa: %LOG_FILE%
) else (
    echo         [OK] satcfdi
)

echo.
echo  [OK] Dependencias instaladas en el entorno virtual.
goto :eof


:: ============================================================
:download_scripts
echo.
echo  [6/7] Descargando archivos desde GitHub...
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
        echo         [OK] %DL_LABEL% (%%~zs bytes^)
    )
)
goto :eof


:: ============================================================
:register_task
echo.
echo  [7/7] Registrando tarea mensual y acceso directo...
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1
schtasks /Create /TN "%TASK_NAME%" /TR ""%INSTALL_DIR%\src\iniciar_contasat.bat"" /SC MONTHLY /D 1 /ST 08:00 /RU "%USERNAME%" /RL HIGHEST /F >nul 2>&1
if %errorlevel% equ 0 (
    echo  [OK] Tarea programada: dia 1 de cada mes a las 08:00
) else (
    echo  [WARN] No se pudo registrar la tarea automatica.
)
goto :eof


:: ============================================================
:create_shortcut
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
if exist "%VENV_PY%"                                    echo  [OK] Entorno virtual Python (venv)
echo.
echo  -------------------------------------------------------
echo  CONFIGURACION DEL SISTEMA
echo  -------------------------------------------------------
echo  Carpeta de instalacion : %INSTALL_DIR%
echo  Entorno virtual        : %VENV_DIR%
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
echo     Si hay error, la ventana mostrara el mensaje exacto.
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
