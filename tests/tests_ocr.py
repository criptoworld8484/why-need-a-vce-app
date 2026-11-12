"""Tests del contrato OCR (src/ocr.py) y del selector de modelos.

Cubre lo que los tests puros no alcanzaban (hallazgo R3-ocr-contract-untested):
que un error de modelo retirado se enruta a la rama modelo_no_disponible,
que un 429 se enruta a cuota_excedida, que el resto mantiene el reintento, y
que una respuesta válida se parsea al contrato {"pregunta", "respuestas"}.
La API se simula con un genai falso: sin red y determinista.
"""
import os
import sys
import tempfile
import types as tipos

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from tests.comun import check, cerrar  # noqa: E402

import src.ocr as ocr  # noqa: E402
from src.modelos_ocr import MODELOS_OCR_RESERVA  # noqa: E402

tmp_home = tempfile.mkdtemp(prefix="vce_test_ocr_")
os.environ["HOME"] = tmp_home

# Imagen mínima válida para la función
from PIL import Image  # noqa: E402

RUTA_IMG = os.path.join(tmp_home, "captura.png")
Image.new("RGB", (2, 2), "white").save(RUTA_IMG)


class _Respuesta:
    def __init__(self, texto):
        self.text = texto


class _FakeTypes:
    class Part:
        @staticmethod
        def from_bytes(data=None, mime_type=None):
            return object()


def _instalar_fake(resultado):
    """Sustituye ocr.genai por un cliente falso que devuelve o lanza
    'resultado'. Devuelve un contador de llamadas."""
    llamadas = []

    class _FakeModels:
        def generate_content(self, model=None, contents=None):
            llamadas.append(model)
            if isinstance(resultado, Exception):
                raise resultado
            return _Respuesta(resultado)

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            self.models = _FakeModels()

    ocr.genai = tipos.SimpleNamespace(Client=_FakeClient)
    ocr.types = _FakeTypes
    ocr.GENAI_AVAILABLE = True
    return llamadas


print("== Ruta de error: modelo retirado (404) ==")
error_real = ("Error: 404 NOT_FOUND. {'error': {'code': 404, 'message': "
              "'This model models/gemini-2.5-flash is no longer available "
              "to new users.'}}")
llamadas = _instalar_fake(Exception(error_real))
res = ocr.extract_text_from_image(RUTA_IMG, "clave-de-prueba")
check("enruta a modelo_no_disponible",
      isinstance(res, dict) and res.get("error") == "modelo_no_disponible",
      f"-> {res}")
check("incluye mensaje y detalle",
      bool(res.get("mensaje")) and "404" in res.get("detalle", ""))
check("no reintenta ante un modelo retirado (una sola llamada)",
      len(llamadas) == 1, f"-> {len(llamadas)}")

print("\n== Ruta de error: cuota (429) ==")
llamadas = _instalar_fake(Exception("429 RESOURCE_EXHAUSTED: quota exceeded, retry in 41s"))
res = ocr.extract_text_from_image(RUTA_IMG, "clave-de-prueba")
check("enruta a cuota_excedida con su mensaje",
      isinstance(res, dict) and res.get("error") == "cuota_excedida"
      and bool(res.get("mensaje")), f"-> {res.get('error')}")

print("\n== Ruta de error: resto con reintento ==")
llamadas = _instalar_fake(Exception("500 INTERNAL: backend exploded"))
res = ocr.extract_text_from_image(RUTA_IMG, "clave-de-prueba", max_retries=1)
check("devuelve el error genérico sin los centinelas",
      isinstance(res, dict) and str(res.get("error", "")).startswith("Error:")
      and res.get("error") not in ("modelo_no_disponible", "cuota_excedida"),
      f"-> {res.get('error')}")
check("con max_retries=1 hubo una sola llamada", len(llamadas) == 1)

print("\n== Ruta de éxito: contrato JSON ==")
_instalar_fake('```json\n{"pregunta": "p1", "respuestas": ["A) x", "B) y"]}\n```')
res = ocr.extract_text_from_image(RUTA_IMG, "clave-de-prueba")
check("parsea al contrato {pregunta, respuestas}",
      isinstance(res, dict) and "error" not in res
      and res.get("pregunta") == "p1" and res.get("respuestas") == ["A) x", "B) y"],
      f"-> {res}")

print("\n== Selector de modelos (AppTest, sin API key) ==")
from streamlit.testing.v1 import AppTest  # noqa: E402

os.makedirs(os.path.join(tmp_home, ".local", "share", "WhyNeedAVCEApp",
                         "imagenes_preguntas"), exist_ok=True)
at = AppTest.from_file(os.path.join(REPO, "app.py"))
at.session_state["config_completed"] = True
at.session_state["api_key_ocr"] = ""
at.session_state["pestana_actual"] = "📸 Extracción OCR"
at.run()
check("sin excepciones en la pestaña OCR", not at.exception)
selectores = [s for s in at.selectbox if s.label == "Modelo"]
check("el selector existe", bool(selectores))
if selectores:
    check("sin key muestra la lista de reserva",
          tuple(selectores[0].options) == tuple(MODELOS_OCR_RESERVA),
          f"-> {selectores[0].options}")
    check("el modelo por defecto es el preferido",
          selectores[0].value == MODELOS_OCR_RESERVA[0], f"-> {selectores[0].value}")

cerrar()
