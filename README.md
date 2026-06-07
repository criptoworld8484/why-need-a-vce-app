# Why need a VCE app?

Simulador de exámenes de certificación con Streamlit.

---

## Ejecución Rápida

### Linux/macOS

```bash
cd MyVCE_Funcional
pip install -r requirements.txt
python -m streamlit run app.py --server.port 8502
```

### Windows

```cmd
cd MyVCE_Funcional
pip install -r requirements.txt
python -m streamlit run app.py --server.port 8502
```

La aplicación se abrirá en: http://localhost:8502

---

## Requisitos

- **Python 3.10+**
- **Streamlit 1.54+** (para timer optimizado)
- **Google Gemini API Key** (opcional, para OCR)

### Dependencias

```
streamlit>=1.54.0
streamlit-autorefresh>=1.0.0
google-genai>=1.0.0
Pillow>=10.0.0
opencv-python>=4.8.0
numpy>=1.24.0
cryptography>=41.0.0
```

**Nota:** Se requiere Streamlit 1.54+ para mejor rendimiento del timer (soporte nativo de fragments).

---

## Características

### 1. Ingesta Manual
- Añadir preguntas directamente desde el formulario
- Soporte para imágenes adjuntas
- Multiple choice con hasta 6 opciones
- Soporte para preguntas de respuesta múltiple
- Tags para agrupar preguntas por vendor/categoría

### 2. Extracción OCR con Gemini
- Extraer preguntas desde imágenes usando Google Gemini
- Procesamiento automático de imágenes
- Validación de preguntas extraídas
- Asignación de tags al importar

### 3. Base de Datos de Preguntas
- Ver todas las preguntas disponibles
- Filtrar por tag y texto
- Editar tags inline y eliminar preguntas
- Importar/Exportar en formato ZIP (incluye imágenes)

### 4. Simulador de Examen
- **Modo Práctica**: Sin límite de tiempo, feedback inmediato
- **Modo Examen**: Temporizador configurable, evaluación final
- Filtrado por tags y rango ordinal
- Orden aleatorio por defecto
- Navegación entre preguntas
- Seguimiento de progreso
- Timer en tiempo real con cuenta regresiva

---

## Configurar API Key de Gemini (Opcional)

Para usar la función de OCR:

1. Ir a: https://makersuite.google.com/app/apikey
2. Crear una API Key de Google Gemini
3. En la app, ingresar la clave cuando lo solicite

---

## Estructura del Proyecto

```
MyVCE_Funcional/
├── app.py                    # Código fuente principal
├── requirements.txt          # Dependencias de Python
├── README.md                 # Esta documentación
├── src/                      # Módulos auxiliares
│   ├── paths.py              # Gestión de rutas
│   ├── api_key_manager.py    # Almacenamiento seguro de API keys
│   └── __init__.py
└── build/                    # Scripts de compilación
```

---

## Solución de Problemas

### "Puerto en uso"
- La app usará automáticamente otro puerto disponible
- Especificar puerto: `python -m streamlit run app.py --server.port 8503`

### Error al cargar imágenes
- Las imágenes deben estar en formato PNG, JPG o JPEG

### Timer no actualiza
- El timer usa `streamlit-autorefresh` para actualizarse cada segundo
- Verificar que el paquete está instalado: `pip install streamlit-autorefresh`

---

## Desarrollo

### Ejecutar en modo desarrollo
```bash
python -m streamlit run app.py --server.port 8502 --server.reload true
```

### Compilar para distribución

**Windows:**
```batch
build\build_windows.bat
```

**Linux:**
```bash
build/build_linux.sh
```
