import streamlit as st
from PIL import Image
import json
import os
import time
import random
import copy
import html
import re
import shutil

# Check for st.fragment support (Streamlit 1.54+)
ST_FRAGMENT_AVAILABLE = hasattr(st, 'fragment')

from src.paths import get_app_dir, get_data_dir
from src.api_key_manager import save_api_key, load_api_key, has_api_key
from src.seleccion import (SIN_TAG, seleccionar_pool, deduplicar, detectar_conflictos,
                           coincide_tag)
from src.preguntas import (LETRAS_OPCIONES, prefijo_opcion,
                           letra_por_posicion, normalizar_opciones_ocr,
                           validar_preguntas_importadas, reasignar_ids,
                           purgar_imagenes_huerfanas)
from src.examen import calcular_resultado
from src.historial import (cargar_historial, clave_pregunta, guardar_historial,
                           historial_vacio, registrar_examen,
                           resumen_reiteradas)
from src.backup import export_questions_to_zip, import_questions_from_zip

# ✅ CONFIGURACIÓN PROTEGIDA DE OPENCV
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "0"
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MPLBACKEND"] = "Agg"

try:
    import cv2
    cv2.setNumThreads(1)
    OPENCV_AVAILABLE = True
except Exception:
    OPENCV_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except Exception:
    GENAI_AVAILABLE = False

try:
    from streamlit_autorefresh import st_autorefresh
    STREAMLIT_AUTOREFRESH_AVAILABLE = True
except ImportError:
    STREAMLIT_AUTOREFRESH_AVAILABLE = False

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión de Preguntas", layout="wide", page_icon="📚")

# ✅ CSS ULTRA MEJORADO PARA CHECKBOXES Y ANIMACIONES
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@600;700;800&display=swap');

    :root {
        --primary: #1e293b;
        --primary-light: #334155;
        --accent: #10b981;
        --accent-hover: #059669;
        --selection-bg: #fef08a;
        --selection-border: #facc15;
        --selection-text: #1e293b;
        --error: #ef4444;
        --error-hover: #dc2626;
        --bg-main: #f8fafc;
        --bg-card: #ffffff;
        --text-main: #1e293b;
        --text-body: #334155;
        --text-muted: #64748b;
        --border-color: #e2e8f0;
        --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
        --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        --radius-md: 12px;
        --radius-lg: 16px;
        /* Override Streamlit dark theme variables */
        --background-color: #f8fafc;
        --secondary-background-color: #ffffff;
        --text-color: #334155;
    }

    /* Global Styles - force light mode even if OS/browser is dark */
    @media (prefers-color-scheme: dark) {
        html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"],
        [data-testid="stMain"], .block-container, section.main {
            background-color: var(--bg-main) !important;
            color: var(--text-body) !important;
        }
        html {
            background-color: var(--bg-main) !important;
        }
    }

    .stApp {
        background-color: var(--bg-main) !important;
        font-family: 'Inter', sans-serif !important;
        color: var(--text-body) !important;
    }

    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif !important;
        color: var(--primary) !important;
        font-weight: 700 !important;
    }

    /* Markdown containers */
    div[data-testid="stMarkdownContainer"] p {
        color: var(--text-body) !important;
    }

    /* Custom Noise Background */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        opacity: 0.03;
        z-index: -1;
        pointer-events: none;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
    }

    /* Contenido del expander - fondo blanco */
    .streamlit-expanderContent {
        background: white !important;
        color: var(--text-body) !important;
    }

    /* ===== EXPANDER SUMMARY (el elemento clickeable) ===== */
    /* Summary - elemento nativo del expander */
    details.streamlit-expander summary,
    .streamlit-expander summary,
    [data-testid="stExpander"] summary {
        background-color: #fef08a !important;
        background: #fef08a !important;
        background-image: none !important;
        color: #1e293b !important;
        list-style: none !important;
        -webkit-appearance: none !important;
        appearance: none !important;
        cursor: pointer !important;
        transition: none !important;
        padding: 12px 16px !important;
        border-radius: var(--radius-md) !important;
        border: 1px solid #facc15 !important;
    }

    /* Quitar el triángulo default del browser */
    details.streamlit-expander summary::-webkit-details-marker,
    .streamlit-expander summary::-webkit-details-marker {
        display: none !important;
    }

    details.streamlit-expander summary::marker,
    .streamlit-expander summary::marker {
        display: none !important;
    }

    /* Hover summary - mismo color, sin animación */
    details.streamlit-expander summary:hover,
    .streamlit-expander summary:hover,
    [data-testid="stExpander"] summary:hover {
        background-color: #fef08a !important;
        background: #fef08a !important;
        background-image: none !important;
        color: #1e293b !important;
        transition: none !important;
        transform: none !important;
    }

    /* Span dentro del summary - texto principal */
    details.streamlit-expander summary span,
    .streamlit-expander summary span {
        color: #1e293b !important;
        font-weight: 600 !important;
        font-family: 'Outfit', sans-serif !important;
    }

    /* Estilos para el header del expander cuando está expandido */
    .streamlit-expanderHeader {
        background: linear-gradient(135deg, var(--selection-bg) 0%, #fef9c3 100%) !important;
        background-color: #fef08a !important;
        color: var(--selection-text) !important;
        border: 1px solid var(--selection-border) !important;
    }

    .streamlit-expanderHeader:hover {
        background: linear-gradient(135deg, #facc15 0%, #fef08a 100%) !important;
        background-color: #facc15 !important;
    }

    /* Inputs dentro del expander */
    .streamlit-expanderContent input {
        background: white !important;
        color: var(--text-body) !important;
        border: 1px solid var(--border-color) !important;
    }

    /* Input de tag dentro del expander - ensure readable */
    .streamlit-expanderContent [data-testid="stTextInput"] input {
        background: white !important;
        color: var(--text-body) !important;
        border: 1px solid var(--border-color) !important;
    }

    .streamlit-expanderContent [data-testid="stTextInput"] label {
        color: var(--selection-text) !important;
    }

    /* Tags en alerts - contraste garantizado */
    div[data-testid="stAlert"] p strong {
        color: #1e40af !important;
    }

    /* Forzar colores en markdown containers dentro de expander */
    .streamlit-expanderContent [data-testid="stMarkdownContainer"] p code {
        background: #dbeafe !important;
        color: #1e40af !important;
        padding: 2px 8px !important;
        border-radius: 4px !important;
        border: 1px solid #3b82f6 !important;
    }

    /* Labels dentro del expander */
    .streamlit-expanderContent label {
        color: var(--selection-text) !important;
    }

    /* Section con emotion-cache - fondo claro */
    [data-testid="stForm"] {
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--radius-lg) !important;
        padding: 20px !important;
    }

    /* Form container */
    .stForm > div {
        background-color: var(--bg-card) !important;
        border-radius: var(--radius-md) !important;
        padding: 16px !important;
    }

    /* Arreglar desalineación - gap consistente */
    [data-testid="stHorizontalBlock"] {
        gap: 16px !important;
    }

    /* Columnas equitativas */
    [data-testid="stVerticalBlock"] > [data-testid="stHorizontalBlock"] {
        align-items: stretch !important;
    }

    /* Fix padding en secciones de tabs */
    div[data-testid="stTabContent"] {
        padding-top: 20px !important;
    }

    /* Contenedor de form submit */
    .stFormSubmitButton {
        margin-top: 16px !important;
    }

    /* Section headers */
    [data-testid="stForm"] h3,
    [data-testid="stForm"] h2 {
        color: var(--primary) !important;
        margin-bottom: 16px !important;
    }

    /* Asegurar que todos los contenedores internos usen fondo blanco */
    div[class*="st-emotion-cache"] {
        background-color: transparent !important;
    }

    /* Contenedor principal de secciones */
    [data-testid="stMainBlockContainer"] {
        background-color: var(--bg-main) !important;
        padding: 20px !important;
    }

    /* Sidebar container */
    [data-testid="stSidebar"] {
        background-color: var(--bg-card) !important;
    }

    /* ===== BOTONES - TODOS AMARILLOS, SIN CAMBIOS EN HOVER ===== */
    /* Selectores de alta especificidad para override completo */

    button,
    .stButton > button,
    button[data-testid="stBaseButton"],
    button[data-testid="stBaseButton-secondary"],
    button[class*="stBaseButton"],
    .streamlit-expanderHeader button,
    .streamlit-expanderContent button,
    [data-testid="stForm"] button,
    .stForm button {
        background-color: #fef08a !important;
        background: #fef08a !important;
        background-image: none !important;
        color: #1e293b !important;
        border: 1px solid #facc15 !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
    }

    /* Hover igual al estado default - sin cambio de color */
    button:hover,
    .stButton > button:hover,
    button[data-testid="stBaseButton"]:hover,
    button[data-testid="stBaseButton-secondary"]:hover,
    button[class*="stBaseButton"]:hover,
    .streamlit-expanderHeader button:hover,
    .streamlit-expanderContent button:hover,
    [data-testid="stForm"] button:hover,
    .stForm button:hover {
        background-color: #fef08a !important;
        background: #fef08a !important;
        background-image: none !important;
        color: #1e293b !important;
        border: 1px solid #facc15 !important;
        transform: none !important;
        box-shadow: 0 4px 6px -1px rgba(250, 204, 21, 0.3) !important;
    }

    /* Active igual al default */
    button:active,
    .stButton > button:active,
    button[data-testid="stBaseButton"]:active,
    button[data-testid="stBaseButton-secondary"]:active {
        background-color: #fef08a !important;
        background: #fef08a !important;
        background-image: none !important;
        color: #1e293b !important;
        transform: none !important;
    }

    /* Focus state igual al default */
    button:focus,
    button:focus-visible,
    button[data-testid="stBaseButton"]:focus,
    button[data-testid="stBaseButton-secondary"]:focus {
        background-color: #fef08a !important;
        background: #fef08a !important;
        background-image: none !important;
        color: #1e293b !important;
        border: 1px solid #facc15 !important;
        box-shadow: 0 4px 6px -1px rgba(250, 204, 21, 0.3) !important;
    }

    /* ===== LABELS Y TEXTOS EN CHECKBOXES ===== */
    div[data-testid="stCheckbox"] label {
        color: var(--text-body) !important;
        font-size: 16px !important;
        font-weight: 500 !important;
    }

    div[data-testid="stCheckbox"] label span {
        color: var(--text-body) !important;
    }

    /* ===== RADIO BUTTONS LEGIBLES ===== */
    div[data-testid="stRadio"] label {
        color: var(--text-body) !important;
        font-weight: 500 !important;
    }

    div[data-testid="stRadio"] span {
        color: var(--text-body) !important;
    }

    /* ===== FORMULARIOS LEGIBLES ===== */
    .stTextInput label, .stTextArea label, .stSelectbox label, .stNumberInput label {
        color: var(--primary) !important;
        font-weight: 600 !important;
    }

    .stTextInput input, .stTextArea textarea {
        color: var(--text-body) !important;
        background: white !important;
    }

    /* ===== CHECKBOXES ESTILIZADOS ===== */
    div[data-testid="stCheckbox"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--radius-md) !important;
        padding: 12px 16px !important;
        margin: 8px 0 !important;
        box-shadow: var(--shadow-sm) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    div[data-testid="stCheckbox"]:hover {
        border-color: var(--accent) !important;
        box-shadow: var(--shadow-md) !important;
        transform: translateX(4px) !important;
    }

    div[data-testid="stCheckbox"] input[type="checkbox"] {
        accent-color: var(--accent) !important;
        width: 20px !important;
        height: 20px !important;
        cursor: pointer !important;
    }

    div[data-testid="stCheckbox"]:has(input:checked) {
        background: linear-gradient(135deg, var(--selection-bg) 0%, #fef9c3 100%) !important;
        border-color: var(--selection-border) !important;
        box-shadow: 0 4px 12px rgba(250, 204, 21, 0.2) !important;
    }

    /* Checkbox checked - texto legible */
    div[data-testid="stCheckbox"]:has(input:checked) label {
        color: var(--selection-text) !important;
        font-weight: 600 !important;
    }

    div[data-testid="stCheckbox"]:has(input:checked) label span {
        color: var(--selection-text) !important;
    }

    /* ===== BOTONES - extra ===== */
    .stButton > button {
        border-radius: var(--radius-md) !important;
        padding: 10px 24px !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 6px -1px rgba(250, 204, 21, 0.3) !important;
    }

    .stButton > button:hover {
        box-shadow: 0 10px 15px -3px rgba(250, 204, 21, 0.4) !important;
    }

    /* ===== NAVEGACIÓN (TABS) ===== */
    div[data-testid="stRadio"] > div {
        background: white !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--radius-lg) !important;
        padding: 6px !important;
        box-shadow: var(--shadow-sm) !important;
    }

    div[data-testid="stRadio"] > div > label {
        font-family: 'Inter', sans-serif !important;
        font-weight: 500 !important;
        font-size: 14px !important;
        border-radius: calc(var(--radius-lg) - 4px) !important;
        transition: all 0.2s ease !important;
        color: var(--text-muted) !important;
    }

    div[data-testid="stRadio"] > div > label:has(input:checked) {
        background: linear-gradient(135deg, var(--selection-bg) 0%, #fef9c3 100%) !important;
        color: var(--selection-text) !important;
        box-shadow: 0 4px 12px rgba(250, 204, 21, 0.2) !important;
        font-weight: 600 !important;
        border: 1px solid var(--selection-border) !important;
    }

    /* Hover state para pestañas - texto legible */
    div[data-testid="stRadio"] > div > label:hover {
        background: #fef9c3 !important;
        color: var(--text-body) !important;
    }

    /* ===== METRICS ===== */
    div[data-testid="stMetric"] {
        background: white !important;
        border: 1px solid var(--border-color) !important;
        border-radius: var(--radius-md) !important;
        padding: 20px !important;
        box-shadow: var(--shadow-sm) !important;
    }

    div[data-testid="stMetricValue"] {
        color: var(--primary) !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 800 !important;
    }

    /* ===== PROGRESS BAR ===== */
    .stProgress > div > div > div {
        background: var(--accent) !important;
    }

    /* ===== TOAST NOTIFICATIONS ===== */
    .stToast {
        background: var(--primary) !important;
        color: white !important;
    }

    /* ===== FILE UPLOADER ===== */
    .stFileUploader {
        background: white !important;
    }

    /* ===== CODE BLOCKS ===== */
    code {
        color: var(--text-body) !important;
    }

    /* ===== INFO/WARNING/ERROR MESSAGES ===== */
    .stInfo, .stWarning, .stError, .stSuccess {
        color: var(--text-body) !important;
    }
    
    /* ===== ALERTS LEGIBLES ===== */
    div[data-testid="stAlert"] {
        color: var(--text-body) !important;
    }
    
    /* ===== SPINNER ===== */
    .stSpinner {
        color: var(--primary) !important;
    }

    /* ===== TOOLTIP / HELP ===== */
    [role="tooltip"] {
        background: #ffffff !important;
        color: #1e293b !important;
    }

    [data-testid="stTooltipContent"] {
        background: #ffffff !important;
        color: #1e293b !important;
    }

    [data-testid="stTooltipContent"] p,
    [data-testid="stTooltipContent"] span {
        color: #1e293b !important;
    }

    [role="tooltip"] p,
    [role="tooltip"] span {
        color: #1e293b !important;
    }

    /* ===== FILE UPLOADER DRAG & DROP BUTTONS ===== */
    [data-testid="stFileUploadDropzone"] {
        background: linear-gradient(135deg, var(--selection-bg) 0%, #fef9c3 100%) !important;
        border: 2px dashed var(--selection-border) !important;
        border-radius: var(--radius-lg) !important;
    }

    [data-testid="stFileUploadDropzone"]:hover {
        border-color: #facc15 !important;
        background: linear-gradient(135deg, #fef9c3 0%, #fef08a 100%) !important;
    }

    [data-testid="stFileUploadDropzone"] button {
        background: linear-gradient(135deg, var(--selection-bg) 0%, #fef9c3 100%) !important;
        color: var(--selection-text) !important;
        border: 1px solid var(--selection-border) !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
        border-radius: var(--radius-md) !important;
        box-shadow: 0 4px 6px -1px rgba(250, 204, 21, 0.3) !important;
    }

    [data-testid="stFileUploadDropzone"] button:hover {
        background: linear-gradient(135deg, #facc15 0%, #fef08a 100%) !important;
    }

    /* Estilos para file uploader widget */
    .stFileUploader > div {
        background: linear-gradient(135deg, var(--selection-bg) 0%, #fef9c3 100%) !important;
        background-color: #fef08a !important;
        border-radius: var(--radius-lg) !important;
        border: 2px dashed var(--selection-border) !important;
    }

    .stFileUploader [data-testid="stWidgetLabel"] {
        color: var(--selection-text) !important;
        font-weight: 600 !important;
    }

    .stFileUploader button {
        background: linear-gradient(135deg, var(--selection-bg) 0%, #fef9c3 100%) !important;
        background-color: #fef08a !important;
        color: var(--selection-text) !important;
        border: 1px solid var(--selection-border) !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
        border-radius: var(--radius-md) !important;
    }

    .stFileUploader button:hover {
        background: linear-gradient(135deg, #facc15 0%, #fef08a 100%) !important;
        background-color: #facc15 !important;
    }

    /* Archivo cargado */
    [data-testid="stFileUploaderFile"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--selection-border) !important;
        border-radius: var(--radius-md) !important;
    }

    /* Dropzone area */
    [data-testid="stFileUploadDropzone"] > div {
        background: transparent !important;
    }

    /* Drag text */
    [data-testid="stFileUploadDropzone"] p {
        color: var(--selection-text) !important;
        font-weight: 500 !important;
    }

</style>
""", unsafe_allow_html=True)

# --- CONSTANTES ---
APP_DIR = get_app_dir()
DATA_DIR = get_data_dir()
os.makedirs(DATA_DIR, exist_ok=True)

ARCHIVO_JSON = os.path.join(DATA_DIR, "preguntas.json")
ARCHIVO_HISTORIAL = os.path.join(DATA_DIR, "historial_fallos.json")
CARPETA_IMAGENES = os.path.join(DATA_DIR, "imagenes_preguntas")
os.makedirs(CARPETA_IMAGENES, exist_ok=True)


def get_relative_image_path(abs_path):
    """Convierte ruta absoluta a relativa para exportar."""
    if not abs_path or not os.path.isabs(abs_path):
        return abs_path
    try:
        return os.path.relpath(abs_path, DATA_DIR)
    except ValueError:
        return abs_path


def resolve_image_path(rel_path):
    """Convierte ruta relativa a absoluta para mostrar."""
    if not rel_path:
        return None
    if os.path.isabs(rel_path):
        return rel_path
    return os.path.join(DATA_DIR, rel_path)


# --- FUNCIONES EXPORT/IMPORT ZIP ---
# export_questions_to_zip / import_questions_from_zip viven en src/backup.py
# (endurecidas: sin extractall, tope de tamaño anti zip-bomb).


def _initialize_resources():
    """Copia recursos por defecto al directorio de datos si no existen."""
    app_json = os.path.join(APP_DIR, "preguntas.json")
    if os.path.exists(app_json) and not os.path.exists(ARCHIVO_JSON):
        shutil.copy2(app_json, ARCHIVO_JSON)
    
    app_img_dir = os.path.join(APP_DIR, "imagenes_preguntas")
    data_img_dir = CARPETA_IMAGENES
    if os.path.exists(app_img_dir) and os.path.isdir(app_img_dir):
        if not os.path.exists(data_img_dir) or not os.listdir(data_img_dir):
            if os.path.exists(data_img_dir):
                shutil.rmtree(data_img_dir)
            shutil.copytree(app_img_dir, data_img_dir)

_initialize_resources()

# --- PANTALLA DE CONFIGURACIÓN INICIAL ---
if "config_completed" not in st.session_state:
    saved_key = load_api_key()
    st.session_state.config_completed = saved_key is not None or has_api_key()
    st.session_state.api_key_ocr = saved_key or ""

if not st.session_state.config_completed:
    st.title("🎓 Why need a VCE app?")
    st.markdown("### Bienvenido al Simulador de Exámenes de Certificación")
    
    st.markdown("---")
    st.markdown("#### Configuración Inicial")
    st.markdown("Para usar la funcionalidad de **OCR** (extracción de preguntas desde imágenes), necesitas configurar tu API Key de Google Gemini.")
    
    api_key_input = st.text_input(
        "API Key de Google Gemini",
        type="password",
        placeholder="Ingresa tu API Key...",
        key="api_key_setup_input"
    )
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("Guardar API Key", type="primary", use_container_width=True):
            if api_key_input:
                if save_api_key(api_key_input):
                    st.session_state.api_key_ocr = api_key_input
                    st.session_state.config_completed = True
                    st.success("API Key guardada correctamente. La funcionalidad OCR estará disponible.")
                    st.rerun()
                else:
                    st.error("Error al guardar la API Key. Asegúrate de tener cryptography instalado.")
            else:
                st.warning("Por favor, ingresa una API Key.")
    
    with col_btn2:
        if st.button("Continuar sin OCR", use_container_width=True):
            st.session_state.config_completed = True
            st.session_state.api_key_ocr = ""
            st.rerun()
    
    with st.expander("Como obtener una API Key?"):
        st.markdown("""
        1. Ve a [Google AI Studio](https://makersuite.google.com/app/apikey)
        2. Inicia sesión con tu cuenta de Google
        3. Crea una nueva API Key
        4. Copia la clave y pégala arriba
        """)
    
    st.markdown("---")
    st.info("Si no tienes API Key, puedes usar el simulador sin OCR. Podrás añadir preguntas manualmente.")
    
    st.stop()

st.title("📚 Why need a VCE app?")

# --- FUNCIONES DE CARGA/GUARDADO ---
@st.cache_data(ttl=10)
def load_questions():
    try:
        with open(ARCHIVO_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        # JSON corrupto: se renombra a .corrupta_<timestamp> para que el
        # siguiente guardado no lo machaque y el usuario pueda recuperarlo.
        try:
            os.replace(ARCHIVO_JSON, f"{ARCHIVO_JSON}.corrupta_{int(time.time())}")
        except OSError:
            pass
        return []

def save_questions(preguntas_actualizadas):
    # Escritura atomica: se escribe en un .tmp y se renombra con os.replace,
    # asi un cierre a mitad de guardado no deja el JSON a medias.
    tmp_path = ARCHIVO_JSON + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(preguntas_actualizadas, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, ARCHIVO_JSON)
    load_questions.clear()

def _registrar_historial():
    """Registra el examen recién terminado en el historial de fallos.

    Cualquier no acierto (incorrecta, parcial o no respondida) suma un fallo
    por pregunta. Se llama una sola vez por examen (Finalizar, timeout del
    timer o fallback de resultados): el flag de sesión evita dobles registros
    cuando el timeout y el cálculo de resultados coinciden en el mismo rerun.
    """
    if st.session_state.get("historial_examen_registrado", False):
        return
    try:
        historial = cargar_historial(ARCHIVO_HISTORIAL)
        historial = registrar_examen(
            historial,
            st.session_state.preguntas_simulador,
            st.session_state.respuestas_usuario,
        )
        guardar_historial(ARCHIVO_HISTORIAL, historial)
    except (OSError, KeyError):
        # Un fallo de disco no debe romper la pantalla de resultados.
        pass
    st.session_state.historial_examen_registrado = True

preguntas = load_questions()

# --- FUNCIÓN DE ALEATORIZACIÓN ---
def aleatorizar_pregunta(pregunta):
    """
    Aleatoriza las opciones de una pregunta manteniendo la trazabilidad
    de las respuestas correctas. Soporta múltiples formatos (A), A., A -, etc.)
    """
    pregunta_aleatoria = copy.deepcopy(pregunta)
    
    opciones_originales = pregunta["opciones"]
    
    # Extraer letras y textos de forma robusta usando regex
    pares_originales = []
    for opcion in opciones_originales:
        par = prefijo_opcion(opcion)
        if par:
            pares_originales.append(par)
    
    if not pares_originales:
        return pregunta_aleatoria
    
    # Mezclar las opciones
    random.shuffle(pares_originales)
    
    # Reconstruir opciones con nuevas letras
    letras_disponibles = ["A", "B", "C", "D", "E", "F"]
    nuevas_opciones = []
    mapa_nuevas_letras = {}
    
    for idx, (letra_original, texto) in enumerate(pares_originales):
        if idx >= len(letras_disponibles):
            break
        nueva_letra = letras_disponibles[idx]
        nuevas_opciones.append(f"{nueva_letra}) {texto}")
        mapa_nuevas_letras[letra_original] = nueva_letra
    
    # Mapear las respuestas correctas a las nuevas letras
    nuevas_correctas = [mapa_nuevas_letras.get(letra, letra) for letra in pregunta["correctas"]]
    
    pregunta_aleatoria["opciones"] = nuevas_opciones
    pregunta_aleatoria["correctas"] = nuevas_correctas
    
    return pregunta_aleatoria

# --- FUNCIÓN OCR ---
def extract_text_from_image(image_path, api_key, modelo="gemini-2.5-flash", max_retries=2):
    if not GENAI_AVAILABLE:
        return {"error": "google.genai no está instalado. Ejecuta: pip install google-genai"}
    
    for intento in range(max_retries):
        try:
            client = genai.Client(api_key=api_key)
            
            img = Image.open(image_path)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            import io
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=95)
            img_bytes = img_byte_arr.getvalue()
            
            prompt = """
            Eres un asistente experto en analizar capturas de pantalla de exámenes de certificación.
            Extrae el texto de la imagen y devuélvelo ESTRICTAMENTE en este formato JSON:
            {
                "pregunta": "Aquí el texto de la pregunta completa",
                "respuestas": [
                    "A) texto de la primera opción (usa \\n para saltos de línea si la opción tiene múltiples líneas)",
                    "B) texto de la segunda opción",
                    ...
                ]
            }
            
            IMPORTANTE:
            - Si una opción tiene múltiples líneas (código, listas, texto largo), preserva el formato usando \\n
            - Ignora cualquier texto de interfaz (botones, logos, horas, etc.)
            - Si no hay opciones de respuesta, deja la lista "respuestas" vacía
            - Devuelve SOLO el JSON válido, sin markdown
            """
            
            response = client.models.generate_content(
                model=modelo,
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=img_bytes,
                        mime_type='image/jpeg'
                    )
                ]
            )
            
            if not response or not response.text:
                return {"error": "Gemini no devolvió contenido."}
            
            texto_limpio = response.text.strip()
            
            # Limpiar marcas de markdown
            if texto_limpio.startswith("```json"):
                texto_limpio = texto_limpio[7:].rstrip("```").strip()
            elif texto_limpio.startswith("```"):
                texto_limpio = texto_limpio[3:].rstrip("```").strip()
            
            # Validar que no esté vacío después de limpiar
            if not texto_limpio:
                return {"error": "La respuesta está vacía después de procesar."}
            
            try:
                data = json.loads(texto_limpio)
            except json.JSONDecodeError:
                return {"error": f"JSON inválido. La respuesta no es un JSON válido."}
            
            # Validar estructura del JSON
            if not isinstance(data, dict):
                return {"error": "JSON inválido: la raíz debe ser un objeto."}
            
            if "pregunta" not in data:
                return {"error": "JSON inválido: falta el campo 'pregunta'."}
            
            if "respuestas" not in data:
                return {"error": "JSON inválido: falta el campo 'respuestas'."}
            
            # Validar tipos
            if not isinstance(data.get("pregunta"), str):
                return {"error": "JSON inválido: 'pregunta' debe ser texto."}
            
            if not isinstance(data.get("respuestas"), list):
                return {"error": "JSON inválido: 'respuestas' debe ser una lista."}
                
            return data
            
        except json.JSONDecodeError as e:
            texto_error = response.text[:200] if response and hasattr(response, 'text') else 'Sin respuesta'
            return {"error": f"Error al parsear JSON: {str(e)}\n\nRespuesta: {texto_error}..."}
        
        except Exception as e:
            error_str = str(e)
            
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                retry_match = re.search(r'retry in (\d+(?:\.\d+)?)', error_str)
                wait_seconds = int(float(retry_match.group(1))) if retry_match else 30
                
                return {
                    "error": "cuota_excedida",
                    "mensaje": f"""🚫 **Cuota de API agotada**

Has excedido los límites gratuitos de Google Gemini.

**Soluciones:**
1. ⏳ Espera {wait_seconds} segundos y reintenta
2. 🔑 Crea una nueva API Key: https://makersuite.google.com/app/apikey
3. ✍️ Usa la pestaña "Ingesta Manual"
                    """.strip()
                }
            
            if intento < max_retries - 1:
                time.sleep(2 ** intento)
                continue
            
            return {"error": f"Error: {str(e)}"}
    
    return {"error": "Máximo de reintentos alcanzado"}

# --- FUNCIÓN PARA LIMPIAR FORMULARIO MANUAL ---
def limpiar_formulario_manual():
    st.session_state.manual_enunciado = ""
    st.session_state.manual_imagen = None
    st.session_state.manual_tag = ""
    for letra in ["A", "B", "C", "D", "E", "F"]:
        st.session_state[f"manual_texto_{letra}"] = ""
        st.session_state[f"manual_corr_{letra}"] = False

# --- FUNCIÓN PARA CERRAR EL EDITOR DE UNA PREGUNTA ---
def cerrar_editor_pregunta(qid):
    """Borra de session_state las claves del editor de la pregunta qid.

    Sin esto, cancelar y reabrir el editor mostraría los textos de la
    sesion de edicion anterior: session_state conserva el valor de los
    widgets aunque el formulario ya no exista.
    """
    st.session_state.pop(f"editando_{qid}", None)
    st.session_state.pop(f"edit_enun_{qid}", None)
    for letra in LETRAS_OPCIONES:
        st.session_state.pop(f"edit_texto_{letra}_{qid}", None)
        st.session_state.pop(f"edit_corr_{letra}_{qid}", None)

# --- PESTAÑAS PRINCIPALES CON ESTADO ---
opciones_pestanas = ["✍️ Ingesta Manual", "📸 Extracción OCR", "📊 Ver Preguntas", "🎮 Simulador", "🔁 Sección Errores Reiterados"]

if "pestana_actual" not in st.session_state:
    st.session_state.pestana_actual = opciones_pestanas[0]

if st.session_state.pestana_actual not in opciones_pestanas:
    st.session_state.pestana_actual = opciones_pestanas[0]

try:
    index_inicial = opciones_pestanas.index(st.session_state.pestana_actual)
except ValueError:
    index_inicial = 0

pestana_seleccionada = st.radio(
    "Navegación",
    opciones_pestanas,
    index=index_inicial,
    horizontal=True,
    label_visibility="collapsed",
    key="pestana_radio"
)
st.session_state.pestana_seleccionada = pestana_seleccionada

# ========================================
# PESTAÑA 1: INGESTA MANUAL
# ========================================
if pestana_seleccionada == opciones_pestanas[0]:
    st.header("✍️ Añadir Pregunta Manualmente")
    st.markdown("Rellena el formulario para añadir una pregunta directamente.")
    
    if "manual_enunciado" not in st.session_state:
        st.session_state.manual_enunciado = ""
    if "manual_imagen" not in st.session_state:
        st.session_state.manual_imagen = None
    if "manual_tag" not in st.session_state:
        st.session_state.manual_tag = ""
    
    with st.form("form_manual", clear_on_submit=False):
        enunciado = st.text_area(
            "📝 Enunciado de la pregunta *", 
            height=120, 
            value=st.session_state.manual_enunciado,
            placeholder="Ejemplo: ¿Cuál de las siguientes opciones describe mejor...?",
            key="form_enunciado"
        )
        
        imagen_subida = st.file_uploader(
            "🖼️ Imagen adjunta (opcional)", 
            type=["png", "jpg", "jpeg"],
            key="img_upload_manual"
        )
        
        tag_manual = st.text_input(
            "🏷️ Tag / Categoría",
            value=st.session_state.manual_tag,
            placeholder="Ej: Palo Alto, Forcepoint, Fortinet...",
            key="form_tag",
            help="Etiqueta para agrupar preguntas (ej: vendor, tecnología)"
        )
        
        st.markdown("### Opciones de Respuesta")
        st.caption("⚠️ Rellena al menos 2 opciones y ✅ marca las correctas (puedes marcar múltiples).")
        
        letras = ["A", "B", "C", "D", "E", "F"]
        opciones_inputs = {}
        correctas_checks = {}
        
        for letra in letras:
            col1, col2 = st.columns([5, 1])
            with col1:
                if f"manual_texto_{letra}" not in st.session_state:
                    st.session_state[f"manual_texto_{letra}"] = ""
                
                opciones_inputs[letra] = st.text_input(
                    f"Opción {letra}", 
                    value=st.session_state[f"manual_texto_{letra}"],
                    key=f"form_texto_{letra}",
                    placeholder=f"Escribe la respuesta {letra}..."
                )
            with col2:
                st.write("")
                if f"manual_corr_{letra}" not in st.session_state:
                    st.session_state[f"manual_corr_{letra}"] = False
                
                correctas_checks[letra] = st.checkbox(
                    "✅ Correcta", 
                    value=st.session_state[f"manual_corr_{letra}"],
                    key=f"form_corr_{letra}"
                )
        
        col_submit, col_reset = st.columns([3, 1])
        
        with col_submit:
            submitted = st.form_submit_button("💾 Guardar Pregunta", type="primary", use_container_width=True)
        
        with col_reset:
            reset = st.form_submit_button("🔄 Limpiar", use_container_width=True)
        
        if reset:
            limpiar_formulario_manual()
            st.rerun()
        
        if submitted:
            st.session_state.manual_enunciado = enunciado
            st.session_state.manual_tag = tag_manual
            for letra in letras:
                st.session_state[f"manual_texto_{letra}"] = opciones_inputs[letra]
                st.session_state[f"manual_corr_{letra}"] = correctas_checks[letra]
            
            if not enunciado.strip():
                st.error("❌ El enunciado es obligatorio.")
            else:
                opciones_capturadas = []
                correctas_capturadas = []
                
                for letra in letras:
                    texto = opciones_inputs[letra].strip()
                    if texto:
                        opciones_capturadas.append(f"{letra}) {texto}")
                        if correctas_checks[letra]:
                            correctas_capturadas.append(letra)
                
                if len(opciones_capturadas) < 2:
                    st.error("❌ Debes rellenar al menos 2 opciones.")
                elif not correctas_capturadas:
                    st.error("❌ Debes marcar al menos una respuesta correcta.")
                else:
                    with st.spinner("💾 Guardando pregunta..."):
                        preguntas_actuales = load_questions()
                        nuevo_id = 1 if not preguntas_actuales else max(p.get("id", 0) for p in preguntas_actuales) + 1
                        ruta_imagen = None
                        
                        if imagen_subida:
                            extension = imagen_subida.name.split(".")[-1]
                            nombre_archivo = f"img_q{nuevo_id}_{int(time.time())}.{extension}"
                            ruta_absoluta = os.path.join(CARPETA_IMAGENES, nombre_archivo)
                            with open(ruta_absoluta, "wb") as f:
                                f.write(imagen_subida.getbuffer())
                            ruta_imagen = get_relative_image_path(ruta_absoluta)
                        
                        nueva_pregunta = {
                            "id": nuevo_id,
                            "pregunta": enunciado.strip(),
                            "imagen": ruta_imagen,
                            "tag": tag_manual.strip(),
                            "opciones": opciones_capturadas,
                            "correctas": correctas_capturadas
                        }
                        
                        preguntas_actuales.append(nueva_pregunta)
                        save_questions(preguntas_actuales)
                    
                    st.success(f"✅ ¡Pregunta #{nuevo_id} guardada!")
                    # El toast sobrevive al rerun inmediato (los balloons no),
                    # y sin sleep(1) el guardado no bloquea el servidor.
                    st.toast("✅ Pregunta guardada!", icon="🎉")

                    limpiar_formulario_manual()
                    st.rerun()

# ========================================
# PESTAÑA 2: EXTRACCIÓN OCR
# ========================================
elif pestana_seleccionada == "📸 Extracción OCR":
    st.header("📸 Extracción Automática con OCR (Gemini)")
    
    if not GENAI_AVAILABLE:
        st.error("❌ El módulo `google.genai` no está instalado.")
        st.code("pip install google-genai", language="bash")
    else:
        st.markdown("Sube una captura y guarda directamente en la base de datos.")
        
        col_config1, col_config2 = st.columns([2, 1])
        
        with col_config1:
            with st.expander("🔑 Configurar API Key", expanded=True):
                saved_key = load_api_key()
                key_status = "✅ Configurada" if saved_key else "⚠️ No configurada"
                st.write(f"**Estado:** {key_status}")
                
                if saved_key:
                    st.session_state.api_key_ocr = saved_key
                    st.info("Tienes una API Key guardada. Puedes usarla o cambiarla.")
                
                new_key = st.text_input(
                    "API Key de Google Gemini",
                    value="",
                    type="password",
                    placeholder="Ingresa nueva API Key para actualizar...",
                    key="api_key_ocr_input"
                )
                
                col_save, col_clear = st.columns(2)
                with col_save:
                    if st.button("💾 Guardar Key", use_container_width=True):
                        if new_key:
                            if save_api_key(new_key):
                                st.session_state.api_key_ocr = new_key
                                st.success("API Key actualizada correctamente!")
                                st.rerun()
                            else:
                                st.error("Error al guardar la key.")
                        else:
                            st.warning("Ingresa una API Key.")
                with col_clear:
                    if st.button("🗑️ Eliminar Key", use_container_width=True):
                        from src.api_key_manager import delete_api_key
                        delete_api_key()
                        st.session_state.api_key_ocr = ""
                        st.info("API Key eliminada.")
                        st.rerun()
                
                st.caption("🔗 [Obtén tu API Key](https://makersuite.google.com/app/apikey)")
        
        with col_config2:
            with st.expander("⚙️ Modelo", expanded=False):
                modelo_seleccionado = st.selectbox(
                    "Modelo",
                    options=[
                        "gemini-2.5-flash",
                        "gemini-3-flash-preview",
                        "gemini-3.1-pro-preview"
                    ],
                    index=0
                )
        
        uploaded_file = st.file_uploader(
            "📤 Sube captura de pantalla",
            type=["png", "jpg", "jpeg"],
            key="img_upload_ocr"
        )
        
        if uploaded_file is not None:
            col_prev, col_full = st.columns([2, 1])
            
            with col_prev:
                st.image(uploaded_file, caption="Vista previa", width=400)
            
            with col_full:
                st.write("")
                with st.expander("🔍 Ver tamaño completo"):
                    st.image(uploaded_file, use_container_width=True)
            
            # Temporal en el data dir (nunca en el CWD: en el .exe empaquetado
            # puede ser Program Files, que no es escribible).
            temp_path = os.path.join(DATA_DIR, "temp_capture_ocr.png")
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            if st.button("🚀 Procesar con OCR", type="primary", use_container_width=True):
                if not st.session_state.api_key_ocr.strip():
                    st.error("❌ Ingresa tu API Key arriba.")
                else:
                    with st.spinner(f"🧠 Analizando imagen con {modelo_seleccionado}..."):
                        resultado_texto = extract_text_from_image(
                            temp_path, 
                            st.session_state.api_key_ocr,
                            modelo=modelo_seleccionado
                        )
                        
                        st.session_state.resultado_ocr = resultado_texto
                        st.session_state.imagen_ocr_path = temp_path
                    
                    st.toast("✅ Análisis completado!", icon="✅")
            
            if "resultado_ocr" in st.session_state and st.session_state.resultado_ocr:
                resultado_texto = st.session_state.resultado_ocr
                
                st.success("✅ Procesamiento completado!")
                st.markdown("---")
                
                if "error" not in resultado_texto:
                    st.markdown("### ✏️ Revisar y Guardar")
                    
                    with st.expander("🖼️ Ver imagen capturada a tamaño completo", expanded=False):
                        if os.path.exists(st.session_state.imagen_ocr_path):
                            st.image(st.session_state.imagen_ocr_path, use_container_width=True)
                    
                    pregunta_editada = st.text_area(
                        "📝 Pregunta", 
                        resultado_texto.get("pregunta", ""), 
                        height=120, 
                        key="ocr_pregunta_editable"
                    )
                    
                    st.markdown("**Opciones de respuesta:**")
                    st.caption("✏️ Edita si es necesario y ✅ marca las correctas")
                    
                    respuestas = normalizar_opciones_ocr(resultado_texto.get("respuestas", []))
                    opciones_guardadas = []
                    correctas_marcadas = []
                    
                    for idx, (letra, texto_opcion) in enumerate(respuestas):
                        
                        col_opt, col_check = st.columns([5, 1])
                        
                        with col_opt:
                            texto_editado = st.text_area(
                                f"Opción {letra}",
                                value=texto_opcion,
                                height=90,
                                key=f"ocr_opcion_{idx}",
                                help="Edita si es necesario, puedes usar múltiples líneas"
                            )
                            
                            if texto_editado.strip():
                                opciones_guardadas.append(f"{letra}) {texto_editado.strip()}")
                        
                        with col_check:
                            st.write("")
                            st.write("")
                            es_correcta = st.checkbox(
                                f"✅ {letra}",
                                key=f"ocr_correcta_{idx}",
                                help=f"Marca si {letra} es correcta"
                            )
                            
                            if es_correcta and texto_editado.strip():
                                correctas_marcadas.append(letra)
                    
                    incluir_imagen = st.checkbox(
                        "📎 Guardar imagen adjunta",
                        value=True
                    )
                    
                    tag_ocr = st.text_input(
                        "🏷️ Tag / Categoría",
                        placeholder="Ej: Palo Alto, Forcepoint, Fortinet...",
                        key="ocr_tag",
                        help="Etiqueta para agrupar preguntas (ej: vendor, tecnología)"
                    )
                    
                    col_save, col_cancel = st.columns([3, 1])
                    
                    with col_save:
                        if st.button("💾 Guardar en Base de Datos", type="primary", use_container_width=True):
                            if not pregunta_editada.strip():
                                st.error("❌ La pregunta no puede estar vacía")
                            elif len(opciones_guardadas) < 2:
                                st.error("❌ Debe haber al menos 2 opciones")
                            elif not correctas_marcadas:
                                st.error("❌ Marca al menos una correcta")
                            else:
                                with st.spinner("💾 Guardando..."):
                                    preguntas_actuales = load_questions()
                                    nuevo_id = 1 if not preguntas_actuales else max(p.get("id", 0) for p in preguntas_actuales) + 1
                                    ruta_imagen = None
                                    
                                    if incluir_imagen and os.path.exists(st.session_state.imagen_ocr_path):
                                        import shutil
                                        nombre_archivo = f"img_q{nuevo_id}_ocr_{int(time.time())}.png"
                                        ruta_absoluta = os.path.join(CARPETA_IMAGENES, nombre_archivo)
                                        shutil.copy(st.session_state.imagen_ocr_path, ruta_absoluta)
                                        ruta_imagen = get_relative_image_path(ruta_absoluta)
                                    
                                    nueva_pregunta = {
                                        "id": nuevo_id,
                                        "pregunta": pregunta_editada.strip(),
                                        "imagen": ruta_imagen,
                                        "tag": tag_ocr.strip() if tag_ocr else "",
                                        "opciones": opciones_guardadas,
                                        "correctas": correctas_marcadas
                                    }
                                    
                                    preguntas_actuales.append(nueva_pregunta)
                                    save_questions(preguntas_actuales)
                                
                                st.success(f"🎉 ¡Pregunta #{nuevo_id} guardada!")
                                st.toast("✅ Pregunta guardada exitosamente!", icon="🎉")

                                del st.session_state.resultado_ocr
                                if os.path.exists(temp_path):
                                    os.remove(temp_path)

                                st.rerun()
                    
                    with col_cancel:
                        if st.button("🔄 Nueva captura", use_container_width=True):
                            del st.session_state.resultado_ocr
                            if os.path.exists(temp_path):
                                os.remove(temp_path)
                            st.rerun()
                
                elif resultado_texto.get("error") == "cuota_excedida":
                    st.error("🚫 Cuota agotada")
                    st.markdown(resultado_texto.get("mensaje", ""))
                else:
                    st.error(f"❌ {resultado_texto['error']}")

# ========================================
# PESTAÑA 3: VER PREGUNTAS
# ========================================
elif pestana_seleccionada == "📊 Ver Preguntas":
    st.header("📊 Base de Datos de Preguntas")
    
    preguntas = load_questions()
    
    if not preguntas:
        st.info("ℹ️ No hay preguntas guardadas.")
        
        st.markdown("### 📥 Importar preguntas desde archivo")
        
        archivo_importar = st.file_uploader(
            "Selecciona un archivo JSON o ZIP con preguntas",
            type=["json", "zip"],
            help="Sube un archivo JSON o ZIP (con imágenes) con el formato correcto de preguntas",
            key="importar_inicial"
        )

        if archivo_importar is not None:
            es_zip = archivo_importar.name.endswith('.zip')
            contenido = None

            try:
                if es_zip:
                    contenido = import_questions_from_zip(archivo_importar.getvalue(), DATA_DIR)
                    if isinstance(contenido, dict) and "error" in contenido:
                        st.error(f"❌ {contenido['error']}")
                        contenido = None
                else:
                    contenido = json.load(archivo_importar)
            except json.JSONDecodeError:
                st.error("❌ El archivo no es un JSON válido")
                contenido = None
            except Exception as e:
                st.error(f"❌ Error al importar: {str(e)}")
                contenido = None

            if contenido is not None and not (isinstance(contenido, list) and contenido):
                st.error("❌ El archivo está vacío o no contiene una lista de preguntas")
            elif contenido:
                preguntas_validas, errores_import = validar_preguntas_importadas(contenido)

                if errores_import:
                    with st.expander(f"⚠️ {len(errores_import)} entrada(s) inválidas (se ignorarán)"):
                        for err in errores_import:
                            st.markdown(f"- {err}")

                if preguntas_validas:
                    st.success(f"✅ Archivo válido: {len(preguntas_validas)} preguntas detectadas")

                    with st.expander("👀 Vista previa de las preguntas"):
                        for i, p in enumerate(preguntas_validas[:5]):
                            st.markdown(f"**{i+1}.** {p['pregunta'][:80]}...")
                        if len(preguntas_validas) > 5:
                            st.caption(f"... y {len(preguntas_validas) - 5} preguntas más")

                    if st.button("✅ Importar todas las preguntas", type="primary"):
                        with st.spinner("📥 Importando..."):
                            reasignar_ids(preguntas_validas)
                            save_questions(preguntas_validas)
                        st.success(f"🎉 ¡{len(preguntas_validas)} preguntas importadas!")
                        st.toast("✅ Importación exitosa!", icon="🎉")
                        st.rerun()
                else:
                    st.error("❌ Ninguna pregunta del archivo pasa la validación")

    else:
        st.success(f"✅ {len(preguntas)} pregunta(s) guardada(s)")

        _unicas, _dups = deduplicar(preguntas)
        if _dups:
            _ids_dup = ", ".join(f"#{p.get('id')}" for p in _dups)
            st.warning(
                f"⚠️ Hay {len(_dups)} pregunta(s) repetida(s) en el banco ({_ids_dup}). "
                "El simulador las omite automáticamente, pero puedes borrarlas aquí."
            )
        for _grupo in detectar_conflictos(preguntas):
            _ids_conf = " y ".join(f"#{i}" for i in _grupo)
            st.error(
                f"❌ Las preguntas {_ids_conf} son iguales pero tienen respuestas correctas "
                "distintas. Una de las dos está mal: corrígela o bórrala."
            )
        
        tags_unicos = sorted(set(p.get("tag", "") for p in preguntas if p.get("tag", "")))
        tiene_sin_tag = any(not p.get("tag", "") for p in preguntas)
        if tiene_sin_tag:
            tags_unicos = ["Sin tag"] + tags_unicos
        if tags_unicos:
            tag_counts = {}
            for p in preguntas:
                t = p.get("tag", "") or "Sin tag"
                tag_counts[t] = tag_counts.get(t, 0) + 1
            stats_str = " | ".join(f"{t} ({c})" for t, c in sorted(tag_counts.items()))
            st.markdown(f"🏷️ **Tags:** {stats_str}")
        
        st.markdown("### 🔧 Herramientas")
        
        col_buscar, col_aleatorio = st.columns([3, 1])
        
        with col_buscar:
            buscar = st.text_input("🔍 Buscar", placeholder="Palabras clave...")
        
        with col_aleatorio:
            st.write("")
            mostrar_aleatorio = st.checkbox("🎲 Aleatorizar", key="mostrar_aleatorio")
        
        if tags_unicos:
            tags_filtrar = st.multiselect(
                "🏷️ Filtrar por tag",
                options=tags_unicos,
                key="filtro_tag_ver",
                help="Selecciona uno o más tags para filtrar las preguntas mostradas"
            )
        else:
            tags_filtrar = []
        
        with st.expander("📥 Importar / 📤 Exportar preguntas"):
            col_exp, col_imp = st.columns(2)
            
            with col_exp:
                st.markdown("**📤 Exportar (ZIP)**")
                # El ZIP solo se construye al pulsar el botón: empaquetar el
                # banco (JSON + todas las imágenes) en cada rerun era coste
                # inútil. Se invalida solo si el banco cambió en disco (mtime).
                huella_banco = (f"{len(preguntas)}_"
                                f"{int(os.path.getmtime(ARCHIVO_JSON)) if os.path.exists(ARCHIVO_JSON) else 0}")
                if st.session_state.get("zip_export_huella") != huella_banco:
                    st.session_state.zip_export_data = None

                if st.button("📦 Generar backup ZIP", key="gen_zip"):
                    with st.spinner("📦 Empaquetando..."):
                        st.session_state.zip_export_data = export_questions_to_zip(preguntas, DATA_DIR)
                        st.session_state.zip_export_huella = huella_banco
                    st.toast("📦 Backup listo para descargar", icon="📦")

                zip_data = st.session_state.get("zip_export_data")
                if zip_data:
                    st.download_button(
                        label="⬇️ Descargar ZIP",
                        data=zip_data,
                        file_name=f"preguntas_backup_{int(time.time())}.zip",
                        mime="application/zip",
                        use_container_width=True
                    )
            
            with col_imp:
                st.markdown("**📥 Importar**")
                archivo_importar = st.file_uploader(
                    "Selecciona archivo",
                    type=["json", "zip"],
                    key="importar_con_preguntas"
                )
        
        if archivo_importar is not None:
            es_zip = archivo_importar.name.endswith('.zip')
            
            try:
                if es_zip:
                    contenido = import_questions_from_zip(archivo_importar.getvalue(), DATA_DIR)
                    if isinstance(contenido, dict) and "error" in contenido:
                        st.error(contenido["error"])
                        contenido = None
                else:
                    contenido = json.load(archivo_importar)
            except Exception as e:
                st.error(f"Error al leer archivo: {str(e)}")
                contenido = None
            
            if contenido is not None and not (isinstance(contenido, list) and contenido):
                st.error("❌ El archivo está vacío o no contiene una lista de preguntas")
            elif contenido:
                preguntas_validas, errores_import = validar_preguntas_importadas(contenido)

                if errores_import:
                    with st.expander(f"⚠️ {len(errores_import)} entrada(s) inválidas (se ignorarán)"):
                        for err in errores_import:
                            st.markdown(f"- {err}")

                if preguntas_validas:
                    st.success(f"✅ Archivo válido: {len(preguntas_validas)} preguntas")

                    col_merge, col_replace = st.columns(2)

                    with col_merge:
                        if st.button("➕ Añadir", use_container_width=True):
                            with st.spinner("📥 Añadiendo..."):
                                max_id = max((p.get("id", 0) for p in preguntas), default=0)
                                for idx, p_nueva in enumerate(preguntas_validas):
                                    p_nueva["id"] = max_id + idx + 1
                                preguntas.extend(preguntas_validas)
                                save_questions(preguntas)
                            st.toast(f"✅ {len(preguntas_validas)} preguntas añadidas!", icon="✅")
                            st.rerun()

                    with col_replace:
                        if st.button("🔄 Reemplazar", type="secondary", use_container_width=True):
                            st.session_state.confirmar_reemplazo = True

                    if st.session_state.get("confirmar_reemplazo", False):
                        st.warning("⚠️ Esto borrará todas las preguntas actuales")
                        col1, col2 = st.columns(2)

                        with col1:
                            if st.button("✅ Confirmar", type="primary"):
                                with st.spinner("🔄 Reemplazando..."):
                                    reasignar_ids(preguntas_validas)
                                    save_questions(preguntas_validas)
                                # Las imágenes del banco anterior quedan
                                # huérfanas: se purgan contra el banco recién
                                # guardado (las del ZIP importado están
                                # referenciadas y sobreviven).
                                purgar_imagenes_huerfanas(CARPETA_IMAGENES, preguntas_validas)
                                st.session_state.confirmar_reemplazo = False
                                st.toast("✅ Base de datos reemplazada!", icon="🔄")
                                st.rerun()

                        with col2:
                            if st.button("❌ Cancelar"):
                                st.session_state.confirmar_reemplazo = False
                                st.rerun()
                else:
                    st.error("❌ Ninguna pregunta del archivo pasa la validación")
        
        st.markdown("---")

        if preguntas:
            col_del, col_space = st.columns([1, 4])
            with col_del:
                if st.button("🗑️ Eliminar Todas", type="secondary", use_container_width=True):
                    st.session_state.mostrar_confirmar_eliminar_todas = True

            if st.session_state.get("mostrar_confirmar_eliminar_todas", False):
                st.warning(f"⚠️ ¿Estás seguro de eliminar las {len(preguntas)} pregunta(s)? Esta acción no se puede deshacer.")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("✅ Confirmar Eliminación", type="primary", use_container_width=True):
                        preguntas.clear()
                        save_questions(preguntas)
                        purgar_imagenes_huerfanas(CARPETA_IMAGENES, preguntas)
                        st.toast("🗑️ Todas las preguntas eliminadas")
                        st.session_state.mostrar_confirmar_eliminar_todas = False
                        st.rerun()
                with col_cancel:
                    if st.button("❌ Cancelar", use_container_width=True):
                        st.session_state.mostrar_confirmar_eliminar_todas = False
                        st.rerun()

        st.markdown("---")

        preguntas_filtradas = preguntas
        if buscar.strip():
            preguntas_filtradas = [p for p in preguntas_filtradas if buscar.lower() in p['pregunta'].lower()]
        if tags_filtrar:
            preguntas_filtradas = [p for p in preguntas_filtradas if coincide_tag(p, tags_filtrar)]
        if buscar.strip() or tags_filtrar:
            st.caption(f"🔍 {len(preguntas_filtradas)} resultado(s)")

        # Numeracion de orden: se cuenta sobre el filtro de tags (no sobre la
        # busqueda de texto), que es exactamente lo que mide el rango del
        # simulador cuando se elige ese mismo tag.
        base_orden = [p for p in preguntas if coincide_tag(p, tags_filtrar)]
        posiciones = {id(p): i + 1 for i, p in enumerate(base_orden)}
        if tags_filtrar:
            st.caption(
                f"🔢 El **N.º** cuenta dentro del filtro de tags activo "
                f"({len(base_orden)} preguntas): es el número que usa el rango del simulador."
            )
        else:
            st.caption("🔢 El **N.º** es el orden de aparición: es el número que usa el rango del simulador.")

        for q in preguntas_filtradas:
            p_mostrar = aleatorizar_pregunta(q) if mostrar_aleatorio else q
            n_orden = posiciones.get(id(q), "?")
            
            with st.expander(f"❓ N.º {n_orden} · #{q['id']}: {q['pregunta'][:60]}..."):
                st.caption(f"N.º de orden **{n_orden}** (el que usa el rango del simulador) · id interno #{q['id']}")
                tag_actual = q.get("tag", "")
                if tag_actual:
                    st.info(f"🏷️ **Tag:** {tag_actual}")
                else:
                    st.caption("🏷️ Sin tag asignado")
                
                col_tag_input, col_tag_btn = st.columns([3, 1])
                with col_tag_input:
                    nuevo_tag = st.text_input(
                        "Tag",
                        value=tag_actual,
                        key=f"tag_edit_{q['id']}",
                        placeholder="Asignar tag...",
                        label_visibility="collapsed"
                    )
                with col_tag_btn:
                    if st.button("💾", key=f"save_tag_{q['id']}", help="Guardar tag"):
                        q["tag"] = nuevo_tag.strip()
                        save_questions(preguntas)
                        st.toast(f"✅ Tag actualizado: '{nuevo_tag.strip() or 'sin tag'}'", icon="🏷️")
                        st.rerun()
                
                st.markdown("---")
                
                # Al editar se usa SIEMPRE q (la original), nunca p_mostrar:
                # con "🎲 Aleatorizar" activo, p_mostrar está barajada y
                # guardar sobre ella reescribiría la pregunta mezclada.
                if st.session_state.get(f"editando_{q['id']}", False):
                    # st.form: sin él, cada pulsación de tecla rerun-ea la
                    # pestaña entera (todas las preguntas) por 8 widgets.
                    with st.form(key=f"form_edit_{q['id']}"):
                        st.text_area(
                            "📝 Enunciado",
                            height=120,
                            key=f"edit_enun_{q['id']}"
                        )
                        
                        st.caption("⚠️ Rellena al menos 2 opciones y marca las correctas (puedes marcar múltiples).")
                        for letra in LETRAS_OPCIONES:
                            col_txt, col_chk = st.columns([5, 1])
                            with col_txt:
                                st.text_input(
                                    f"Opción {letra}",
                                    key=f"edit_texto_{letra}_{q['id']}",
                                    placeholder=f"Escribe la respuesta {letra}...",
                                    label_visibility="collapsed"
                                )
                            with col_chk:
                                st.checkbox(
                                    letra,
                                    key=f"edit_corr_{letra}_{q['id']}",
                                    help=f"Marcar {letra} como correcta"
                                )
                        
                        col_guardar, col_cancelar = st.columns(2)
                        with col_guardar:
                            guardar_cambios = st.form_submit_button(
                                "💾 Guardar cambios", type="primary", use_container_width=True)
                        with col_cancelar:
                            cancelar_edicion = st.form_submit_button(
                                "❌ Cancelar", use_container_width=True)
                    
                    if cancelar_edicion:
                        cerrar_editor_pregunta(q["id"])
                        st.rerun()
                    
                    if guardar_cambios:
                        # Reconstruir opciones/correctas: correctas solo puede
                        # contener letras de opciones no vacías.
                        opciones_editadas = []
                        correctas_editadas = []
                        for letra in LETRAS_OPCIONES:
                            texto = st.session_state[f"edit_texto_{letra}_{q['id']}"].strip()
                            if texto:
                                opciones_editadas.append(f"{letra}) {texto}")
                                if st.session_state[f"edit_corr_{letra}_{q['id']}"]:
                                    correctas_editadas.append(letra)
                        
                        # Se reutiliza el validador de importación: una única
                        # fuente de verdad para el contrato del esquema.
                        candidata = {
                            "id": q["id"],
                            "pregunta": st.session_state[f"edit_enun_{q['id']}"],
                            "imagen": q.get("imagen"),
                            "tag": q.get("tag", ""),
                            "opciones": opciones_editadas,
                            "correctas": correctas_editadas,
                        }
                        validas_edit, errores_edit = validar_preguntas_importadas([candidata])
                        
                        if errores_edit:
                            for err in errores_edit:
                                st.error(f"❌ {err}")
                        else:
                            q.update(validas_edit[0])
                            save_questions(preguntas)
                            cerrar_editor_pregunta(q["id"])
                            st.toast("✅ Pregunta actualizada", icon="✏️")
                            st.rerun()
                else:
                    st.markdown(f"**{p_mostrar['pregunta']}**")
                    
                    imagen_path = resolve_image_path(p_mostrar.get("imagen"))
                    if imagen_path and os.path.exists(imagen_path):
                        st.image(imagen_path, use_container_width=True)
                    elif p_mostrar.get("imagen"):
                        st.warning("⚠️ Imagen no encontrada")
                    
                    st.markdown("**Opciones:**")
                    for opt in p_mostrar["opciones"]:
                        letra = opt[0]
                        if letra in p_mostrar['correctas']:
                            st.markdown(f"✅ **{opt}**")
                        else:
                            st.markdown(f"- {opt}")
                    
                    col_edit, col_del = st.columns(2)
                    
                    with col_edit:
                        if st.button("✏️ Editar", key=f"edit_{q['id']}", use_container_width=True):
                            # Sembrar los valores actuales del banco en las
                            # claves de los widgets: sin esto (o pasando
                            # value=), reabrir tras cancelar mostraría los
                            # textos de la sesión de edición anterior.
                            st.session_state[f"edit_enun_{q['id']}"] = q["pregunta"]
                            for i, letra in enumerate(LETRAS_OPCIONES):
                                if i < len(q["opciones"]):
                                    par = prefijo_opcion(q["opciones"][i])
                                    texto = par[1] if par else q["opciones"][i].strip()
                                    letra_origen = par[0] if par else letra
                                else:
                                    texto = ""
                                    letra_origen = letra
                                st.session_state[f"edit_texto_{letra}_{q['id']}"] = texto
                                st.session_state[f"edit_corr_{letra}_{q['id']}"] = (
                                    letra_origen in q.get("correctas", []))
                            st.session_state[f"editando_{q['id']}"] = True
                            st.rerun()
                    
                    with col_del:
                        if st.button(f"🗑️ Eliminar", key=f"del_{q['id']}", use_container_width=True):
                            # La purga se limita a la imagen de ESTA pregunta: borrar
                            # una pregunta no debe arrastrar huérfanas antiguas.
                            img_borrada = os.path.basename(q["imagen"]) if q.get("imagen") else None
                            preguntas.remove(q)
                            save_questions(preguntas)
                            if img_borrada:
                                purgar_imagenes_huerfanas(
                                    CARPETA_IMAGENES, preguntas, limitar_a={img_borrada})
                            st.toast("✅ Pregunta eliminada", icon="🗑️")
                            st.rerun()

# ========================================
# PESTAÑA 4: SIMULADOR OPTIMIZADO SIN PARPADEOS
# ========================================
elif pestana_seleccionada == "🎮 Simulador":
    st.header("🎮 Simulador de Examen")
    
    preguntas = load_questions()
    
    if not preguntas:
        st.info("ℹ️ No hay preguntas disponibles.")
    else:
        st.markdown(f"**📚 Banco:** {len(preguntas)} preguntas")
        
        # Inicializar estados
        if "simulador_activo" not in st.session_state:
            st.session_state.simulador_activo = False
        if "indice_actual" not in st.session_state:
            st.session_state.indice_actual = 0
        if "respuestas_usuario" not in st.session_state:
            st.session_state.respuestas_usuario = {}
        if "preguntas_simulador" not in st.session_state:
            st.session_state.preguntas_simulador = []
        if "mostrar_resultados" not in st.session_state:
            st.session_state.mostrar_resultados = False
        if "resultado_final" not in st.session_state:
            st.session_state.resultado_final = None

        # ========================================
        # PANTALLA 1: CONFIGURACIÓN (CON SLIDER EN LUGAR DE NUMBER_INPUT)
        # ========================================
        if not st.session_state.simulador_activo:
            
            st.markdown("### ⚙️ Configurar Examen")
            
            # El rango es un numero de orden sobre la lista YA FILTRADA por tag,
            # contando de arriba abajo igual que se ve en "Ver Preguntas" con ese
            # mismo filtro. Nunca es el #id: los ids cambian al borrar preguntas.
            tags_simulador = sorted(set(p.get("tag", "") for p in preguntas if p.get("tag", "")))
            hay_sin_tag = any(not p.get("tag", "") for p in preguntas)
            opciones_tags = tags_simulador + ([SIN_TAG] if hay_sin_tag else [])

            if opciones_tags:
                tags_seleccionados = st.multiselect(
                    "🏷️ Seleccionar tags a incluir",
                    options=opciones_tags,
                    default=opciones_tags,
                    key="tags_simulador",
                    help="Selecciona qué tags incluir en el examen. Si no seleccionas ninguno, se incluyen todas las preguntas."
                )
            else:
                tags_seleccionados = []

            st.markdown("---")

            usar_rango = st.checkbox(
                "📏 Seleccionar por rango ordinal",
                value=False,
                key="usar_rango",
                help="Elige un tramo por orden de aparición (ej. las 5 primeras del tag), no por el #id"
            )

            # Tamano del tramo elegible: manda el filtro de tags, no el banco entero.
            preguntas_con_tag = [p for p in preguntas if coincide_tag(p, tags_seleccionados)]

            rango = None
            if usar_rango:
                max_rango = max(len(preguntas_con_tag), 1)
                st.caption(
                    f"Contando sobre las **{len(preguntas_con_tag)}** preguntas del filtro actual, "
                    "de arriba abajo tal como salen en 'Ver Preguntas'."
                )

                for clave in ("rango_inicio", "rango_fin"):
                    if clave in st.session_state:
                        st.session_state[clave] = max(1, min(st.session_state[clave], max_rango))

                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    rango_inicio = st.number_input(
                        "Desde (N.º de orden)",
                        min_value=1,
                        max_value=max_rango,
                        step=1,
                        key="rango_inicio",
                        help="Orden dentro del filtro actual: 1 = la primera que aparece en 'Ver Preguntas' (no es el #id)"
                    )
                with col_r2:
                    rango_fin = st.number_input(
                        "Hasta (N.º de orden)",
                        min_value=1,
                        max_value=max_rango,
                        step=1,
                        key="rango_fin",
                        help="Orden dentro del filtro actual, contando de arriba abajo (no es el #id)"
                    )

                if rango_inicio > rango_fin:
                    st.info("ℹ️ Rango invertido: se interpretará como "
                            f"{rango_fin} a {rango_inicio}.")
                rango = (rango_inicio, rango_fin)

            preguntas_disponibles, info_pool = seleccionar_pool(
                preguntas, tags_seleccionados=tags_seleccionados, rango=rango
            )

            if rango:
                r_ini, r_fin = info_pool["rango"]
                st.caption(
                    f"📋 Preguntas **{r_ini}.ª a {r_fin}.ª** del filtro actual "
                    f"(de {info_pool['total_filtrado']}) → **{len(preguntas_disponibles)}** disponibles"
                )
                if preguntas_disponibles:
                    ids_incluidos = [p.get("id") for p in preguntas_disponibles]
                    st.caption(f"🆔 Corresponden a los ids: {', '.join(str(i) for i in ids_incluidos)}")
            else:
                st.caption(f"📋 Pool completo: **{len(preguntas_disponibles)}** preguntas")

            if info_pool["duplicados"]:
                ids_dup = ", ".join(str(i) for i in info_pool["ids_duplicados"])
                st.info(
                    f"ℹ️ Ese tramo trae **{info_pool['duplicados']}** pregunta(s) repetida(s) "
                    f"(id: {ids_dup}); se apartan para que no salgan dos veces. "
                    "Bórralas en 'Ver Preguntas' para que el tramo cuadre."
                )

            for grupo in info_pool["conflictos"]:
                ids_conf = " y ".join(str(i) for i in grupo)
                st.warning(
                    f"⚠️ Las preguntas {ids_conf} son iguales pero tienen respuestas "
                    "correctas distintas. Revísalas en 'Ver Preguntas': una de las dos está mal."
                )

            st.markdown("---")
            
            if len(preguntas_disponibles) == 0:
                st.error("❌ No hay preguntas disponibles con el rango/tag seleccionado.")
                st.stop()
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                if len(preguntas_disponibles) == 1:
                    num_preguntas = 1
                    st.info("📋 Solo hay 1 pregunta disponible en el pool seleccionado.")
                else:
                    # El pool cambia de tamaño al tocar rango o tags. Se guarda
                    # aparte cuántas preguntas quiere el usuario y solo se recorta
                    # para mostrar: así el valor no se queda "trinquetado" abajo
                    # cuando el pool vuelve a crecer.
                    tope = len(preguntas_disponibles)
                    deseado = st.session_state.get("num_preguntas_deseado", 10)
                    mostrado = max(1, min(deseado, tope))
                    num_preguntas = st.slider(
                        "🎯 Número de preguntas del examen",
                        min_value=1,
                        max_value=tope,
                        value=mostrado,
                        step=1,
                        help="Desliza para seleccionar cuántas preguntas quieres"
                    )
                    # Solo se registra como intención del usuario si movió el slider
                    # (o si el pool da de sobra), nunca el recorte automático.
                    if num_preguntas != mostrado or tope >= deseado:
                        st.session_state.num_preguntas_deseado = num_preguntas
                
                st.caption(f"📊 Seleccionadas: **{num_preguntas}** de {len(preguntas_disponibles)} preguntas disponibles")
            
            with col2:
                modo_examen = st.radio(
                    "🎮 Modo",
                    options=["Práctica", "Examen"],
                    index=0,
                    horizontal=True,
                    help="Práctica: sin límite de tiempo | Examen: con temporizador"
                )
            
            # Tiempo solo si es modo examen
            tiempo_minutos = 0
            if modo_examen == "Examen":
                st.markdown("---")
                tiempo_minutos = st.number_input(
                    "⏱️ Tiempo límite (minutos)",
                    min_value=1,
                    max_value=180,
                    value=30,
                    step=5,
                    help="Tiempo total para completar el examen"
                )
                st.caption(f"⏰ Tendrás {tiempo_minutos} minutos para {num_preguntas} preguntas")
            
            modo_aleatorio = st.checkbox("🎲 Orden aleatorio", value=True, key="modo_aleatorio")
            
            st.markdown("---")
            
            if st.button("🚀 Iniciar Examen", type="primary", use_container_width=True):
                with st.spinner("🎮 Preparando tu examen personalizado..."):
                    # preguntas_disponibles ya viene sin duplicados desde seleccionar_pool(),
                    # así que el muestreo entrega siempre el número de preguntas pedido.
                    preguntas_sel = random.sample(preguntas_disponibles, num_preguntas) if modo_aleatorio else preguntas_disponibles[:num_preguntas]
                    st.session_state.preguntas_simulador = [aleatorizar_pregunta(p) for p in preguntas_sel]
                    st.session_state.simulador_activo = True
                    st.session_state.indice_actual = 0
                    st.session_state.respuestas_usuario = {}
                    st.session_state.mostrar_resultados = False
                    st.session_state.historial_examen_registrado = False
                    
                    # Guardar configuración del examen
                    st.session_state.modo_examen = modo_examen
                    st.session_state.tiempo_limite = tiempo_minutos * 60
                    st.session_state.tiempo_inicio = time.time()
                    st.session_state.timer_activo = (modo_examen == "Examen")
                st.rerun()
        
        # ========================================
        # PANTALLA 2: VISTA DE CORRECCIÓN
        # ========================================
        elif st.session_state.mostrar_resultados:
            res = st.session_state.resultado_final
            if res is None:
                res = calcular_resultado(
                    st.session_state.preguntas_simulador,
                    st.session_state.respuestas_usuario,
                    contar_no_respondidas_como_incorrectas=st.session_state.get("timer_activo", False),
                )
                st.session_state.resultado_final = res
                _registrar_historial()

            st.markdown("## 🎯 Resultados del Examen")
            st.markdown('<div id="reporte-topo"></div>', unsafe_allow_html=True)
            
            # La métrica de no respondidas solo ocupa columna si hay alguna
            # (en modo examen son 0: cuentan como incorrectas).
            hay_no_respondidas = res['no_respondidas'] > 0
            cols_metricas = st.columns(5 if hay_no_respondidas else 4)

            with cols_metricas[0]:
                st.metric("✅ Correctas", res['correctas'], delta=f"{res['correctas']}/{res['total']}")
            with cols_metricas[1]:
                st.metric("🟡 Parciales", res['parciales'])
            with cols_metricas[2]:
                st.metric("❌ Incorrectas", res['incorrectas'])
            if hay_no_respondidas:
                with cols_metricas[3]:
                    st.metric("⬜ No respondidas", res['no_respondidas'])
                with cols_metricas[4]:
                    st.metric("📊 Puntuación", f"{res['porcentaje']:.0f}%")
            else:
                with cols_metricas[3]:
                    st.metric("📊 Puntuación", f"{res['porcentaje']:.0f}%")
            
            if res['porcentaje'] >= 80:
                st.success("🎉 ¡Excelente! Has aprobado con nota alta")
            elif res['porcentaje'] >= 60:
                st.warning("😊 Aprobado - Puedes mejorar")
            else:
                st.error("😔 No aprobado - Sigue estudiando")

            # Mini-resumen de reiteradas: cuántas preguntas de ESTE examen
            # acumulan ya 2+ fallos en el historial completo.
            try:
                claves_reiteradas = {r["clave"] for r in resumen_reiteradas(cargar_historial(ARCHIVO_HISTORIAL), 2)}
                claves_examen = {clave_pregunta(p) for p in st.session_state.preguntas_simulador}
                reiteradas_examen = claves_examen & claves_reiteradas
                if reiteradas_examen:
                    st.info(f"🔁 {len(reiteradas_examen)} pregunta(s) de este examen ya se fallan de "
                            f"forma reiterada: repásalas en la pestaña **🔁 Sección Errores Reiterados**.")
            except OSError:
                pass
            
            st.markdown("---")
            st.markdown("### 📋 Revisión Detallada")
            
            col_filtro1, col_filtro2 = st.columns([3, 1])
            
            with col_filtro1:
                filtro = st.radio(
                    "Mostrar:",
                    ["Todas las preguntas", "Solo incorrectas", "Solo correctas", "Solo parciales"],
                    horizontal=True
                )
            
            with col_filtro2:
                st.write("")
                if st.button("🔄 Nuevo Examen", type="primary", use_container_width=True):
                    st.session_state.simulador_activo = False
                    st.session_state.mostrar_resultados = False
                    st.session_state.indice_actual = 0
                    st.session_state.respuestas_usuario = {}
                    st.rerun()
            
            st.markdown("---")
            
            # Preparar lista filtrada
            preguntas_revision = []
            for i, preg in enumerate(st.session_state.preguntas_simulador):
                resp_usuario = st.session_state.respuestas_usuario.get(i, [])
                if not isinstance(resp_usuario, list):
                    resp_usuario = [resp_usuario] if resp_usuario else []
                
                correctas_preg = set(preg["correctas"])
                respuestas_set = set(resp_usuario)
                
                if respuestas_set == correctas_preg:
                    estado = "correcta"
                elif respuestas_set.intersection(correctas_preg):
                    estado = "parcial"
                else:
                    estado = "incorrecta"
                
                if filtro == "Todas las preguntas":
                    preguntas_revision.append((i, preg, resp_usuario, estado))
                elif filtro == "Solo incorrectas" and estado == "incorrecta":
                    preguntas_revision.append((i, preg, resp_usuario, estado))
                elif filtro == "Solo correctas" and estado == "correcta":
                    preguntas_revision.append((i, preg, resp_usuario, estado))
                elif filtro == "Solo parciales" and estado == "parcial":
                    preguntas_revision.append((i, preg, resp_usuario, estado))
            
            if not preguntas_revision:
                st.info(f"ℹ️ No hay preguntas con el filtro '{filtro}'")
            else:
                st.caption(f"📊 {len(preguntas_revision)} pregunta(s)")
                
                for idx_rev, (idx_orig, preg, resp_usuario, estado) in enumerate(preguntas_revision):
                    
                    st.markdown(f'<div id="pregunta-{idx_orig}"></div>', unsafe_allow_html=True)
                    st.markdown("---")
                    # El id viene del banco importado: se escapa porque estas
                    # cabeceras usan unsafe_allow_html (XSS si viene malicioso).
                    id_html = html.escape(str(preg.get('id', '?')))
                    
                    if estado == "correcta":
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 16px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);'>
                            <h3 style='margin: 0; font-size: 20px;'>✅ Pregunta {idx_orig + 1} - CORRECTA <span style='font-size:14px;font-weight:500;opacity:0.75;'>(#{id_html})</span></h3>
                        </div>
                        """, unsafe_allow_html=True)
                    elif estado == "parcial":
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 16px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);'>
                            <h3 style='margin: 0; font-size: 20px;'>🟡 Pregunta {idx_orig + 1} - PARCIAL <span style='font-size:14px;font-weight:500;opacity:0.75;'>(#{id_html})</span></h3>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; padding: 16px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);'>
                            <h3 style='margin: 0; font-size: 20px;'>❌ Pregunta {idx_orig + 1} - INCORRECTA <span style='font-size:14px;font-weight:500;opacity:0.75;'>(#{id_html})</span></h3>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    col_pregunta, col_respuesta = st.columns([1, 1])
                    
                    with col_pregunta:
                        st.markdown("#### 📝 Enunciado")
                        
                        imagen_path = resolve_image_path(preg.get("imagen"))
                        if imagen_path and os.path.exists(imagen_path):
                            st.image(imagen_path, use_container_width=True)
                            st.markdown("---")
                        elif preg.get("imagen"):
                            st.warning("⚠️ Imagen no encontrada")
                        
                        st.markdown(f"**{preg['pregunta']}**")
                        st.markdown("---")
                        st.markdown("##### Opciones:")
                        
                        for opcion in preg["opciones"]:
                            letra = opcion[0]
                            texto = opcion[3:].strip() if len(opcion) > 3 else opcion
                            # Escapado obligatorio: el texto viene del banco
                            # (importable por JSON/ZIP) y va inline en HTML.
                            letra_html = html.escape(letra)
                            texto_html = html.escape(texto)
                            
                            bg_correcta = "#d1fae5"
                            color_correcta = "#065f46"
                            border_correcta = "#10b981"
                            bg_incorrecta = "#fee2e2"
                            color_incorrecta = "#991b1b"
                            border_incorrecta = "#ef4444"
                            bg_default = "#f9fafb"
                            color_default = "#4b5563"
                            border_default = "#d1d5db"
                            
                            if letra in preg["correctas"]:
                                st.markdown(f"""
                                <div style='background: {bg_correcta}; border-left: 4px solid {border_correcta}; padding: 12px; margin-bottom: 8px; border-radius: 6px;'>
                                    <strong style='color: {color_correcta};'>{letra_html}) {texto_html}</strong>
                                    <span style='color: {color_correcta}; font-weight: 600;'> ← ✅ CORRECTA</span>
                                </div>
                                """, unsafe_allow_html=True)
                            elif letra in resp_usuario:
                                st.markdown(f"""
                                <div style='background: {bg_incorrecta}; border-left: 4px solid {border_incorrecta}; padding: 12px; margin-bottom: 8px; border-radius: 6px;'>
                                    <span style='color: {color_incorrecta};'>{letra_html}) {texto_html}</span>
                                    <span style='color: {color_incorrecta}; font-weight: 600;'> ← ❌ Tu respuesta</span>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown(f"""
                                <div style='background: {bg_default}; border-left: 4px solid {border_default}; padding: 12px; margin-bottom: 8px; border-radius: 6px;'>
                                    <span style='color: {color_default};'>{letra_html}) {texto_html}</span>
                                </div>
                                """, unsafe_allow_html=True)
                    
                    with col_respuesta:
                        st.markdown("#### 🎯 Corrección")
                        
                        st.markdown("**Tu respuesta:**")
                        if resp_usuario:
                            if estado == "correcta":
                                st.success(f"✅ {', '.join(resp_usuario)}")
                            elif estado == "parcial":
                                st.warning(f"🟡 {', '.join(resp_usuario)}")
                            else:
                                st.error(f"❌ {', '.join(resp_usuario)}")
                        else:
                            st.error("❌ No respondida")
                        
                        st.markdown("---")
                        st.markdown("**Respuesta correcta:**")
                        st.success(f"✅ {', '.join(preg['correctas'])}")
                        
                        st.markdown("---")
                        st.markdown("**📚 Explicación:**")
                        
                        if len(preg['correctas']) > 1:
                            st.info(f"Requiere {len(preg['correctas'])} opciones")
                        else:
                            st.info("Respuesta única")
                
                # === PANEL DE NAVEGACIÓN FLOTANTE ===
                badges_nav = ""
                for idx_rev, (idx_orig, preg, resp_usuario, estado) in enumerate(preguntas_revision):
                    color = "#10b981" if estado == "correcta" else "#f59e0b" if estado == "parcial" else "#ef4444"
                    badges_nav += f'<a href="#pregunta-{idx_orig}" class="flotbadge" style="background:{color};" title="P{idx_orig+1} - {estado.upper()}">{idx_orig+1}</a>'

                ultimo_idx = preguntas_revision[-1][0] if preguntas_revision else 0

                nav_html = f"""
                <style>
                html {{ scroll-behavior: smooth; }}
                .flotnav{{position:fixed!important;bottom:20px!important;right:20px!important;z-index:99999!important;
                background:rgba(17,24,39,0.95);border-radius:14px;padding:12px;
                box-shadow:0 4px 24px rgba(0,0,0,0.4);max-height:320px;
                overflow-y:auto;font-family:sans-serif;min-width:60px;
                transition:opacity 0.3s, transform 0.3s;}}
                .flotnav-hide:checked ~ .flotnav{{opacity:0;pointer-events:none;transform:translateY(20px);}}
                .flotnav-toggle{{position:fixed!important;bottom:20px!important;right:20px!important;z-index:100000!important;
                background:#ef4444;border:none;border-radius:50%;width:40px;height:40px;
                cursor:pointer;color:white;font-weight:700;font-size:18px;display:none;
                box-shadow:0 2px 12px rgba(239,68,68,0.5);line-height:40px;text-align:center;}}
                .flotnav-hide:checked ~ .flotnav-toggle{{display:block;}}
                .flotbadge{{display:inline-block;width:28px;height:28px;line-height:28px;text-align:center;
                border-radius:50%;color:#fff;font-size:11px;font-weight:700;margin:2px;cursor:pointer;
                transition:transform 0.15s;text-decoration:none;}}
                .flotbadge:hover{{transform:scale(1.35);filter:brightness(1.2);}}
                .flotnav-btn{{display:block;width:100%;padding:7px;margin:4px 0;border:none;border-radius:8px;
                cursor:pointer;font-weight:700;font-size:13px;text-align:center;color:#fff;text-decoration:none;}}
                .flotnav-top{{background:linear-gradient(135deg,#3b82f6,#2563eb);}}
                .flotnav-bottom{{background:linear-gradient(135deg,#6b7280,#4b5563);}}
                .flotnav-label{{color:#9ca3af;font-size:10px;text-align:center;margin:4px 0 2px;}}
                .flotnav-close{{position:absolute;top:6px;right:10px;background:none;border:none;
                color:#9ca3af;font-size:18px;cursor:pointer;padding:0;line-height:1;z-index:1;}}
                .flotnav-close:hover{{color:#ef4444;}}
                </style>
                <input type="checkbox" id="flotnav-hide" class="flotnav-hide" style="display:none;">
                <label for="flotnav-hide" class="flotnav-toggle" title="Mostrar panel de navegacion">&#9776;</label>
                <div class="flotnav">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                        <a href="#reporte-topo" class="flotnav-btn flotnav-top" style="flex:1;margin-right:8px;">&#11014; Inicio</a>
                        <label for="flotnav-hide" class="flotnav-close" title="Ocultar panel">&#10005;</label>
                    </div>
                    <div class="flotnav-label">Preguntas</div>
                    <div style="text-align:center;">{badges_nav}</div>
                    <a href="#pregunta-{ultimo_idx}" class="flotnav-btn flotnav-bottom">&#11015; Fin</a>
                </div>
                """
                st.markdown(nav_html, unsafe_allow_html=True)
                
                st.markdown("---")
                col_f1, col_f2, col_f3 = st.columns([1, 2, 1])
                with col_f2:
                    if st.button("🔄 Nuevo Examen", type="primary", use_container_width=True, key="final"):
                        st.session_state.simulador_activo = False
                        st.session_state.mostrar_resultados = False
                        st.session_state.indice_actual = 0
                        st.session_state.respuestas_usuario = {}
                        st.rerun()
        
        # ========================================
        # PANTALLA 3: SIMULADOR CON AVISO DESTACADO
        # ========================================
        else:
            idx = st.session_state.indice_actual
            preg = st.session_state.preguntas_simulador[idx]
            total = len(st.session_state.preguntas_simulador)
            
            # === TIMER EN TIEMPO REAL ===
            # Con st.fragment (Streamlit 1.54+) solo este bloque se re-ejecuta
            # cada segundo; sin fragment, el fallback es st_autorefresh (o
            # sleep+rerun), que re-ejecuta la pagina entera.
            if st.session_state.get("timer_activo", False):

                def _cuerpo_timer(idx_q, total_q):
                    tiempo_inicio_timer = st.session_state.tiempo_inicio
                    tiempo_limite_timer = st.session_state.tiempo_limite

                    tiempo_transcurrido = time.time() - tiempo_inicio_timer
                    tiempo_restante = tiempo_limite_timer - tiempo_transcurrido

                    if tiempo_restante <= 0:
                        st.error("⏰ ¡Tiempo agotado!")
                        st.session_state.resultado_final = calcular_resultado(
                            st.session_state.preguntas_simulador,
                            st.session_state.respuestas_usuario,
                            contar_no_respondidas_como_incorrectas=True,
                        )
                        st.session_state.mostrar_resultados = True
                        _registrar_historial()
                        # scope="app": hay que salir de la pantalla de examen
                        # entera, no solo del fragmento del timer.
                        if ST_FRAGMENT_AVAILABLE:
                            st.rerun(scope="app")
                        st.rerun()

                    minutos = int(tiempo_restante // 60)
                    segundos = int(tiempo_restante % 60)

                    # Determinar color según el tiempo restante
                    if tiempo_restante < 60:
                        timer_color = "#ef4444"
                        timer_bg = "#fef2f2"
                        timer_border = "#dc2626"
                    elif tiempo_restante < 300:
                        timer_color = "#f59e0b"
                        timer_bg = "#fffbeb"
                        timer_border = "#d97706"
                    else:
                        timer_color = "#059669"
                        timer_bg = "#f0fdf4"
                        timer_border = "#047857"

                    st.markdown(f"""
                    <div style="
                        background: {timer_bg};
                        border: 4px solid {timer_border};
                        border-radius: 16px;
                        padding: 24px;
                        margin: 10px 0;
                        text-align: center;
                        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
                    ">
                        <div style="font-size: 18px; color: #6b7280; font-weight: 700; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 3px;">
                            ⏱️ TIEMPO RESTANTE
                        </div>
                        <div style="
                            font-size: 72px;
                            font-weight: 900;
                            color: {timer_color};
                            font-family: 'Courier New', monospace;
                            letter-spacing: 8px;
                            text-shadow: 3px 3px 6px rgba(0,0,0,0.2);
                        ">
                            {minutos:02d}:{segundos:02d}
                        </div>
                        <div style="
                            background: #e5e7eb;
                            border-radius: 12px;
                            height: 16px;
                            margin-top: 20px;
                            overflow: hidden;
                        ">
                            <div style="
                                background: {timer_color};
                                height: 100%;
                                width: {(tiempo_restante / tiempo_limite_timer) * 100}%;
                                border-radius: 12px;
                                transition: width 1s linear;
                            "></div>
                        </div>
                        <div style="margin-top: 12px; font-size: 14px; color: #6b7280;">
                            Pregunta {idx_q + 1} de {total_q}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if tiempo_restante < 60:
                        st.warning(f"⚠️ ¡Solo quedan {int(tiempo_restante)} segundos!")

                if ST_FRAGMENT_AVAILABLE:
                    @st.fragment(run_every=1)
                    def bloque_timer(idx_q, total_q):
                        _cuerpo_timer(idx_q, total_q)

                    bloque_timer(idx, total)
                else:
                    def bloque_timer(idx_q, total_q):
                        _cuerpo_timer(idx_q, total_q)
                        # Refresco de pagina completa: autorefresh si está, o
                        # sleep+rerun como ultimo recurso.
                        if STREAMLIT_AUTOREFRESH_AVAILABLE:
                            st_autorefresh(interval=1000, limit=None, key="timer_refresh")
                        else:
                            st.warning("⚠️ Instala streamlit-autorefresh para timer fluido: pip install streamlit-autorefresh")
                            time.sleep(1)
                            st.rerun()

                    bloque_timer(idx, total)
            else:
                st.progress((idx + 1) / total, text=f"📍 Pregunta {idx + 1} de {total}")
            
            st.markdown(f"### {preg['pregunta']}")
            
            imagen_path = resolve_image_path(preg.get("imagen"))
            if imagen_path and os.path.exists(imagen_path):
                with st.expander("🔍 Ver imagen"):
                    st.image(imagen_path, use_container_width=True)
            elif preg.get("imagen"):
                st.warning("⚠️ Imagen no encontrada")
            
            st.markdown("---")
            
            num_correctas = len(preg.get("correctas", []))
            es_multiple = num_correctas > 1
            
            # ✅ AVISO ULTRA VISIBLE PARA SELECCIÓN MÚLTIPLE
            if es_multiple:
                st.markdown(f"""
                <div style='
                    background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
                    border: 4px solid #d97706;
                    border-radius: 12px;
                    padding: 20px;
                    margin: 20px 0;
                    box-shadow: 0 8px 16px rgba(245, 158, 11, 0.4);
                    animation: pulse 2s infinite;
                '>
                    <div style='display: flex; align-items: center; gap: 16px;'>
                        <div style='
                            width: 60px;
                            height: 60px;
                            background: white;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 32px;
                            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                        '>
                            ⚠️
                        </div>
                        <div style='flex: 1;'>
                            <div style='color: white; font-size: 22px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;'>
                                ⚠️ ATENCIÓN: SELECCIÓN MÚLTIPLE ⚠️
                            </div>
                            <div style='color: #ffffff; font-size: 18px; font-weight: 600;'>
                                Esta pregunta requiere seleccionar <strong style='font-size: 24px; background: white; color: #f59e0b; padding: 4px 12px; border-radius: 6px;'>{num_correctas}</strong> respuestas correctas
                            </div>
                        </div>
                    </div>
                </div>
                
                <style>
                    @keyframes pulse {{
                        0%, 100% {{
                            transform: scale(1);
                            box-shadow: 0 8px 16px rgba(245, 158, 11, 0.4);
                        }}
                        50% {{
                            transform: scale(1.02);
                            box-shadow: 0 12px 24px rgba(245, 158, 11, 0.6);
                        }}
                    }}
                </style>
                """, unsafe_allow_html=True)

                # 🚫 AVISO DE BLOQUEO: se activa al intentar avanzar con la
                # selección incompleta (o en exceso) en una pregunta múltiple.
                if st.session_state.pop("aviso_bloqueo_multiple", False):
                    marcadas_bloqueo = [
                        op[0] for op in preg["opciones"]
                        if st.session_state.get(f"opt_{idx}_{op[0]}", False)
                    ]
                    if len(marcadas_bloqueo) < num_correctas:
                        detalle_bloqueo = (
                            f"Has marcado <strong>{len(marcadas_bloqueo)}</strong> de "
                            f"<strong>{num_correctas}</strong> respuestas. Debes marcar "
                            f"<strong>{num_correctas - len(marcadas_bloqueo)}</strong> más "
                            "para poder continuar."
                        )
                    else:
                        detalle_bloqueo = (
                            f"Has marcado <strong>{len(marcadas_bloqueo)}</strong> respuestas, "
                            f"pero esta pregunta requiere exactamente <strong>{num_correctas}</strong>. "
                            "Desmarca las que sobren para poder continuar."
                        )
                    st.markdown(f"""
                    <div style='
                        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                        border: 4px solid #b91c1c;
                        border-radius: 12px;
                        padding: 20px;
                        margin: 20px 0;
                        box-shadow: 0 8px 16px rgba(239, 68, 68, 0.4);
                    '>
                        <div style='display: flex; align-items: center; gap: 16px;'>
                            <div style='
                                width: 60px;
                                height: 60px;
                                background: white;
                                border-radius: 50%;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-size: 32px;
                                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                            '>
                                🚫
                            </div>
                            <div style='flex: 1;'>
                                <div style='color: white; font-size: 22px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;'>
                                    🚫 No puedes continuar aún 🚫
                                </div>
                                <div style='color: #ffffff; font-size: 18px; font-weight: 600;'>
                                    Esta pregunta requiere exactamente <strong style='font-size: 24px; background: white; color: #dc2626; padding: 4px 12px; border-radius: 6px;'>{num_correctas}</strong> respuestas. {detalle_bloqueo}
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                # Aviso para respuesta única (más discreto pero visible)
                st.markdown(f"""
                <div style='
                    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                    border: 3px solid #1d4ed8;
                    border-radius: 10px;
                    padding: 16px;
                    margin: 16px 0;
                    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
                '>
                    <div style='display: flex; align-items: center; gap: 12px;'>
                        <div style='
                            width: 48px;
                            height: 48px;
                            background: white;
                            border-radius: 50%;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 24px;
                        '>
                            ℹ️
                        </div>
                        <div style='flex: 1;'>
                            <div style='color: white; font-size: 18px; font-weight: 700;'>
                                📌 Selecciona UNA única respuesta correcta
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Mostrar opciones con checkboxes - Streamlit maneja el estado automáticamente
            st.markdown("### Selecciona tu respuesta:")

            opciones_seleccionadas = {}

            for i, opcion in enumerate(preg["opciones"]):
                letra = opcion[0]
                texto = opcion[3:].strip() if len(opcion) > 3 else opcion

                # El checkbox mantiene su estado automáticamente vía session_state
                opciones_seleccionadas[letra] = st.checkbox(
                    f"✅ Opción {letra}",
                    key=f"opt_{idx}_{letra}"
                )

                # Mostrar card visual basada en el estado ACTUAL del checkbox
                if opciones_seleccionadas[letra]:
                    st.markdown(f"""
                    <div style='
                        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                        border: 3px solid #047857;
                        border-radius: 12px;
                        padding: 16px;
                        margin-bottom: 12px;
                        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
                    '>
                        <div style='display: flex; align-items: center; gap: 12px;'>
                            <div style='
                                width: 48px;
                                height: 48px;
                                border-radius: 50%;
                                background: white;
                                color: #10b981;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-weight: bold;
                                font-size: 24px;
                            '>
                                ✓
                            </div>
                            <div style='flex: 1; color: white;'>
                                <div style='font-size: 14px; font-weight: 800; text-transform: uppercase;'>
                                    OPCIÓN {letra} SELECCIONADA
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div style='
                        background: white;
                        border: 2px solid #e5e7eb;
                        border-radius: 12px;
                        padding: 16px;
                        margin-bottom: 12px;
                    '>
                        <div style='display: flex; align-items: center; gap: 12px;'>
                            <div style='
                                width: 48px;
                                height: 48px;
                                border-radius: 50%;
                                background: #9ca3af;
                                color: white;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-weight: bold;
                                font-size: 22px;
                            '>
                                {letra}
                            </div>
                            <div style='flex: 1;'>
                                <div style='font-size: 12px; color: #6b7280; text-transform: uppercase; font-weight: 600;'>
                                    Opción {letra}
                                </div>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # Mostrar texto de la opción
                if '\n' in texto or len(texto) > 70:
                    st.text(texto)
                else:
                    st.markdown(texto)

                st.markdown("---")

            # Guardar estado en session_state (sin rerun - se actualiza solo)
            respuestas_actuales = [letra for letra, seleccionada in opciones_seleccionadas.items() if seleccionada]
            if respuestas_actuales:
                st.session_state.respuestas_usuario[idx] = respuestas_actuales
                if es_multiple:
                    st.success(f"✓ Has marcado {len(respuestas_actuales)} de {num_correctas} opciones: {', '.join(respuestas_actuales)}")
                else:
                    st.success(f"✓ Seleccionada: {respuestas_actuales[0]}")
            else:
                if idx in st.session_state.respuestas_usuario:
                    del st.session_state.respuestas_usuario[idx]
            
            st.markdown("---")
            
            # Botones de navegación (estos SÍ pueden estar en un form o como botones normales)
            col1, col2, col3 = st.columns([1, 1, 1])
            
            with col1:
                if idx > 0:
                    if st.button("⬅ Anterior", use_container_width=True):
                        st.session_state.indice_actual -= 1
                        st.rerun()

            with col2:
                respondidas = len(st.session_state.respuestas_usuario)
                st.metric("📊", f"{respondidas}/{total}")

            with col3:
                if idx < total - 1:
                    if st.button("Siguiente ➡", type="primary", use_container_width=True):
                        # En preguntas de respuesta múltiple no se puede avanzar
                        # hasta marcar exactamente el total de respuestas requeridas.
                        if es_multiple and len(respuestas_actuales) != num_correctas:
                            st.session_state.aviso_bloqueo_multiple = True
                            st.rerun()
                        st.session_state.indice_actual += 1
                        st.rerun()
                else:
                    if st.button("🏁 Finalizar", type="primary", use_container_width=True):
                        if es_multiple and len(respuestas_actuales) != num_correctas:
                            st.session_state.aviso_bloqueo_multiple = True
                            st.rerun()
                        with st.spinner("📊 Calculando tus resultados finales..."):
                            st.session_state.resultado_final = calcular_resultado(
                                st.session_state.preguntas_simulador,
                                st.session_state.respuestas_usuario,
                                contar_no_respondidas_como_incorrectas=st.session_state.get("timer_activo", False),
                            )
                            st.session_state.mostrar_resultados = True
                            _registrar_historial()
                        st.rerun()

# ========================================
# PESTAÑA 5: SECCIÓN ERRORES REITERADOS
# ========================================
elif pestana_seleccionada == "🔁 Sección Errores Reiterados":
    st.header("🔁 Sección Errores Reiterados")
    st.caption("Cada examen terminado registra un fallo por pregunta no acertada "
               "(incorrecta, parcial o sin responder). Aquí quedan las que se "
               "repiten para poder repasarlas y comprobarlas.")

    historial_actual = cargar_historial(ARCHIVO_HISTORIAL)

    col_ctrl1, col_ctrl2 = st.columns(2)
    with col_ctrl1:
        umbral_reiteradas = st.slider(
            "Mínimo de fallos para considerar una pregunta reiterada",
            min_value=1, max_value=10, value=2, step=1, key="reiteradas_umbral",
        )
    with col_ctrl2:
        ventana_opcion = st.selectbox(
            "Ventana de tiempo",
            ["Todo el historial", "Últimos 7 días", "Últimos 30 días", "Últimos 90 días"],
            key="reiteradas_ventana",
        )
    dias_ventana = {"Todo el historial": None, "Últimos 7 días": 7,
                    "Últimos 30 días": 30, "Últimos 90 días": 90}[ventana_opcion]

    resumen = resumen_reiteradas(historial_actual, umbral_reiteradas, dias=dias_ventana)
    con_fallos = [d for d in historial_actual.get("preguntas", {}).values()
                  if any(e.get("resultado") == "fallo" for e in d.get("eventos", []))]

    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.metric("📝 Exámenes registrados", historial_actual.get("examenes", 0))
    with col_m2:
        st.metric("❌ Preguntas con fallos", len(con_fallos))
    with col_m3:
        st.metric("🔁 Reiteradas ahora", len(resumen))

    st.markdown("---")

    if historial_actual.get("examenes", 0) == 0:
        st.info("ℹ️ Aún no hay exámenes registrados. Termina un examen en la pestaña "
                "🎮 Simulador y las preguntas que falles quedarán registradas aquí.")
    elif not resumen:
        st.success(f"✅ Ninguna pregunta alcanza {umbral_reiteradas} fallos en la ventana seleccionada. ¡Bien!")
    else:
        claves_banco = {clave_pregunta(p) for p in load_questions()}

        def _fecha_humana(texto_iso):
            try:
                from datetime import datetime as _dt
                return _dt.strptime(texto_iso, "%Y-%m-%dT%H:%M:%S").strftime("%d/%m/%Y %H:%M")
            except (TypeError, ValueError):
                return "—"

        st.caption(f"📊 {len(resumen)} pregunta(s) reiterada(s) — ordenadas por nº de fallos")
        for r in resumen:
            enunciado_html = html.escape(r["enunciado"] or "(sin enunciado)")
            tag_html = html.escape(r["tag"] or "Sin tag")
            correctas_txt = ", ".join(r["correctas"]) if r["correctas"] else "?"
            fuera_banco = "" if r["clave"] in claves_banco else " — <em>ya no está en el banco</em>"
            ultimo_fallo_humano = _fecha_humana(r["ultimo_fallo"])
            st.markdown(f"""
            <div style='
                background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
                border: 3px solid #fca5a5;
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 12px;
            '>
                <div style='font-size: 16px; font-weight: 700; color: #1f2937; margin-bottom: 8px;'>
                    ❌ {enunciado_html}{fuera_banco}
                </div>
                <div style='font-size: 13px; color: #6b7280;'>
                    Tag: <strong>{tag_html}</strong> · Fallos: <strong style='color: #dc2626;'>{r['fallos']}</strong>
                    / {r['intentos']} intentos ({r['tasa_fallo']:.0f}% de fallo)
                    · Último fallo: {ultimo_fallo_humano}
                </div>
                <div style='font-size: 13px; color: #059669; margin-top: 4px;'>
                    ✅ Respuesta(s) correcta(s): <strong>{html.escape(correctas_txt)}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    with st.expander("⚠️ Zona peligrosa — reiniciar historial"):
        st.warning("El reinicio borra TODO el historial de fallos acumulado "
                   "(incluidas las estadísticas de preguntas reiteradas). Esta acción no se puede deshacer.")
        confirmar_reset = st.checkbox("Estoy seguro de que quiero borrar todo el historial", key="confirmar_reset_historial")
        if st.button("🗑️ Reiniciar historial a cero", type="primary", disabled=not confirmar_reset):
            try:
                os.remove(ARCHIVO_HISTORIAL)
            except FileNotFoundError:
                pass
            except OSError:
                st.error("No se pudo borrar el archivo del historial.")
                st.stop()
            st.toast("🗑️ Historial reiniciado a cero", icon="✅")
            st.rerun()
