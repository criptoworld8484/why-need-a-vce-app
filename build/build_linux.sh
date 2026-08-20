#!/bin/bash

echo "========================================"
echo "  MyVCE - Script de Preparacion Linux"
echo "========================================"
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 no esta instalado."
    echo "Instalalo con: sudo apt install python3 python3-venv"
    exit 1
fi

# Obtener directorio del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

echo "[1/4] Preparando archivos..."
echo ""

# Crear estructura de carpetas
mkdir -p dist/MyVCE_Certificacion/_internal/imagenes_preguntas
mkdir -p dist/MyVCE_Certificacion/_internal/src

# Copiar archivos necesarios
echo "    Copiando app.py..."
cp -f app.py dist/MyVCE_Certificacion/_internal/

echo "    Copiando preguntas.json..."
cp -f preguntas.json dist/MyVCE_Certificacion/_internal/

echo "    Copiando src/..."
if [ -d "src" ]; then
    cp -f src/*.py dist/MyVCE_Certificacion/_internal/src/
fi

echo "    Copiando imagenes..."
if [ -d "imagenes_preguntas" ]; then
    cp -r imagenes_preguntas/* dist/MyVCE_Certificacion/_internal/imagenes_preguntas/ 2>/dev/null || true
fi

echo "    Copiando scripts de ejecucion..."
cp -f build/MyVCE_Certificacion.sh dist/MyVCE_Certificacion/
chmod +x dist/MyVCE_Certificacion/MyVCE_Certificacion.sh
cp -f build/MyVCE_Certificacion.bat dist/MyVCE_Certificacion/ 2>/dev/null || true
cp -f README.md dist/MyVCE_Certificacion/LEEME.md 2>/dev/null || true

echo "    Copiando entorno virtual..."
if [ -d "venv" ]; then
    mkdir -p dist/MyVCE_Certificacion/venv
    cp -r venv/* dist/MyVCE_Certificacion/venv/ 2>/dev/null || true
fi

# Eliminar ejecutable de PyInstaller si existe
rm -f dist/MyVCE_Certificacion/MyVCE_Certificacion 2>/dev/null
rm -f dist/MyVCE_Certificacion/MyVCE_Certificacion.exe 2>/dev/null

echo ""
echo "[2/4] Creando entorno virtual con dependencias..."
echo ""

# Crear o actualizar entorno virtual
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Instalar dependencias en el venv
source venv/bin/activate
pip install --upgrade pip -q
pip install streamlit numpy Pillow opencv-python cryptography -q
deactivate

echo ""
echo "[3/4] Archivos en dist/MyVCE_Certificacion/"
ls -1 dist/MyVCE_Certificacion/ 2>/dev/null || echo "    (ninguno)"

echo ""
echo "[4/4] Verificando archivos..."
ERRORS=0

if [ ! -f "dist/MyVCE_Certificacion/_internal/app.py" ]; then
    echo "    [ERROR] Falta app.py"
    ERRORS=1
fi

if [ ! -f "dist/MyVCE_Certificacion/_internal/preguntas.json" ]; then
    echo "    [ERROR] Falta preguntas.json"
    ERRORS=1
fi

if [ ! -f "dist/MyVCE_Certificacion/_internal/src/paths.py" ]; then
    echo "    [ERROR] Falta src/paths.py"
    ERRORS=1
fi

if [ ! -f "dist/MyVCE_Certificacion/MyVCE_Certificacion.sh" ]; then
    echo "    [ERROR] Falta MyVCE_Certificacion.sh"
    ERRORS=1
fi

if [ ! -d "dist/MyVCE_Certificacion/venv/lib/python3."*"/site-packages/streamlit" ]; then
    echo "    [ERROR] Falta streamlit en el entorno virtual"
    ERRORS=1
fi

if [ $ERRORS -eq 1 ]; then
    echo ""
    echo "[ERROR] Hubo problemas al preparar los archivos."
    exit 1
fi

echo "    [OK] Todos los archivos verificados."

echo ""
echo "========================================"
echo "  PREPARACION COMPLETADA"
echo "========================================"
echo ""
echo "Ubicacion:"
echo "  dist/MyVCE_Certificacion/"
echo ""
echo "Para ejecutar:"
echo "  cd dist/MyVCE_Certificacion"
echo "  ./MyVCE_Certificacion.sh"
echo ""
echo "El launcher automaticamente:"
echo "  - Creara el entorno virtual si es necesario"
echo "  - Instalara Streamlit y dependencias"
echo "  - Ejecutara la aplicacion"
echo ""
