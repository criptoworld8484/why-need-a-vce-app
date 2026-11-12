"""Selección de modelos Gemini para el OCR.

La disponibilidad de modelos NO es universal: depende de la cuenta de la API
Key. Un modelo retirado para usuarios nuevos (p. ej. gemini-2.5-flash) sigue
funcionando en cuentas que lo usaron antes de su retiro, y la API devuelve un
404 NOT_FOUND en las cuentas nuevas. Por eso la lista no se codifica a mano:
se consulta a la API con la key del usuario y solo se recurre a una lista de
reserva cuando la consulta no es posible.
"""

import re

MODELO_OCR_PREDEFINIDO = "gemini-3.8-flash"

# Única fuente de modelos conocidos, en orden de preferencia (estables y con
# tier gratuito primero; gemini-4-argon es de pago y nunca por defecto). Es a
# la vez la lista de reserva cuando la API no se puede consultar y el orden
# para elegir el modelo por defecto: una sola lista que mantener.
MODELOS_OCR_RESERVA = (
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
)

# Un error de cuota nunca es 'modelo no disponible', aunque su texto mencione
# 404 o 'not found' (p. ej. en metadatos o pistas de reintento).
_INDIOS_CUOTA = ("429", "resource_exhausted", "quota")

# Subcadenas que descartan modelos no aptos para extraer texto de imágenes.
_NO_APTOS_OCR = (
    "tts", "live", "image", "embedding", "transcribe", "audio", "banana", "aqa",
)

# Indicios de que la API rechaza el modelo por no estar disponible para la
# cuenta (retirado, solo para usuarios antiguos, nombre inexistente...).
_INDIOS_MODELO_NO_DISPONIBLE = (
    "404", "not_found", "not found", "no longer available", "does not exist",
)


def _clave_version(nombre):
    """Clave de orden natural: los bloques numéricos comparan como números
    (gemini-3.10-flash va después de gemini-3.9-flash)."""
    partes = re.split(r"(\d+)", nombre.lower())
    return [(1, int(p)) if p.isdigit() else (0, p) for p in partes]


def filtrar_modelos_ocr(nombres):
    """Normaliza nombres crudos de la API a IDs aptos para OCR.

    Quita el prefijo "models/", descarta modelos que no generan texto desde
    imágenes (tts, live, embeddings, image...), deduplica y ordena de más
    nuevo a más antiguo.
    """
    limpios = []
    for nombre in nombres or []:
        if not nombre:
            continue
        nombre = str(nombre).strip()
        if nombre.startswith("models/"):
            nombre = nombre[len("models/"):]
        bajo = nombre.lower()
        if not bajo.startswith("gemini"):
            continue
        if any(parte in bajo for parte in _NO_APTOS_OCR):
            continue
        if nombre not in limpios:
            limpios.append(nombre)
    return sorted(limpios, key=_clave_version, reverse=True)


def modelo_ocr_preferido(nombres):
    """Devuelve el mejor modelo por defecto entre los disponibles.

    Prioriza los modelos estables con tier gratuito; si ninguno coincide,
    devuelve el primero de la lista, y si la lista está vacía,
    MODELO_OCR_PREDEFINIDO.
    """
    nombres = nombres or []
    for preferido in MODELOS_OCR_RESERVA:
        if preferido in nombres:
            return preferido
    return nombres[0] if nombres else MODELO_OCR_PREDEFINIDO


def es_error_modelo_no_disponible(texto_error):
    """Detecta si un error de la API significa 'modelo no disponible'.

    Exige contexto de modelo en el texto y un indicio de disponibilidad, y
    descarta de plano los errores de cuota: un 404 o un 'not found' genérico
    sin mención de modelo no cuenta, para no secuestrar la vía de reintentos.
    """
    bajo = str(texto_error or "").lower()
    if any(cuota in bajo for cuota in _INDIOS_CUOTA):
        return False
    if "model" not in bajo and "modelo" not in bajo:
        return False
    return any(indicio in bajo for indicio in _INDIOS_MODELO_NO_DISPONIBLE)


def listar_modelos_ocr(api_key):
    """Lista los modelos de OCR disponibles para la API Key.

    Devuelve (modelos, motivo): 'modelos' es la lista apta para OCR o None si
    no se pudo obtener; en ese caso 'motivo' dice por qué (sin key, SDK
    ausente, error de red, la API sin modelos aptos...). El llamador decide si
    recurre a MODELOS_OCR_RESERVA y puede mostrar el motivo. La consulta va
    con timeout acotado para no colgar la pestaña OCR si la red se cuelga.
    """
    if not api_key or not api_key.strip():
        return None, "sin API key configurada"
    try:
        from google import genai
        from google.genai import types
    except Exception:
        return None, "google-genai no está instalado"
    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=8000),
        )
        nombres = []
        for modelo in client.models.list():
            acciones = getattr(modelo, "supported_actions", None) or []
            if acciones and "generateContent" not in acciones:
                continue
            nombres.append(modelo.name)
        filtrados = filtrar_modelos_ocr(nombres)
        if not filtrados:
            return None, "la API no devolvió modelos aptos para OCR"
        return filtrados, None
    except Exception as e:
        detalle = str(e).strip().splitlines()
        return None, f"no se pudo consultar la API: {detalle[0][:120] if detalle else type(e).__name__}"
