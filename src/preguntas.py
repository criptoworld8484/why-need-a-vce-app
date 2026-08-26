"""Normalización y validación del esquema de preguntas.

Funciones puras (sin Streamlit) compartidas por la ingesta OCR y la
importación de JSON/ZIP: la importación valida 'correctas' antes de tocar el
banco, y las opciones del OCR se reparsean sin asumir el prefijo "A) ".
Incluye la purga de imágenes huérfanas del directorio de imágenes.
"""

import os
import re

LETRAS_OPCIONES = ["A", "B", "C", "D", "E", "F"]

_PREFIJO_OPCION = re.compile(r"^([A-Fa-f])\s*[\).\-:]\s*(.*)", re.DOTALL)


def prefijo_opcion(opcion):
    """Separa (letra, texto) de una opción con prefijo; None si no lo tiene.

    Acepta los mismos formatos que aleatorizar_pregunta(): "A)", "A.", "A -",
    "A:". re.DOTALL conserva las opciones de varias líneas que el OCR genera
    con \\n (sin él, el texto se cortaba en el primer salto de línea).
    """
    if not isinstance(opcion, str):
        return None
    match = _PREFIJO_OPCION.match(opcion.strip())
    if not match:
        return None
    texto = match.group(2).strip()
    if not texto:
        return None
    return match.group(1).upper(), texto


def letra_por_posicion(idx):
    """Letra canónica para la opción en posición idx (A, B, ... F, G...)."""
    return LETRAS_OPCIONES[idx] if idx < len(LETRAS_OPCIONES) else chr(65 + idx)


def normalizar_opciones_ocr(respuestas):
    """Convierte la lista 'respuestas' del OCR en pares (letra, texto).

    Se relettera en orden A, B, C... conservando el texto completo: el OCR a
    veces devuelve opciones sin prefijo ("TCP/25") y trocear con opcion[0] /
    opcion[3:] las mutilaba. Las entradas vacías o no texto se descartan.
    """
    resultado = []
    for opcion in respuestas or []:
        if not isinstance(opcion, str):
            continue
        par = prefijo_opcion(opcion)
        texto = par[1] if par else opcion.strip()
        if texto:
            resultado.append((letra_por_posicion(len(resultado)), texto))
    return resultado


def validar_preguntas_importadas(contenido):
    """Valida y normaliza una lista de preguntas de un JSON/ZIP importado.

    Devuelve (validas, errores). Antes solo se comprobaba que existieran
    'pregunta' y 'opciones', y un JSON sin 'correctas' entraba al banco y
    reventaba el simulador (KeyError) al aleatorizar o corregir.
    """
    if not isinstance(contenido, list):
        return [], ["El archivo debe contener una lista de preguntas."]

    validas = []
    errores = []
    for i, p in enumerate(contenido, start=1):
        if not isinstance(p, dict):
            errores.append(f"Entrada {i}: no es un objeto.")
            continue

        pregunta = p.get("pregunta")
        if not isinstance(pregunta, str) or not pregunta.strip():
            errores.append(f"Entrada {i}: 'pregunta' falta, no es texto o está vacía.")
            continue

        opciones = p.get("opciones")
        if (not isinstance(opciones, list) or len(opciones) < 2
                or not all(isinstance(o, str) and o.strip() for o in opciones)):
            errores.append(
                f"Entrada {i}: 'opciones' debe ser una lista con al menos 2 textos.")
            continue

        correctas = p.get("correctas")
        if not isinstance(correctas, list) or not correctas:
            errores.append(f"Entrada {i} ('{pregunta[:40]}...'): 'correctas' falta o está vacía.")
            continue

        correctas_norm = [str(c).strip().upper() for c in correctas]
        if not all(c in LETRAS_OPCIONES for c in correctas_norm):
            errores.append(
                f"Entrada {i} ('{pregunta[:40]}...'): 'correctas' debe ser una lista de letras A-F.")
            continue

        letras_opciones = {
            par[0] for par in (prefijo_opcion(o) for o in opciones) if par
        }
        if not set(correctas_norm) <= letras_opciones:
            errores.append(
                f"Entrada {i} ('{pregunta[:40]}...'): hay respuestas correctas que "
                "no corresponden a ninguna opción con prefijo de letra.")
            continue

        imagen = p.get("imagen")
        tag = p.get("tag")
        validas.append({
            "id": p.get("id") if isinstance(p.get("id"), int) else None,
            "pregunta": pregunta.strip(),
            "imagen": imagen if isinstance(imagen, str) and imagen else None,
            "tag": tag.strip() if isinstance(tag, str) else "",
            "opciones": [o.strip() for o in opciones],
            "correctas": correctas_norm,
        })
    return validas, errores


def reasignar_ids(preguntas):
    """Reasigna ids consecutivos 1..N evitando duplicados del origen.

    Los ids duplicados colisionan en las claves de los widgets de 'Ver
    Preguntas' (tag_edit_*, del_*) y rompen la UI.
    """
    for nuevo_id, p in enumerate(preguntas, start=1):
        p["id"] = nuevo_id


def imagenes_referenciadas(preguntas):
    """Set con los nombres de archivo (basename) que usa alguna pregunta.

    Las imágenes viven todas en imagenes_preguntas/ y se referencian como
    ruta relativa ("imagenes_preguntas/x.png") o absoluta; en ambos casos el
    basename es la identidad del archivo.
    """
    referenciadas = set()
    for p in preguntas:
        imagen = p.get("imagen") if isinstance(p, dict) else None
        if imagen and os.path.basename(imagen):
            referenciadas.add(os.path.basename(imagen))
    return referenciadas


def purgar_imagenes_huerfanas(carpeta_imagenes, preguntas, limitar_a=None):
    """Borra de carpeta_imagenes los archivos que ninguna pregunta referencia.

    Evita que el directorio acumule imágenes de preguntas borradas. Solo toca
    archivos directamente dentro de carpeta_imagenes y devuelve la lista de
    nombres borrados.

    limitar_a (set de basenames) restringe la purga a esos archivos: se usa
    en el borrado individual para que eliminar una pregunta NO arrastre
    huérfanas ajenas y antiguas — eso queda para las purgas globales
    ("Eliminar Todas", "Reemplazar"), donde el usuario ya está rehaciendo el
    banco entero.
    """
    if not os.path.isdir(carpeta_imagenes):
        return []

    referenciadas = imagenes_referenciadas(preguntas)
    borradas = []
    for nombre in os.listdir(carpeta_imagenes):
        if limitar_a is not None and nombre not in limitar_a:
            continue
        ruta = os.path.join(carpeta_imagenes, nombre)
        if not os.path.isfile(ruta):
            continue
        if nombre not in referenciadas:
            try:
                os.remove(ruta)
                borradas.append(nombre)
            except OSError:
                pass
    return borradas
