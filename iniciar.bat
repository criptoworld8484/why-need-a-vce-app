@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================
echo   MyVCE - Simulador de Certificacion
echo ============================================
echo.

REM --- Primera ejecucion: instalar antes de arrancar ---
if not exist ".venv\Scripts\python.exe" (
    echo Primera ejecucion: instalando dependencias...
    echo.
    call "%~dp0instalar.bat" --auto
    echo.
)

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] El entorno no esta listo.
    echo Ejecuta instalar.bat y revisa los mensajes de error.
    echo.
    pause
    exit /b 1
)

echo Iniciando la aplicacion... se abrira en tu navegador.
echo Para detenerla, cierra esta ventana o pulsa Ctrl+C.
echo.
".venv\Scripts\python.exe" -m streamlit run "%~dp0app.py" --server.port 8502 --server.headless false

echo.
echo Aplicacion detenida.
pause
exit /b 0
