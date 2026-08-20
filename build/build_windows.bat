@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ========================================
echo   MyVCE - Script de Preparacion
echo ========================================
echo.

REM Obtener el directorio donde esta este script
set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

REM Cambiar al directorio del proyecto
cd /d "%PROJECT_DIR%"
if errorlevel 1 (
    echo [ERROR] No se pudo acceder al directorio del proyecto
    pause
    exit /b 1
)

REM Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no esta instalado.
    echo Descargalo de: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Preparando archivos...
echo.

REM Crear estructura de carpetas
if not exist "dist\MyVCE_Certificacion\_internal\imagenes_preguntas" (
    mkdir dist\MyVCE_Certificacion\_internal\imagenes_preguntas 2>nul
)
if not exist "dist\MyVCE_Certificacion\_internal\src" (
    mkdir dist\MyVCE_Certificacion\_internal\src 2>nul
)

REM Copiar archivos necesarios
echo     Copiando app.py...
copy /Y app.py dist\MyVCE_Certificacion\_internal\ >nul 2>&1

echo     Copiando preguntas.json...
copy /Y preguntas.json dist\MyVCE_Certificacion\_internal\ >nul 2>&1

echo     Copiando src/...
if exist "src" (
    for %%f in (src\*.py) do (
        copy /Y "%%f" dist\MyVCE_Certificacion\_internal\src\ >nul 2>&1
    )
)

echo     Copiando imagenes...
if exist "imagenes_preguntas" (
    for %%f in (imagenes_preguntas\*) do (
        copy /Y "%%f" dist\MyVCE_Certificacion\_internal\imagenes_preguntas\ >nul 2>&1
    )
)

echo     Copiando scripts de ejecucion...
copy /Y build\MyVCE_Certificacion.bat dist\MyVCE_Certificacion\ >nul 2>&1
copy /Y build\MyVCE_Certificacion.sh dist\MyVCE_Certificacion\ >nul 2>&1
copy /Y README.md dist\MyVCE_Certificacion\LEEME.md >nul 2>&1

echo     Copiando entorno virtual...
if exist "venv" (
    if not exist "dist\MyVCE_Certificacion\venv" mkdir dist\MyVCE_Certificacion\venv
    xcopy /E /Q /Y "venv\*" "dist\MyVCE_Certificacion\venv\" >nul 2>&1
)

REM Eliminar ejecutable de PyInstaller si existe
if exist "dist\MyVCE_Certificacion\MyVCE_Certificacion" (
    del /Q "dist\MyVCE_Certificacion\MyVCE_Certificacion" >nul 2>&1
    del /Q "dist\MyVCE_Certificacion\MyVCE_Certificacion.exe" >nul 2>&1
)

echo.
echo [2/4] Creando/entorno virtual con dependencias...
echo.

REM Crear o actualizar entorno virtual
if not exist "venv" (
    python -m venv venv
)

REM Instalar dependencias en el venv
call venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install streamlit numpy Pillow opencv-python cryptography -q
deactivate >nul 2>&1

echo.
echo [3/4] Archivos en dist\MyVCE_Certificacion\
dir /B dist\MyVCE_Certificacion\ 2>nul

echo.
echo [4/4] Verificando archivos...
set "ERRORES=0"

if not exist "dist\MyVCE_Certificacion\_internal\app.py" (
    echo     [ERROR] Falta app.py
    set "ERRORES=1"
)

if not exist "dist\MyVCE_Certificacion\_internal\preguntas.json" (
    echo     [ERROR] Falta preguntas.json
    set "ERRORES=1"
)

if not exist "dist\MyVCE_Certificacion\_internal\src\paths.py" (
    echo     [ERROR] Falta src/paths.py
    set "ERRORES=1"
)

if not exist "dist\MyVCE_Certificacion\MyVCE_Certificacion.bat" (
    echo     [ERROR] Falta MyVCE_Certificacion.bat
    set "ERRORES=1"
)

if not exist "dist\MyVCE_Certificacion\venv\Scripts\python.exe" (
    echo     [ERROR] Falta entorno virtual en dist
    set "ERRORES=1"
)

if "%ERRORES%"=="1" (
    echo.
    echo [ERROR] Hubo problemas al preparar los archivos.
    pause
    exit /b 1
)

echo     [OK] Todos los archivos verificados.

echo.
echo ========================================
echo   PREPARACION COMPLETADA
echo ========================================
echo.
echo Ubicacion:
echo   dist\MyVCE_Certificacion\
echo.
echo Para ejecutar:
echo   cd dist\MyVCE_Certificacion
echo   MyVCE_Certificacion.bat
echo.
echo El launcher automaticamente:
echo   - Creara el entorno virtual si es necesario
echo   - Instalara Streamlit y dependencias
echo   - Ejecutara la aplicacion
echo.
pause
