"""Tests Fase 1: calculo de resultados, parseo de opciones y validacion de import."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.examen import calcular_resultado
from src.preguntas import (
    prefijo_opcion, normalizar_opciones_ocr, validar_preguntas_importadas,
    reasignar_ids,
)

fallos = []
def check(nombre, cond, detalle=""):
    if cond:
        print(f"  PASS  {nombre}")
    else:
        print(f"  FAIL  {nombre} {detalle}")
        fallos.append(nombre)

print("\n== calcular_resultado ==")
psim = [
    {"id": 1, "pregunta": "p1", "opciones": ["A) x", "B) y"], "correctas": ["A"]},
    {"id": 2, "pregunta": "p2", "opciones": ["A) x", "B) y"], "correctas": ["A", "B"]},
    {"id": 3, "pregunta": "p3", "opciones": ["A) x", "B) y"], "correctas": ["A"]},
]
r = calcular_resultado(psim, {0: ["A"], 1: ["A"], 2: ["B"]})
check("coincidencia exacta -> correcta", r["correctas"] == 1, f"-> {r}")
check("subconjunto -> parcial", r["parciales"] == 1, f"-> {r}")
check("disjunta -> incorrecta", r["incorrectas"] == 1, f"-> {r}")
check("porcentaje = 1/3", abs(r["porcentaje"] - 100/3) < 0.01, f"-> {r}")

r = calcular_resultado(psim, {0: ["A"]}, contar_no_respondidas_como_incorrectas=True)
check("modo examen: no respondidas a incorrectas",
      r["incorrectas"] == 2 and r["no_respondidas"] == 0, f"-> {r}")
r = calcular_resultado(psim, {0: ["A"]}, contar_no_respondidas_como_incorrectas=False)
check("modo practica: no respondidas visibles",
      r["incorrectas"] == 0 and r["no_respondidas"] == 2, f"-> {r}")
r = calcular_resultado(psim, {0: "A", 2: ["B"]})
check("respuesta no-lista se envuelve", r["correctas"] == 1 and r["parciales"] == 0, f"-> {r}")
r = calcular_resultado([], {})
check("examen vacio no divide por cero", r["porcentaje"] == 0.0 and r["total"] == 0)

print("\n== prefijo_opcion ==")
check("A) x", prefijo_opcion("A) x") == ("A", "x"))
check("b. y (minuscula)", prefijo_opcion("b. y") == ("B", "y"))
check("C - z", prefijo_opcion("C - z") == ("C", "z"))
check("D:w", prefijo_opcion("D:w") == ("D", "w"))
_multilinea = prefijo_opcion("A) linea1\nlinea2")
check("multilinea se conserva completa",
      _multilinea == ("A", "linea1\nlinea2"), f"-> {_multilinea!r}")
check("sin prefijo -> None", prefijo_opcion("TCP/25") is None)
check("vacia -> None", prefijo_opcion("") is None)
check("no str -> None", prefijo_opcion(None) is None)
check("solo letra sin texto -> None", prefijo_opcion("A)") is None)

print("\n== normalizar_opciones_ocr ==")
check("sin prefijo conserva el texto completo",
      normalizar_opciones_ocr(["TCP/25", "UDP/53"]) == [("A", "TCP/25"), ("B", "UDP/53")],
      f"-> {normalizar_opciones_ocr(['TCP/25', 'UDP/53'])}")
check("con prefijo se relettera en orden",
      normalizar_opciones_ocr(["B) dos", "A) uno"]) == [("A", "dos"), ("B", "uno")])
check("letras duplicadas del OCR se reletteran",
      normalizar_opciones_ocr(["A) x", "A) y"]) == [("A", "x"), ("B", "y")])
check("mixto prefijo/sin prefijo",
      normalizar_opciones_ocr(["A) foo", "bar"]) == [("A", "foo"), ("B", "bar")])
check("vacias y no-str se descartan",
      normalizar_opciones_ocr(["A) x", "", "   ", 7]) == [("A", "x")])
check("None -> lista vacia", normalizar_opciones_ocr(None) == [])

print("\n== validar_preguntas_importadas ==")
buena = {"id": 5, "pregunta": " p ", "imagen": "imagenes_preguntas/x.png",
         "tag": " T ", "opciones": ["A) x ", "B) y"], "correctas": ["a", "B"]}
validas, errores = validar_preguntas_importadas([buena])
check("pregunta valida pasa", len(validas) == 1 and not errores, f"-> {errores}")
if validas:
    v = validas[0]
    check("correctas normalizadas a mayusculas", v["correctas"] == ["A", "B"], f"-> {v}")
    check("tag y opciones sin espacios sobrantes",
          v["tag"] == "T" and v["opciones"] == ["A) x", "B) y"], f"-> {v}")
    check("conserva id e imagen", v["id"] == 5 and v["imagen"] == "imagenes_preguntas/x.png")

sin_correctas = {"pregunta": "p", "opciones": ["A) x", "B) y"]}
validas, errores = validar_preguntas_importadas([sin_correctas])
check("falta correctas -> rechazada (antes reventaba el simulador)",
      not validas and len(errores) == 1, f"-> {errores}")
correctas_raras = {"pregunta": "p", "opciones": ["A) x", "B) y"], "correctas": ["A", "Z"]}
validas, errores = validar_preguntas_importadas([correctas_raras])
check("letra fuera de A-F -> rechazada", not validas, f"-> {errores}")
fuera_opciones = {"pregunta": "p", "opciones": ["A) x", "B) y"], "correctas": ["C"]}
validas, errores = validar_preguntas_importadas([fuera_opciones])
check("correcta sin opcion correspondiente -> rechazada", not validas, f"-> {errores}")
pocas_op = {"pregunta": "p", "opciones": ["A) x"], "correctas": ["A"]}
validas, errores = validar_preguntas_importadas([pocas_op])
check("menos de 2 opciones -> rechazada", not validas, f"-> {errores}")
sin_prefijo_ops = {"pregunta": "p", "opciones": ["x", "y"], "correctas": ["A"]}
validas, errores = validar_preguntas_importadas([sin_prefijo_ops])
check("opciones sin prefijo -> rechazada (aleatorizar las perderia)", not validas, f"-> {errores}")
validas, errores = validar_preguntas_importadas([buena, "chorizo", sin_correctas])
check("mezcla: solo pasa la buena y se listan los errores",
      len(validas) == 1 and len(errores) == 2, f"-> {errores}")
validas, errores = validar_preguntas_importadas({"no": "lista"})
check("raiz no lista -> error", not validas and bool(errores))

print("\n== reasignar_ids ==")
dup = [{"id": 3, "pregunta": "a"}, {"id": 3, "pregunta": "b"}, {"id": None, "pregunta": "c"}]
reasignar_ids(dup)
check("ids consecutivos sin duplicados", [p["id"] for p in dup] == [1, 2, 3])

print("\n" + ("TODOS OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
sys.exit(1 if fallos else 0)
