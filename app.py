import streamlit as st
import numpy as np
from PIL import Image
import json
import os
import sys
import time
import random
import copy
import re
import shutil
import zipfile
import io

# Check for st.fragment support (Streamlit 1.54+)
ST_FRAGMENT_AVAILABLE = hasattr(st, 'fragment')

from src.paths import get_app_dir, get_data_dir
from src.api_key_manager import save_api_key, load_api_key, has_api_key

# ✅ CONFIGURACIÓN PROTEGIDA DE OPENCV
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "0"
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["MPLBACKEND"] = "Agg"

try:
    import cv2
    cv2.setNumThreads(1)
    OPENCV_AVAILABLE = True
except:
    OPENCV_AVAILABLE = False

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except:
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
def export_questions_to_zip(preguntas, data_dir):
    """
    Exporta preguntas e imágenes a un archivo ZIP.
    """
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        preguntas_export = []
        for p in preguntas:
            p_exp = p.copy()
            if p_exp.get("imagen"):
                p_exp["imagen"] = get_relative_image_path(p_exp["imagen"])
            preguntas_export.append(p_exp)
        
        json_data = json.dumps(preguntas_export, indent=4, ensure_ascii=False)
        zip_file.writestr('preguntas.json', json_data)
        
        for p in preguntas:
            if p.get("imagen"):
                abs_path = resolve_image_path(p.get("imagen"))
                if abs_path and os.path.exists(abs_path):
                    img_filename = os.path.basename(abs_path)
                    zip_file.write(abs_path, f'imagenes/{img_filename}')
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def import_questions_from_zip(zip_bytes, data_dir):
    """
    Importa preguntas e imágenes desde un archivo ZIP.
    """
    import tempfile
    
    preguntas_importadas = []
    
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
            zip_file.extractall(temp_dir)
        
        json_path = os.path.join(temp_dir, 'preguntas.json')
        if not os.path.exists(json_path):
            return {"error": "El ZIP no contiene preguntas.json"}
        
        with open(json_path, 'r', encoding='utf-8') as f:
            preguntas_importadas = json.load(f)
        
        img_source_dir = os.path.join(temp_dir, 'imagenes')
        if os.path.exists(img_source_dir):
            for img_file in os.listdir(img_source_dir):
                src_path = os.path.join(img_source_dir, img_file)
                if os.path.isfile(src_path):
                    dst_path = os.path.join(CARPETA_IMAGENES, img_file)
                    shutil.copy2(src_path, dst_path)
    
    for p in preguntas_importadas:
        if p.get("imagen"):
            p["imagen"] = get_relative_image_path(p["imagen"])
    
    return preguntas_importadas


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
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_questions(preguntas_actualizadas):
    with open(ARCHIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(preguntas_actualizadas, f, indent=4, ensure_ascii=False)
    load_questions.clear()

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
        # Match: "A) Texto", "A. Texto", "A - Texto", "A: Texto"
        match = re.match(r"^([A-Fa-f])\s*[\).\-:]\s*(.*)", opcion)
        if match:
            letra_original = match.group(1).upper()
            texto = match.group(2).strip()
        else:
            # Fallback: usar el texto completo si no hay formato estándar
            continue
        
        if texto:
            pares_originales.append((letra_original, texto))
    
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

# --- PESTAÑAS PRINCIPALES CON ESTADO ---
opciones_pestanas = ["✍️ Ingesta Manual", "📸 Extracción OCR", "📊 Ver Preguntas", "🎮 Simulador"]

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
                    st.balloons()
                    
                    limpiar_formulario_manual()
                    time.sleep(1)
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
            
            temp_path = "temp_capture_ocr.png"
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
                    
                    respuestas = resultado_texto.get("respuestas", [])
                    opciones_guardadas = []
                    correctas_marcadas = []
                    
                    for idx, opcion in enumerate(respuestas):
                        letra = opcion[0] if opcion else chr(65 + idx)
                        texto_opcion = opcion[3:].strip() if len(opcion) > 3 else opcion
                        
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
                                st.balloons()
                                st.toast("✅ Pregunta guardada exitosamente!", icon="🎉")
                                
                                del st.session_state.resultado_ocr
                                if os.path.exists(temp_path):
                                    os.remove(temp_path)
                                
                                time.sleep(1)
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

            try:
                if es_zip:
                    contenido = import_questions_from_zip(archivo_importar.getvalue(), DATA_DIR)
                else:
                    contenido = json.load(archivo_importar)
                
                if isinstance(contenido, list) and len(contenido) > 0:
                    if all(isinstance(p, dict) and "pregunta" in p and "opciones" in p for p in contenido):
                        st.success(f"✅ Archivo válido: {len(contenido)} preguntas detectadas")
                        
                        with st.expander("👀 Vista previa de las preguntas"):
                            for i, p in enumerate(contenido[:5]):
                                st.markdown(f"**{i+1}.** {p['pregunta'][:80]}...")
                            if len(contenido) > 5:
                                st.caption(f"... y {len(contenido) - 5} preguntas más")
                        
                        if st.button("✅ Importar todas las preguntas", type="primary"):
                            with st.spinner("📥 Importando..."):
                                save_questions(contenido)
                            st.success(f"🎉 ¡{len(contenido)} preguntas importadas!")
                            st.toast("✅ Importación exitosa!", icon="🎉")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error("❌ El archivo no tiene el formato correcto")
                else:
                    st.error("❌ El archivo está vacío")
            except json.JSONDecodeError:
                st.error("❌ El archivo no es un JSON válido")
            except Exception as e:
                st.error(f"❌ Error al importar: {str(e)}")

    else:
        st.success(f"✅ {len(preguntas)} pregunta(s) guardada(s)")
        
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
                zip_data = export_questions_to_zip(preguntas, DATA_DIR)
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
            
            if contenido and isinstance(contenido, list) and len(contenido) > 0:
                if all(isinstance(p, dict) and "pregunta" in p and "opciones" in p for p in contenido):
                    st.success(f"✅ Archivo válido: {len(contenido)} preguntas")
                    
                    col_merge, col_replace = st.columns(2)
                    
                    with col_merge:
                        if st.button("➕ Añadir", use_container_width=True):
                            with st.spinner("📥 Añadiendo..."):
                                max_id = max((p.get("id", 0) for p in preguntas), default=0)
                                for idx, p_nueva in enumerate(contenido):
                                    p_nueva["id"] = max_id + idx + 1
                                preguntas.extend(contenido)
                                save_questions(preguntas)
                            st.toast(f"✅ {len(contenido)} preguntas añadidas!", icon="✅")
                            time.sleep(1)
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
                                    save_questions(contenido)
                                st.session_state.confirmar_reemplazo = False
                                st.toast("✅ Base de datos reemplazada!", icon="🔄")
                                time.sleep(1)
                                st.rerun()
                        
                        with col2:
                            if st.button("❌ Cancelar"):
                                st.session_state.confirmar_reemplazo = False
                                st.rerun()
            elif contenido:
                st.error("❌ Formato de archivo inválido")
        
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
            def matches_tag(p, tags):
                t = p.get("tag", "")
                for tag_sel in tags:
                    if tag_sel == "Sin tag" and not t:
                        return True
                    elif tag_sel == t:
                        return True
                return False
            preguntas_filtradas = [p for p in preguntas_filtradas if matches_tag(p, tags_filtrar)]
        if buscar.strip() or tags_filtrar:
            st.caption(f"🔍 {len(preguntas_filtradas)} resultado(s)")
        
        for q in preguntas_filtradas:
            p_mostrar = aleatorizar_pregunta(q) if mostrar_aleatorio else q
            
            with st.expander(f"❓ #{q['id']}: {q['pregunta'][:70]}..."):
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
                
                if st.button(f"🗑️ Eliminar", key=f"del_{q['id']}"):
                    preguntas.remove(q)
                    save_questions(preguntas)
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
            
            tags_simulador = sorted(set(p.get("tag", "") for p in preguntas if p.get("tag", "")))
            if tags_simulador:
                tags_seleccionados = st.multiselect(
                    "🏷️ Seleccionar tags a incluir",
                    options=tags_simulador,
                    default=tags_simulador,
                    key="tags_simulador",
                    help="Selecciona qué tags incluir en el examen. Si no seleccionas ninguno, se incluyen todas las preguntas."
                )
                if tags_seleccionados:
                    preguntas_con_tag = [p for p in preguntas if p.get("tag", "") in tags_seleccionados]
                else:
                    preguntas_con_tag = preguntas
            else:
                preguntas_con_tag = preguntas
                tags_seleccionados = []
            
            total_con_tag = len(preguntas_con_tag)
            
            st.markdown("---")
            
            usar_rango = st.checkbox(
                "📏 Seleccionar por rango ordinal",
                value=False,
                key="usar_rango",
                help="Activa para elegir un rango específico de preguntas (ej: preguntas 1 a 11)"
            )
            
            if usar_rango:
                max_rango = max(total_con_tag, 1)
                
                if "rango_inicio" in st.session_state:
                    st.session_state.rango_inicio = min(st.session_state.rango_inicio, max_rango)
                if "rango_fin" in st.session_state:
                    st.session_state.rango_fin = min(st.session_state.rango_fin, max_rango)
                
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    rango_inicio = st.number_input(
                        "Desde (pregunta #)",
                        min_value=1,
                        max_value=max_rango,
                        step=1,
                        key="rango_inicio",
                        help="Número de pregunta de inicio (orden según 'Ver Preguntas')"
                    )
                with col_r2:
                    rango_fin = st.number_input(
                        "Hasta (pregunta #)",
                        min_value=1,
                        max_value=max_rango,
                        step=1,
                        key="rango_fin",
                        help="Número de pregunta de fin (orden según 'Ver Preguntas')"
                    )
                
                if rango_inicio > rango_fin:
                    st.warning("⚠️ El rango inicio no puede ser mayor que el fin. Se ajustará automáticamente.")
                    rango_fin = max(rango_inicio, rango_fin)
                
                preguntas_disponibles = preguntas_con_tag[rango_inicio - 1:rango_fin]
                st.caption(f"📋 Rango aplicado: preguntas **{rango_inicio}** a **{rango_fin}** → **{len(preguntas_disponibles)}** preguntas seleccionadas")
            else:
                preguntas_disponibles = preguntas_con_tag
                st.caption(f"📋 Pool completo: **{len(preguntas_disponibles)}** preguntas")
            
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
                    num_preguntas = st.slider(
                        "🎯 Número de preguntas del examen",
                        min_value=1,
                        max_value=len(preguntas_disponibles),
                        value=min(10, len(preguntas_disponibles)),
                        step=1,
                        key="num_preguntas_slider",
                        help="Desliza para seleccionar cuántas preguntas quieres"
                    )
                
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
                    preguntas_sel = random.sample(preguntas_disponibles, num_preguntas) if modo_aleatorio else preguntas_disponibles[:num_preguntas]
                    # Deduplicar por texto de pregunta (safety net contra duplicados)
                    vistos = set()
                    preguntas_unicas = []
                    for p in preguntas_sel:
                        texto = p.get("pregunta", "").strip()
                        if texto not in vistos:
                            vistos.add(texto)
                            preguntas_unicas.append(p)
                    if len(preguntas_unicas) < len(preguntas_sel):
                        st.warning(f"⚠️ Se eliminaron {len(preguntas_sel) - len(preguntas_unicas)} pregunta(s) duplicada(s).")
                    st.session_state.preguntas_simulador = [aleatorizar_pregunta(p) for p in preguntas_unicas]
                    st.session_state.simulador_activo = True
                    st.session_state.indice_actual = 0
                    st.session_state.respuestas_usuario = {}
                    st.session_state.mostrar_resultados = False
                    
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
            
            st.markdown("## 🎯 Resultados del Examen")
            st.markdown('<div id="reporte-topo"></div>', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("✅ Correctas", res['correctas'], delta=f"{res['correctas']}/{res['total']}")
            with col2:
                st.metric("🟡 Parciales", res['parciales'])
            with col3:
                st.metric("❌ Incorrectas", res['incorrectas'])
            with col4:
                st.metric("📊 Puntuación", f"{res['porcentaje']:.0f}%")
            
            if res['porcentaje'] >= 80:
                st.success("🎉 ¡Excelente! Has aprobado con nota alta")
            elif res['porcentaje'] >= 60:
                st.warning("😊 Aprobado - Puedes mejorar")
            else:
                st.error("😔 No aprobado - Sigue estudiando")
            
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
                    
                    if estado == "correcta":
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 16px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);'>
                            <h3 style='margin: 0; font-size: 20px;'>✅ Pregunta {idx_orig + 1} - CORRECTA</h3>
                        </div>
                        """, unsafe_allow_html=True)
                    elif estado == "parcial":
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; padding: 16px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);'>
                            <h3 style='margin: 0; font-size: 20px;'>🟡 Pregunta {idx_orig + 1} - PARCIAL</h3>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                        <div style='background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; padding: 16px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);'>
                            <h3 style='margin: 0; font-size: 20px;'>❌ Pregunta {idx_orig + 1} - INCORRECTA</h3>
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
                                    <strong style='color: {color_correcta};'>{letra}) {texto}</strong>
                                    <span style='color: {color_correcta}; font-weight: 600;'> ← ✅ CORRECTA</span>
                                </div>
                                """, unsafe_allow_html=True)
                            elif letra in resp_usuario:
                                st.markdown(f"""
                                <div style='background: {bg_incorrecta}; border-left: 4px solid {border_incorrecta}; padding: 12px; margin-bottom: 8px; border-radius: 6px;'>
                                    <span style='color: {color_incorrecta};'>{letra}) {texto}</span>
                                    <span style='color: {color_incorrecta}; font-weight: 600;'> ← ❌ Tu respuesta</span>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown(f"""
                                <div style='background: {bg_default}; border-left: 4px solid {border_default}; padding: 12px; margin-bottom: 8px; border-radius: 6px;'>
                                    <span style='color: {color_default};'>{letra}) {texto}</span>
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
            
            # === TIMER EN TIEMPO REAL CON STREAMLIT AUTOREFREASH ===
            if st.session_state.get("timer_activo", False):
                tiempo_inicio_timer = st.session_state.tiempo_inicio
                tiempo_limite_timer = st.session_state.tiempo_limite
                
                tiempo_transcurrido = time.time() - tiempo_inicio_timer
                tiempo_restante = tiempo_limite_timer - tiempo_transcurrido
                
                if tiempo_restante <= 0:
                    st.error("⏰ ¡Tiempo agotado!")
                    st.session_state.mostrar_resultados = True
                    st.rerun()
                
                minutos = int(tiempo_restante // 60)
                segundos = int(tiempo_restante % 60)
                
                # Usar Streamlit autoRefresh cada segundo (importado al inicio del archivo)
                if STREAMLIT_AUTOREFRESH_AVAILABLE:
                    st_autorefresh(interval=1000, limit=None, key="timer_refresh")
                else:
                    # Fallback: Force rerun con st.empty si no hay autorefresh
                    st.warning("⚠️ Instala streamlit-autorefresh para timer fluido: pip install streamlit-autorefresh")
                    time.sleep(1)
                    st.rerun()
                
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
                        Pregunta {idx + 1} de {total}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if tiempo_restante < 60:
                    st.warning(f"⚠️ ¡Solo quedan {int(tiempo_restante)} segundos!")
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
                        st.session_state.indice_actual += 1
                        st.rerun()
                else:
                    if st.button("🏁 Finalizar", type="primary", use_container_width=True):
                        with st.spinner("📊 Calculando tus resultados finales..."):
                            correctas = 0
                            parciales = 0
                            incorrectas = 0
                            no_respondidas = 0
                            
                            for i, p in enumerate(st.session_state.preguntas_simulador):
                                resp = st.session_state.respuestas_usuario.get(i, [])
                                if not isinstance(resp, list):
                                    resp = [resp] if resp else []
                                
                                # Verificar si fue respondida
                                if not resp:
                                    no_respondidas += 1
                                    continue
                                
                                correctas_p = set(p["correctas"])
                                respuestas_s = set(resp)
                                
                                if respuestas_s == correctas_p:
                                    correctas += 1
                                elif respuestas_s.intersection(correctas_p):
                                    parciales += 1
                                else:
                                    incorrectas += 1
                            
                            # Las no respondidas se cuentan como incorrectas
                            if no_respondidas > 0 and st.session_state.get("timer_activo", False):
                                incorrectas += no_respondidas
                                no_respondidas = 0
                            
                            st.session_state.resultado_final = {
                                "correctas": correctas,
                                "parciales": parciales,
                                "incorrectas": incorrectas,
                                "no_respondidas": no_respondidas,
                                "total": total,
                                "porcentaje": (correctas / total) * 100
                            }
                            st.session_state.mostrar_resultados = True
                        st.rerun()
