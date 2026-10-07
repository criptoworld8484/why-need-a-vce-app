"""Historial de fallos reiterados entre exámenes.

Funciones puras (sin Streamlit) para registrar, al cerrar cada examen, qué
preguntas no se acertaron (incorrectas, parciales y no respondidas) y
consultar cuáles se fallan de forma reiterada dentro de una ventana de
tiempo. La persistencia vive en 'historial_fallos.json' dentro del data dir.

La identidad de una pregunta es el hash de firma_pregunta() (enunciado +
opciones sin letra y sin orden), NO su id: aleatorizar_pregunta() reordena y
reetiqueta las opciones en cada examen y reasignar_ids() renumera el banco
al importar/reemplazar, así que el id no es estable. La firma sí.
"""

import hashlib
import json
import os
import time
from datetime import datetime, timedelta

from src.seleccion import firma_pregunta

HISTORIAL_VERSION = 1
MAX_CHARS_ENUNCIADO = 300
FORMATO_FECHA = "%Y-%m-%dT%H:%M:%S"


def historial_vacio():
    """Estructura de un historial recién inicializado."""
    return {"version": HISTORIAL_VERSION, "examenes": 0, "preguntas": {}}


def clave_pregunta(pregunta):
    """Identidad estable de la pregunta: hash sha1 de su firma."""
    enunciado, opciones = firma_pregunta(pregunta)
    materia = json.dumps([enunciado, list(opciones)], ensure_ascii=False)
    return hashlib.sha1(materia.encode("utf-8")).hexdigest()


def clasificar_intento(pregunta, respuesta):
    """Resultado de una pregunta en un examen: 'correcta' o 'fallo'.

    Todo lo no acertado cuenta como fallo (decisión de producto): respuesta
    parcial (acierta alguna pero no todas), incorrecta y no respondida.
    """
    resp = respuesta if isinstance(respuesta, list) else ([respuesta] if respuesta else [])
    if not resp:
        return "fallo"
    correctas = set(pregunta.get("correctas", []))
    return "correcta" if set(resp) == correctas else "fallo"


def registrar_examen(historial, preguntas_simulador, respuestas_usuario, fecha=None):
    """Devuelve un historial nuevo con el examen registrado.

    Añade un evento por pregunta (fecha + resultado). El snapshot (enunciado,
    tag, id, correctas) se refresca en cada registro, así las ediciones del
    banco se reflejan sin duplicar claves. 'historial' no se muta.
    """
    fecha_evento = (fecha or datetime.now()).strftime(FORMATO_FECHA)
    nuevo = {
        "version": historial.get("version", HISTORIAL_VERSION),
        "examenes": historial.get("examenes", 0) + 1,
        "preguntas": {
            clave: dict(datos, eventos=list(datos.get("eventos", [])))
            for clave, datos in historial.get("preguntas", {}).items()
        },
    }
    for i, pregunta in enumerate(preguntas_simulador or []):
        resultado = clasificar_intento(pregunta, respuestas_usuario.get(i, []))
        clave = clave_pregunta(pregunta)
        datos = nuevo["preguntas"].setdefault(
            clave,
            {"enunciado": "", "tag": "", "id_actual": None, "correctas": [], "eventos": []},
        )
        enunciado = (pregunta.get("pregunta") or "").strip()
        datos["enunciado"] = enunciado[:MAX_CHARS_ENUNCIADO]
        datos["tag"] = pregunta.get("tag") or ""
        datos["id_actual"] = pregunta.get("id")
        datos["correctas"] = list(pregunta.get("correctas", []))
        datos["eventos"].append({"fecha": fecha_evento, "resultado": resultado})
    return nuevo


def _parsear_fecha(texto):
    try:
        return datetime.strptime(texto, FORMATO_FECHA)
    except (TypeError, ValueError):
        return None


def resumen_reiteradas(historial, umbral_fallos, dias=None, ahora=None):
    """Preguntas falladas al menos 'umbral_fallos' veces en la ventana dada.

    'dias' None cuenta todo el historial; si no, solo los eventos de los
    últimos N días. Devuelve una lista ordenada por nº de fallos (desc) con
    fallos, intentos, tasa de fallo y fecha del último fallo.
    """
    ref = ahora or datetime.now()
    desde = ref - timedelta(days=dias) if dias is not None else None

    reiteradas = []
    for clave, datos in historial.get("preguntas", {}).items():
        eventos = []
        for e in datos.get("eventos", []):
            fecha = _parsear_fecha(e.get("fecha"))
            if fecha is None:
                continue
            if desde is not None and fecha < desde:
                continue
            eventos.append((fecha, e.get("resultado")))
        if not eventos:
            continue
        fallos = sum(1 for _, resultado in eventos if resultado == "fallo")
        if fallos < umbral_fallos:
            continue
        fechas_fallo = [f for f, resultado in eventos if resultado == "fallo"]
        reiteradas.append({
            "clave": clave,
            "enunciado": datos.get("enunciado", ""),
            "tag": datos.get("tag", ""),
            "correctas": list(datos.get("correctas", [])),
            "fallos": fallos,
            "intentos": len(eventos),
            "tasa_fallo": (fallos / len(eventos)) * 100,
            "ultimo_fallo": max(fechas_fallo).strftime(FORMATO_FECHA),
        })
    reiteradas.sort(key=lambda r: (-r["fallos"], r["enunciado"]))
    return reiteradas


def cargar_historial(ruta):
    """Lee el historial del disco; corrupto o ausente -> historial vacío.

    Un JSON corrupto se renombra a '.corrupta_<ts>' (mismo criterio que
    preguntas.json) para no machachear datos potencialmente recuperables.
    """
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except FileNotFoundError:
        return historial_vacio()
    except (json.JSONDecodeError, OSError):
        try:
            os.replace(ruta, f"{ruta}.corrupta_{int(time.time())}")
        except OSError:
            pass
        return historial_vacio()
    if not isinstance(datos, dict) or "preguntas" not in datos or not isinstance(datos["preguntas"], dict):
        return historial_vacio()
    return datos


def guardar_historial(ruta, historial):
    """Escritura atómica (.tmp + os.replace), igual que save_questions."""
    tmp_path = ruta + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(historial, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, ruta)
