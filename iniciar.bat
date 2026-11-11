@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================
echo   MyVCE - Simulador de Certificacion
echo ============================================
echo.

REM --- Instalar si es la primera vez o si una instalacion anterior quedo
REM     incompleta (venv creado pero dependencias sin terminar) ---
set "INSTALAR=0"
if not exist ".venv\Scripts\python.exe" set "INSTALAR=1"
if not exist ".venv\.instalacion_ok" set "INSTALAR=1"
if "%INSTALAR%"=="1" (
    echo Primera ejecucion o instalacion incompleta: instalando dependencias...
    echo.
    call "%~dp0instalar.bat" --auto
    if errorlevel 1 (
        echo [ERROR] La instalacion fallo. Revisa los mensajes anteriores.
        echo.
        pause
        exit /b 1
    )
    echo.
)

if not exist ".venv\.instalacion_ok" (
    echo [ERROR] El entorno no esta completo.
    echo Ejecuta instalar.bat y revisa los mensajes de error.
    echo.
    pause
    exit /b 1
)

echo Iniciando la aplicacion... se abrira en tu navegador.
echo Para detenerla, cierra esta ventana o pulsa Ctrl+C.
echo.
".venv\Scripts\python.exe" -m streamlit run "%~dp0app.py" --server.port 8502 --server.headless false
set "CODIGO_SALIDA=%ERRORLEVEL%"

echo.
if "%CODIGO_SALIDA%"=="0" (
    echo Aplicacion detenida.
) else (
    echo [ERROR] La aplicacion termino con codigo %CODIGO_SALIDA%.
)
pause
exit /b %CODIGO_SALIDA%
