@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title ContaSAT — Instalador v1.0

:: ════════════════════════════════════════════════════════════
::  ContaSAT — Instalador Auto-descarga desde GitHub
::  Repositorio: https://github.com/HHuertaB/contadorcito
::
::  Este archivo es el UNICO que necesitas descargar.
::  El resto lo descarga e instala automaticamente.
:: ════════════════════════════════════════════════════════════

:: ── URLs base del repositorio ───────────────────────────────
set "REPO_RAW=https://raw.githubusercontent.com/HHuertaB/contadorcito/main"
set "REPO_URL=https://github.com/HHuertaB/contadorcito"

:: ── Archivos a descargar ────────────────────────────────────
set "FILE_MOTOR=src/descarga_cfdi_sat.py"
set "FILE_GUI=src/contasat_gui.html"
set "FILE_DEPS=src/instalar_dependencias.py"

:: ── Directorio de instalacion ───────────────────────────────
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


:: ════════════════════════════════════════════════════════════
:print_header
cls
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║       ContaSAT  —  Instalador Automatico v1.0       ║
echo  ║       Gestion de CFDIs del SAT Mexico               ║
echo  ║       github.com/HHuertaB/contadorcito              ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  Carpeta de instalacion : %INSTALL_DIR%
echo  Repositorio            : %REPO_URL%
echo  ─────────────────────────────────────────────────────
echo.
goto :eof


:: ════════════════════════════════════════════════════════════
:check_admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Se requieren permisos de Administrador.
    echo.
    echo  Haz clic derecho en este archivo y selecciona:
    echo  "Ejecutar como administrador"
    echo.
    pause & exit /b 1
)
echo  [OK] Permisos de administrador confirmados.
goto :eof


:: ════════════════════════════════════════════════════════════
:check_internet
echo.
echo  [1/7] Verificando conexion a internet...
curl -s --head "https://github.com" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Sin conexion a internet. Este instalador
    echo          necesita descargar archivos de GitHub.
    echo          Verifica tu red e intenta nuevamente.
    pause & exit /b 1
)
echo  [OK] Conexion a internet disponible.
goto :eof


:: ════════════════════════════════════════════════════════════
:create_dirs
echo.
echo  [2/7] Creando estructura de carpetas...
for %%d in (
    "%INSTALL_DIR%"
    "%INSTALL_DIR%\efirma"
    "%INSTALL_DIR%\contabilidad_sat"
    "%INSTALL_DIR%\logs"
    "%INSTALL_DIR%\src"
) do (
    if not exist %%d mkdir %%d >nul 2>&1
)
echo  [OK] Carpetas creadas en %INSTALL_DIR%
goto :eof


:: ════════════════════════════════════════════════════════════
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
    echo  [OK] Python !PYVER! encontrado (launcher py^).
    goto :eof
)

echo  [INFO] Python no encontrado. Descargando Python 3.12...
echo         Por favor espera, esto puede tardar unos minutos.
curl -L "%PYTHON_URL%" -o "%PYTHON_INSTALLER%" --progress-bar
if %errorlevel% neq 0 (
    echo  [ERROR] No se pudo descargar Python.
    echo          Descargalo manualmente desde: https://python.org
    pause & exit /b 1
)
echo  [INFO] Instalando Python 3.12...
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
if %errorlevel% neq 0 (
    echo  [ERROR] Fallo la instalacion de Python.
    pause & exit /b 1
)
del "%PYTHON_INSTALLER%" >nul 2>&1
set "PYTHON_CMD=python"
echo  [OK] Python 3.12 instalado.

:: Refrescar variables de entorno sin cerrar la ventana
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>nul') do set "PATH=%%b;%PATH%"
goto :eof


:: ════════════════════════════════════════════════════════════
:download_scripts
echo.
echo  [4/7] Descargando archivos desde GitHub...
echo         Repositorio: %REPO_URL%
echo.

set "DOWNLOAD_OK=1"

call :download_file "%REPO_RAW%/%FILE_MOTOR%"   "%INSTALL_DIR%\src\descarga_cfdi_sat.py"   "Motor principal"
call :download_file "%REPO_RAW%/%FILE_GUI%"     "%INSTALL_DIR%\src\contasat_gui.html"       "Interfaz grafica"
call :download_file "%REPO_RAW%/%FILE_DEPS%"    "%INSTALL_DIR%\src\instalar_dependencias.py" "Instalador de deps"

if "!DOWNLOAD_OK!"=="0" (
    echo.
    echo  [ERROR] Algunos archivos no se pudieron descargar.
    echo          Revisa tu conexion o el estado del repositorio.
    pause & exit /b 1
)
echo  [OK] Todos los archivos descargados.
goto :eof

:download_file
set "URL=%~1"
set "DEST=%~2"
set "LABEL=%~3"
echo         Descargando %LABEL%...
curl -s -L "%URL%" -o "%DEST%"
if %errorlevel% neq 0 (
    echo         [ERROR] No se pudo descargar: %LABEL%
    set "DOWNLOAD_OK=0"
) else (
    :: Verificar que el archivo no este vacio (404 devuelve HTML)
    for %%s in ("%DEST%") do if %%~zs LSS 100 (
        echo         [ERROR] Archivo invalido (posible 404^): %LABEL%
        set "DOWNLOAD_OK=0"
    ) else (
        echo         [OK] %LABEL%
    )
)
goto :eof


:: ════════════════════════════════════════════════════════════
:install_dependencies
echo.
echo  [5/7] Instalando dependencias Python...
%PYTHON_CMD% "%INSTALL_DIR%\src\instalar_dependencias.py" >> "%LOG_FILE%" 2>&1

:: Instalar paquetes criticos directamente como respaldo
for %%p in (cfdiclient openpyxl lxml schedule) do (
    %PYTHON_CMD% -m pip install %%p --quiet --upgrade >> "%LOG_FILE%" 2>&1
    if !errorlevel! equ 0 (
        echo         [OK] %%p
    ) else (
        echo         [WARN] %%p — ver log: %LOG_FILE%
    )
)
echo  [OK] Dependencias instaladas.

:: Crear config.ini con valores por defecto
if not exist "%INSTALL_DIR%\config.ini" (
    (
        echo # ContaSAT — Configuracion
        echo # Edita este archivo con tu RFC y datos de e.firma
        echo.
        echo RFC=XAXX010101000
        echo FIEL_CER=efirma\tu_archivo.cer
        echo FIEL_KEY=efirma\tu_archivo.key
        echo FIEL_PASSWORD=
        echo NOTIF_EMAIL=
        echo DIA_AUTO=1
        echo HORA_AUTO=08:00
        echo CARPETA_DESTINO=contabilidad_sat
    ) > "%INSTALL_DIR%\config.ini"
    echo  [OK] Archivo config.ini creado.
)
goto :eof


:: ════════════════════════════════════════════════════════════
:register_task
echo.
echo  [6/7] Registrando tarea automatica mensual...
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

schtasks /Create ^
  /TN "%TASK_NAME%" ^
  /TR "\"%PYTHON_CMD%\" \"%INSTALL_DIR%\src\descarga_cfdi_sat.py\" --auto" ^
  /SC MONTHLY /D 1 /ST 08:00 ^
  /RU "%USERNAME%" /RL HIGHEST /F >nul 2>&1

if %errorlevel% equ 0 (
    echo  [OK] Tarea programada: dia 1 de cada mes a las 08:00
) else (
    echo  [WARN] No se pudo registrar la tarea automatica.
    echo         Configurala manualmente desde el Administrador de tareas.
)
goto :eof


:: ════════════════════════════════════════════════════════════
:create_shortcut
echo.
echo  [7/7] Creando acceso directo en el Escritorio...
set "SHORTCUT=%USERPROFILE%\Desktop\ContaSAT.lnk"
set "PS1=%TEMP%\cs_shortcut.ps1"

:: Acceso directo para abrir la GUI en el navegador
(
    echo $s = (New-Object -COM WScript.Shell^).CreateShortcut('%SHORTCUT%'^)
    echo $s.TargetPath = '%INSTALL_DIR%\src\contasat_gui.html'
    echo $s.Description = 'ContaSAT - Gestion de CFDIs del SAT'
    echo $s.WorkingDirectory = '%INSTALL_DIR%'
    echo $s.Save(^)
) > "%PS1%"
powershell -ExecutionPolicy Bypass -File "%PS1%" >nul 2>&1
del "%PS1%" >nul 2>&1

if exist "%SHORTCUT%" (
    echo  [OK] Acceso directo creado en el Escritorio.
) else (
    echo  [INFO] No se pudo crear el acceso directo automaticamente.
)
goto :eof


:: ════════════════════════════════════════════════════════════
:final_message
echo.
echo  ╔══════════════════════════════════════════════════════╗
echo  ║            INSTALACION COMPLETADA                   ║
echo  ╚══════════════════════════════════════════════════════╝
echo.
echo  Carpeta de instalacion:
echo    %INSTALL_DIR%
echo.
echo  PROXIMOS PASOS:
echo.
echo  1. Copia tu e.firma (.cer y .key) a:
echo       %INSTALL_DIR%\efirma\
echo.
echo  2. Edita tu RFC en:
echo       %INSTALL_DIR%\config.ini
echo.
echo  3. Abre la interfaz grafica (acceso directo en Escritorio)
echo       o abre directamente:
echo       %INSTALL_DIR%\src\contasat_gui.html
echo.
echo  4. La descarga automatica mensual esta programada para el
echo       dia 1 de cada mes a las 08:00 hrs.
echo.
echo  Repositorio y actualizaciones:
echo    %REPO_URL%
echo.
echo  Log de instalacion: %LOG_FILE%
echo  ─────────────────────────────────────────────────────
echo.
pause
goto :eof
