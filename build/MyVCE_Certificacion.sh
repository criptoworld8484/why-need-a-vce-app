#!/bin/bash

# MyVCE Certificacion - Launcher Script

# Obtener el directorio donde esta este script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PATH="$SCRIPT_DIR/_internal/app.py"
PROJECT_DIR="$SCRIPT_DIR"
VENV_DIR="$PROJECT_DIR/venv"

echo "============================================"
echo "  MyVCE Certificacion"
echo "============================================"
echo ""

# Verificar que la app existe
if [ ! -f "$APP_PATH" ]; then
    echo "[ERROR] No se encontro la aplicacion"
    echo "Asegurate de ejecutar este script desde la carpeta MyVCE_Certificacion"
    exit 1
fi

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 no esta instalado"
    echo "Instala Python 3.10 o superior"
    exit 1
fi

echo "[OK] Python encontrado"

# Crear o usar entorno virtual
if [ ! -d "$VENV_DIR/bin/python" ]; then
    echo ""
    echo "[1/3] Creando entorno virtual..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "[ERROR] No se pudo crear el entorno virtual"
        exit 1
    fi
    echo "[OK] Entorno virtual creado"
else
    echo ""
    echo "[OK] Usando entorno virtual existente"
fi

# Instalar dependencias
echo ""
echo "[2/3] Instalando dependencias..."
$VENV_DIR/bin/pip install --upgrade pip -q
$VENV_DIR/bin/pip install streamlit numpy Pillow opencv-python cryptography -q

if [ $? -ne 0 ]; then
    echo "[ERROR] Fallo la instalacion de dependencias"
    exit 1
fi

echo "[OK] Dependencias instaladas"

# Ejecutar la aplicacion
echo ""
echo "[3/3] Iniciando aplicacion..."
echo ""
echo "Presiona Ctrl+C para salir"
echo "============================================"
echo ""

cd "$SCRIPT_DIR"
exec "$VENV_DIR/bin/python" -m streamlit run "$APP_PATH" \
    --server.headless=true \
    --browser.serverAddress=localhost
