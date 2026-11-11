"""Tests de la selección de modelos Gemini para el OCR (src/modelos_ocr.py).

Cubre:
1. filtrar_modelos_ocr: normaliza nombres crudos de la API (quita el prefijo
   "models/"), descarta modelos no aptos para extraer texto de imágenes
   (tts, live, embeddings, image, audio...), deduplica y ordena.
2. modelo_ocr_preferido: elige un modelo estable y con tier gratuito por
   defecto cuando está disponible; si no, el primero de la lista.
3. es_error_modelo_no_disponible: detecta el 404 de "modelo no disponible
   para tu cuenta" sin confundirlo con otros errores (429, 500...).
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from src.modelos_ocr import (
    MODELO_OCR_PREDEFINIDO,
    es_error_modelo_no_disponible,
    filtrar_modelos_ocr,
    modelo_ocr_preferido,
)

fallos = []


def check(desc, cond, detail=""):
    marca = "OK " if cond else "FAIL"
    print(f"  [{marca}] {desc} {detail}")
    if not cond:
        fallos.append(desc)


print("== filtrar_modelos_ocr ==")
crudos = ["models/gemini-3.8-flash", "models/gemini-2.5-flash"]
check("quita el prefijo 'models/' y ordena de más nuevo a más antiguo",
      filtrar_modelos_ocr(crudos) == ["gemini-3.8-flash", "gemini-2.5-flash"],
      f"-> {filtrar_modelos_ocr(crudos)}")

mezcla = [
    "models/gemini-3.8-flash-tts",
    "models/gemini-2.5-flash",
    "models/gemini-3.8-live",
    "models/text-embedding-004",
    "models/gemma-3-27b-it",
    "models/gemini-nano-banana-2.1",
    "models/gemini-3.1-flash-image",
    "models/gemini-2.5-flash-native-audio",
    "models/gemini-3.5-flash-lite",
]
check("solo sobreviven los gemini de texto aptos para OCR",
      filtrar_modelos_ocr(mezcla) == ["gemini-3.5-flash-lite", "gemini-2.5-flash"],
      f"-> {filtrar_modelos_ocr(mezcla)}")

dup = ["models/gemini-3.8-flash", "gemini-3.8-flash", "", None]
check("duplicados y vacíos se eliminan",
      filtrar_modelos_ocr(dup) == ["gemini-3.8-flash"],
      f"-> {filtrar_modelos_ocr(dup)}")

check("ordena versiones por número (3.10 es más nuevo que 3.9)",
      filtrar_modelos_ocr(["models/gemini-3.9-flash", "models/gemini-3.10-flash"])
      == ["gemini-3.10-flash", "gemini-3.9-flash"],
      f"-> {filtrar_modelos_ocr(['models/gemini-3.9-flash', 'models/gemini-3.10-flash'])}")

check("lista vacía devuelve lista vacía", filtrar_modelos_ocr([]) == [])

print("\n== modelo_ocr_preferido ==")
nombres = ["gemini-4-argon", "gemini-3.8-flash", "gemini-2.5-flash"]
check("prefiere el modelo estable con tier gratuito aunque haya otros",
      modelo_ocr_preferido(nombres) == "gemini-3.8-flash",
      f"-> {modelo_ocr_preferido(nombres)}")

check("una cuenta antigua conserva su modelo disponible",
      modelo_ocr_preferido(["gemini-2.5-flash"]) == "gemini-2.5-flash",
      f"-> {modelo_ocr_preferido(['gemini-2.5-flash'])}")

check("sin modelos devuelve el modelo por defecto",
      modelo_ocr_preferido([]) == MODELO_OCR_PREDEFINIDO,
      f"-> {modelo_ocr_preferido([])}")

print("\n== es_error_modelo_no_disponible ==")
error_real = ("Error: 404 NOT_FOUND. {'error': {'code': 404, 'message': "
              "'This model models/gemini-2.5-flash is no longer available to new users. "
              "Please update your code to use models/gemini-3.8-flash'}}")
check("detecta el 404 real de modelo retirado",
      es_error_modelo_no_disponible(error_real))
check("detecta 'model is not found'",
      es_error_modelo_no_disponible("400 INVALID_ARGUMENT: model is not found"))
check("sin contexto de modelo no se clasifica como modelo no disponible",
      not es_error_modelo_no_disponible("404 NOT_FOUND: resource not found"))
check("un 429 que menciona 404 en sus metadatos sigue siendo cuota",
      not es_error_modelo_no_disponible(
          "429 RESOURCE_EXHAUSTED: quota exceeded for model gemini-2.5-flash, retry in 404 seconds"))
check("no confunde un 429 de cuota",
      not es_error_modelo_no_disponible("429 RESOURCE_EXHAUSTED: quota exceeded"))
check("no confunde un error interno",
      not es_error_modelo_no_disponible("500 INTERNAL: backend error"))

print("\n" + ("TODOS OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
sys.exit(1 if fallos else 0)
