# Why need a VCE app?

Simulador de exámenes de certificación con Streamlit: banco de preguntas con imágenes, extracción OCR con Google Gemini, modo práctica y modo examen con temporizador.

---

## Instalación en Windows

1. **Instala Python 3.10 o superior** desde [python.org/downloads](https://www.python.org/downloads/).
   > ⚠️ Durante la instalación, marca la casilla **"Add python.exe to PATH"**.
2. **Descarga el proyecto**: en GitHub, botón **Code → Download ZIP**, y descomprímelo en la carpeta que quieras.
3. **Haz doble clic en `instalar.bat`** — solo la primera vez. Instala las dependencias en una carpeta `.venv` (unos minutos).
4. **Haz doble clic en `iniciar.bat`** — la aplicación se abre sola en tu navegador en <http://localhost:8502>.

Para usar la app a partir de ahora, solo necesitas el paso 4. Para actualizar a una versión más nueva: descarga el ZIP de nuevo, pisa la carpeta (tus datos NO se pierden) y ejecuta `instalar.bat`.

## Instalación en Linux/macOS

```bash
cd MyVCE_Funcional
pip install -r requirements.txt
python -m streamlit run app.py --server.port 8502
```

---

## Primer uso

Al abrir la app por primera vez aparece un asistente:

- **Pega tu API Key de Google Gemini** ([aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)) para habilitar el OCR, **o**
- pulsa **"Continuar sin OCR"** — la app es 100 % funcional sin ella; el OCR es opcional.

---

## Características

| Pestaña | Qué hace |
|---|---|
| ✍️ Ingesta Manual | Añadir preguntas con imágenes, hasta 6 opciones, respuesta múltiple y tags |
| 📸 Extracción OCR | Extraer preguntas desde capturas de pantalla con Gemini, revisar y guardar |
| 📊 Ver Preguntas | Buscar, filtrar por tag, editar y eliminar; importar/exportar en ZIP |
| 🎮 Simulador | Modo Práctica (sin tiempo, feedback inmediato) y Modo Examen (temporizador, evaluación final). Puedes terminar cuando quieras, ver la opción correcta y navegar con el teclado (`Enter`/`→` avanzan, `←` vuelve) |
| 🔁 Errores Reiterados | Preguntas falladas en varios exámenes y test de práctica con ellas |

---

## Dónde se guardan tus datos

| Carpeta | Contenido |
|---|---|
| `%APPDATA%\WhyNeedAVCEApp` (Windows) · `~/.local/share/WhyNeedAVCEApp` (Linux/macOS) | Banco de preguntas, historial de exámenes, imágenes |
| `%APPDATA%` (Windows) · `~/.config/WhyNeedAVCEApp` (Linux/macOS) | API Key cifrada (`gemini_key.enc`) |

Tus datos **no** están dentro de la carpeta del proyecto: puedes borrarla o actualizarla sin perderlos. Para desinstalar por completo, borra la carpeta del proyecto y las carpetas de datos de la tabla.

---

## Estructura del proyecto

```
MyVCE_Funcional/
├── app.py                 # Aplicación principal (Streamlit)
├── instalar.bat           # Instalación en Windows (una sola vez)
├── iniciar.bat            # Arranque en Windows
├── requirements.txt       # Dependencias de Python
├── src/                   # Módulos auxiliares (datos, examen, OCR, backup...)
├── tests/                 # Suite de tests (scripts Python ejecutables)
└── .streamlit/            # Configuración de Streamlit
```

---

## Solución de problemas

- **`'python' no se reconoce`** → reinstala Python marcando la casilla *"Add python.exe to PATH"* (o desinstala primero la versión de la Microsoft Store si Windows la abrió al escribir `python`).
- **El puerto 8502 está ocupado** → Streamlit avisa en la terminal y usa otro puerto automáticamente; o edita `--server.port` en `iniciar.bat`.
- **El OCR dice "Modelo no disponible"** → en la pestaña OCR, dentro de **⚙️ Modelo**, elige otro de la lista. La disponibilidad depende de tu cuenta de Google (retira modelos antiguos para usuarios nuevos).
- **La app no arranca tras instalar** → vuelve a ejecutar `instalar.bat`; si persiste, borra la carpeta `.venv` y repite la instalación.

---

## Desarrollo

```bash
python -m streamlit run app.py --server.port 8502   # servidor de desarrollo
```

Los tests son scripts Python directos (sin pytest):

```bash
for f in tests/*.py; do python "$f"; done           # Linux/macOS
for %f in (tests\*.py) do python "%f"               # Windows (cmd)
```
