"""Selección de modelos Gemini para el OCR.

La disponibilidad de modelos NO es universal: depende de la cuenta de la API
Key. Un modelo retirado para usuarios nuevos (p. ej. gemini-2.5-flash) sigue
funcionando en cuentas que lo usaron antes de su retiro, y la API devuelve un
404 NOT_FOUND en las cuentas nuevas. Por eso la lista no se codifica a mano:
se consulta a la API con la key del usuario y solo se recurre a una lista de
reserva cuando la consulta no es posible.
"""

MODELO_OCR_PREDEFINIDO = "gemini-3.8-flash"

# Usada solo cuando no se puede consultar la API (sin key, sin red...).
MODELOS_OCR_RESERVA = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
]

# Orden de preferencia para el modelo por defecto: estables y con tier
# gratuito primero (gemini-4-argon es de pago, nunca por defecto).
_MODELOS_PREFERIDOS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
]

# Subcadenas que descartan modelos no aptos para extraer texto de imágenes.
_NO_APTOS_OCR = (
    "tts", "live", "image", "embedding", "transcribe", "audio", "banana", "aqa",
)

# Indicios de que la API rechaza el modelo por no estar disponible para la
# cuenta (retirado, solo para usuarios antiguos, nombre inexistente...).
_INDIOS_MODELO_NO_DISPONIBLE = (
    "404", "not_found", "not found", "no longer available", "does not exist",
)


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
    return sorted(limpios, reverse=True)


def modelo_ocr_preferido(nombres):
    """Devuelve el mejor modelo por defecto entre los disponibles.

    Prioriza los modelos estables con tier gratuito; si ninguno coincide,
    devuelve el primero de la lista, y si la lista está vacía,
    MODELO_OCR_PREDEFINIDO.
    """
    nombres = nombres or []
    for preferido in _MODELOS_PREFERIDOS:
        if preferido in nombres:
            return preferido
    return nombres[0] if nombres else MODELO_OCR_PREDEFINIDO


def es_error_modelo_no_disponible(texto_error):
    """Detecta si un error de la API significa 'modelo no disponible'."""
    bajo = str(texto_error or "").lower()
    return any(indicio in bajo for indicio in _INDIOS_MODELO_NO_DISPONIBLE)


def listar_modelos_ocr(api_key):
    """Lista los modelos de OCR disponibles para la API Key, o None.

    Devuelve None cuando no se pudo consultar (sin SDK, key inválida, sin
    red...); el llamador decide si recurre a MODELOS_OCR_RESERVA.
    """
    if not api_key or not api_key.strip():
        return None
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        nombres = []
        for modelo in client.models.list():
            acciones = getattr(modelo, "supported_actions", None) or []
            if acciones and "generateContent" not in acciones:
                continue
            nombres.append(modelo.name)
        filtrados = filtrar_modelos_ocr(nombres)
        return filtrados or None
    except Exception:
        return None
