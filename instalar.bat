@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

REM --auto (lo pasa iniciar.bat): termina sin pausas para poder invocarlo
REM desde otro script. Cualquier otro argumento no cambia el comportamiento.
set "AUTO=0"
if /I "%~1"=="--auto" set "AUTO=1"

echo ============================================
echo   MyVCE - Instalacion
echo ============================================
echo.

REM --- Buscar Python: primero el launcher py, luego python en PATH ---
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY (
    python --version >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo [ERROR] No se encontro Python.
    echo.
    echo Pasos para solucionarlo:
    echo   1. Descarga Python 3.10 o superior:
    echo      https://www.python.org/downloads/
    echo   2. Durante la instalacion, MARCA la casilla
    echo      "Add python.exe to PATH"
    echo   3. Vuelve a ejecutar instalar.bat
    echo.
    if "%AUTO%"=="0" pause
    exit /b 1
)

echo [1/3] Python encontrado. Preparando entorno virtual...
if not exist ".venv\Scripts\python.exe" (
    %PY% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual .venv
        if "%AUTO%"=="0" pause
        exit /b 1
    )
)

REM El marcador .instalacion_ok solo existe si las dependencias terminaron de
REM instalarse: detecta venvs a medias (pip interrumpido, red caida, etc.)
del /Q ".venv\.instalacion_ok" 2>nul

echo [2/3] Instalando dependencias (puede tardar unos minutos)...
".venv\Scripts\python.exe" -m pip install --upgrade pip -q
if errorlevel 1 (
    echo [ERROR] Fallo la actualizacion de pip.
    echo Revisa tu conexion a internet y vuelve a ejecutar instalar.bat
    if "%AUTO%"=="0" pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de dependencias.
    echo Revisa tu conexion a internet y vuelve a ejecutar instalar.bat
    if "%AUTO%"=="0" pause
    exit /b 1
)

type nul > ".venv\.instalacion_ok"

echo.
echo [3/3] Instalacion completada.
echo.
echo Para usar la aplicacion haz doble clic en iniciar.bat
echo.
if "%AUTO%"=="0" pause
exit /b 0
