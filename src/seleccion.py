"""Lógica de selección de preguntas para el simulador.

Aislada de Streamlit para poder probarla y para que el rango ordinal use
exactamente la misma numeración que muestra la pestaña "Ver Preguntas".
"""

import re

# Mismo formato de prefijo que usa aleatorizar_pregunta(): "A)", "A.", "A -", "A:"
_PREFIJO_OPCION = re.compile(r"^([A-Fa-f])\s*[\).\-:]\s*(.*)", re.DOTALL)

SIN_TAG = "Sin tag"


def normalizar_texto(texto):
    """Normaliza texto para comparar: minúsculas y espacios/puntuación colapsados.

    El OCR introduce saltos de línea y espacios distintos en preguntas que son
    la misma, así que comparar con == sobre el texto crudo no detecta duplicados.
    """
    if not texto:
        return ""
    return re.sub(r"\W+", " ", texto.lower()).strip()


def _texto_opcion(opcion):
    """Devuelve el texto de una opcion sin su letra, ya normalizado."""
    match = _PREFIJO_OPCION.match(opcion or "")
    return normalizar_texto(match.group(2) if match else opcion)


def firma_pregunta(pregunta):
    """Identidad de una pregunta a efectos de duplicados.

    Incluye enunciado y opciones (sin letra y sin orden), pero NO las respuestas
    correctas: dos copias de la misma pregunta con respuestas distintas son un
    duplicado con un error de datos, no dos preguntas diferentes.

    Las opciones forman parte de la firma porque el banco tiene preguntas
    legítimamente distintas que comparten enunciado ("Refer to the exhibits...")
    y solo se diferencian en las opciones.
    """
    enunciado = normalizar_texto(pregunta.get("pregunta", ""))
    opciones = tuple(sorted(
        t for t in (_texto_opcion(o) for o in pregunta.get("opciones", [])) if t
    ))
    return (enunciado, opciones)


def deduplicar(preguntas):
    """Reparte las preguntas en (unicas, descartadas), conservando la primera copia.

    Mantiene el orden original de las unicas.
    """
    vistas = set()
    unicas = []
    descartadas = []
    for pregunta in preguntas:
        firma = firma_pregunta(pregunta)
        if firma in vistas:
            descartadas.append(pregunta)
        else:
            vistas.add(firma)
            unicas.append(pregunta)
    return unicas, descartadas


def detectar_conflictos(preguntas):
    """Grupos de ids duplicados cuyas respuestas correctas no coinciden.

    Son errores del banco: una de las copias tiene la respuesta mal y conviene
    revisarla a mano en "Ver Preguntas".
    """
    por_firma = {}
    for pregunta in preguntas:
        por_firma.setdefault(firma_pregunta(pregunta), []).append(pregunta)

    conflictos = []
    for grupo in por_firma.values():
        if len(grupo) < 2:
            continue
        respuestas = {tuple(sorted(p.get("correctas", []))) for p in grupo}
        if len(respuestas) > 1:
            conflictos.append([p.get("id") for p in grupo])
    return conflictos


def coincide_tag(pregunta, tags_seleccionados):
    """True si la pregunta encaja en la selección de tags.

    Sin selección => entran todas. "Sin tag" selecciona las no etiquetadas,
    igual que el filtro de la pestaña "Ver Preguntas".
    """
    if not tags_seleccionados:
        return True
    tag = pregunta.get("tag", "") or ""
    for seleccionado in tags_seleccionados:
        if seleccionado == SIN_TAG and not tag:
            return True
        if seleccionado == tag and tag:
            return True
    return False


def normalizar_rango(rango, total):
    """Ordena y recorta un rango 1-based a los límites del banco."""
    inicio, fin = rango
    inicio, fin = min(inicio, fin), max(inicio, fin)
    inicio = max(1, min(inicio, total)) if total else 1
    fin = max(1, min(fin, total)) if total else 1
    return inicio, fin


def seleccionar_pool(banco, tags_seleccionados=None, rango=None):
    """Construye el pool de preguntas elegibles para un examen.

    Orden de operaciones (importa):
      1. Primero se filtra por tags.
      2. El rango se aplica sobre ese resultado, contando de arriba abajo tal
         como aparece en "Ver Preguntas" con ese mismo filtro. Es un numero de
         orden, NO el #id de la pregunta: si la primera del tag es la #135, el
         rango 1-5 empieza en ella y coge las cuatro siguientes. Asi la
         numeracion no depende de los ids, que cambian al borrar preguntas.
      3. Por ultimo se quitan duplicados. Va al final para que el tramo
         seleccionado sea exactamente el que se ve en "Ver Preguntas"; si el
         tramo trae repetidas, se avisa en vez de arrastrarlas al examen.

    Devuelve (pool, info) donde info documenta lo aplicado para mostrarlo en la UI.
    """
    tags_seleccionados = tags_seleccionados or []

    filtrado = [p for p in banco if coincide_tag(p, tags_seleccionados)]
    total_filtrado = len(filtrado)

    if rango:
        inicio, fin = normalizar_rango(rango, total_filtrado)
        seleccion = filtrado[inicio - 1:fin]
    else:
        inicio, fin = (1, total_filtrado)
        seleccion = list(filtrado)

    tras_rango = len(seleccion)
    pool, descartadas = deduplicar(seleccion)

    info = {
        "rango": (inicio, fin) if rango else None,
        "total_banco": len(banco),
        "total_filtrado": total_filtrado,
        "tras_rango": tras_rango,
        "duplicados": len(descartadas),
        "ids_duplicados": [p.get("id") for p in descartadas],
        "conflictos": detectar_conflictos(seleccion),
    }
    return pool, info
