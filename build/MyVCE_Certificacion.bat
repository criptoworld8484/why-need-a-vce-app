@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ============================================
echo   MyVCE Certificacion
echo ============================================
echo.

REM Obtener el directorio donde esta este script
set "SCRIPT_DIR=%~dp0"
set "APP_PATH=%SCRIPT_DIR%_internal\app.py"
set "VENV_DIR=%SCRIPT_DIR%venv"

REM Verificar que la app existe
if not exist "%APP_PATH%" (
    echo [ERROR] No se encontro la aplicacion.
    echo.
    echo Asegurate de ejecutar este script desde la carpeta MyVCE_Certificacion
    pause
    exit /b 1
)

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado en el sistema.
    echo.
    echo Por favor, instala Python 3.10 o superior:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [OK] Python encontrado
echo.

REM Crear o usar entorno virtual
if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [1/3] Creando entorno virtual...
    python -m venv "%VENV_DIR%"
    
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual
        pause
        exit /b 1
    )
    echo [OK] Entorno virtual creado
    echo.
) else (
    echo [OK] Usando entorno virtual existente
    echo.
)

REM Instalar dependencias
echo [2/3] Instalando dependencias...
echo.

REM Instalar streamlit y dependencias
"%VENV_DIR%\Scripts\pip.exe" install --upgrade pip -q
"%VENV_DIR%\Scripts\pip.exe" install streamlit numpy Pillow opencv-python cryptography -q

if errorlevel 1 (
    echo.
    echo [ERROR] Fallo la instalacion de dependencias.
    echo.
    pause
    exit /b 1
)

echo [OK] Dependencias instaladas
echo.

REM Ejecutar la aplicacion
echo [3/3] Iniciando aplicacion...
echo.
echo Presiona Ctrl+C para salir
echo ============================================
echo.

cd /d "%SCRIPT_DIR%"
"%VENV_DIR%\Scripts\python.exe" -m streamlit run "%APP_PATH%" --server.headless true --browser.serverAddress localhost

endlocal
