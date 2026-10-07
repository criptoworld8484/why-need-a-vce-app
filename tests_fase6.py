"""Tests Fase 6: historial de fallos reiterados (src/historial.py).

Cubre:
1. clasificar_intento: exacta = correcta; parcial, incorrecta y no
   respondida = fallo.
2. clave_pregunta: estable ante re-ordenación/reetiquetado de opciones
   (aleatorizar_pregunta) y distinta para preguntas distintas.
3. registrar_examen: acumula eventos, refresca snapshot y no muta la entrada.
4. resumen_reiteradas: umbral, ventana temporal y orden por fallos.
5. cargar/guardar roundtrip, escritura atomica y JSON corrupto.
"""
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

from src.historial import (FORMATO_FECHA, cargar_historial, clasificar_intento,
                           clave_pregunta, guardar_historial, historial_vacio,
                           registrar_examen, resumen_reiteradas)

fallos = []
def check(nombre, cond, detalle=""):
    print(("  PASS  " if cond else "  FAIL  ") + nombre + ("" if cond else f" {detalle}"))
    if not cond:
        fallos.append(nombre)


print("\n== clasificar_intento ==")
P = {"id": 1, "pregunta": "p", "opciones": ["A) x", "B) y"], "correctas": ["A"]}
check("respuesta exacta -> correcta", clasificar_intento(P, ["A"]) == "correcta")
check("respuesta parcial -> fallo", clasificar_intento(P, ["A", "B"]) == "fallo")
check("respuesta incorrecta -> fallo", clasificar_intento(P, ["B"]) == "fallo")
check("sin respuesta -> fallo", clasificar_intento(P, []) == "fallo")
check("respuesta como string -> correcta", clasificar_intento(P, "A") == "correcta")
MULTI = {"id": 2, "pregunta": "m", "opciones": ["A) x", "B) y", "C) z"], "correctas": ["A", "B"]}
check("multiple exacta -> correcta", clasificar_intento(MULTI, ["B", "A"]) == "correcta")
check("multiple con una de dos -> fallo", clasificar_intento(MULTI, ["A"]) == "fallo")

print("\n== clave_pregunta ==")
P_SHUFFLE = {"id": 9, "pregunta": "p", "opciones": ["B) y", "A) x"], "correctas": ["B"]}
check("estable ante reorden/reetiquetado", clave_pregunta(P) == clave_pregunta(P_SHUFFLE))
P_DISTINTA = {"id": 1, "pregunta": "p", "opciones": ["A) x", "B) z"], "correctas": ["A"]}
check("distinta si cambia una opcion", clave_pregunta(P) != clave_pregunta(P_DISTINTA))
check("distinto enunciado -> distinta clave",
      clave_pregunta(P) != clave_pregunta({**P, "pregunta": "otra"}))

print("\n== registrar_examen ==")
AHORA = datetime(2026, 10, 6, 12, 0, 0)
h0 = historial_vacio()
h = registrar_examen(h0, [P, MULTI], {0: ["B"], 1: ["A", "B"]}, fecha=AHORA)
check("cuenta un examen", h["examenes"] == 1)
check("registra un evento por pregunta", len(h["preguntas"]) == 2)
ev_p = h["preguntas"][clave_pregunta(P)]["eventos"]
check("fallo (incorrecta) registrado", ev_p == [{"fecha": AHORA.strftime(FORMATO_FECHA), "resultado": "fallo"}])
ev_m = h["preguntas"][clave_pregunta(MULTI)]["eventos"]
check("correcta registrada", ev_m[0]["resultado"] == "correcta")
check("snapshot guarda correctas y tag",
      h["preguntas"][clave_pregunta(MULTI)]["correctas"] == ["A", "B"])
check("no muta el historial de entrada", h0["examenes"] == 0 and h0["preguntas"] == {})

h2 = registrar_examen(h, [P], {0: ["A"]}, fecha=AHORA + timedelta(days=1))
check("segundo examen acumula", h2["examenes"] == 2)
check("el original queda intacto (inmutabilidad)", len(h["preguntas"][clave_pregunta(P)]["eventos"]) == 1)
ev_p2 = h2["preguntas"][clave_pregunta(P)]["eventos"]
check("evento nuevo con su fecha",
      ev_p2[-1] == {"fecha": (AHORA + timedelta(days=1)).strftime(FORMATO_FECHA), "resultado": "correcta"})

print("\n== resumen_reiteradas ==")
h3 = registrar_examen(h2, [P], {0: []}, fecha=AHORA + timedelta(days=2))  # P falla 2ª vez
r_todo = resumen_reiteradas(h3, umbral_fallos=2)
check("P reiterada con 2 fallos", [r["clave"] for r in r_todo] == [clave_pregunta(P)])
check("fallos e intentos correctos", r_todo[0]["fallos"] == 2 and r_todo[0]["intentos"] == 3)
check("tasa de fallo (2/3)", abs(r_todo[0]["tasa_fallo"] - 66.66) < 0.1, f"-> {r_todo[0]['tasa_fallo']}")
check("umbral 3 no la incluye", resumen_reiteradas(h3, umbral_fallos=3) == [])
r_ventana = resumen_reiteradas(h3, umbral_fallos=2, dias=1, ahora=AHORA + timedelta(days=2, hours=1))
check("ventana de 1 dia solo ve el ultimo fallo (1 < umbral 2)", r_ventana == [])
r_ventana2 = resumen_reiteradas(h3, umbral_fallos=1, dias=1, ahora=AHORA + timedelta(days=2, hours=1))
check("ventana de 1 dia con umbral 1 si la ve", [r["clave"] for r in r_ventana2] == [clave_pregunta(P)])
check("orden por fallos descendentes",
      [r["fallos"] for r in resumen_reiteradas(
          registrar_examen(h3, [MULTI], {0: []}, fecha=AHORA), 1)] == [2, 1])

print("\n== persistencia ==")
tmpdir = tempfile.mkdtemp(prefix="vce_test_fase6_")
ruta = os.path.join(tmpdir, "historial_fallos.json")
check("cargar de ruta inexistente -> vacio", cargar_historial(ruta) == historial_vacio())
guardar_historial(ruta, h3)
check("roundtrip guardar/cargar", cargar_historial(ruta) == h3)
check("sin .tmp residual", not os.path.exists(ruta + ".tmp"))
with open(ruta, "w", encoding="utf-8") as f:
    f.write("{json roto")
h_corrupto = cargar_historial(ruta)
check("JSON corrupto -> historial vacio", h_corrupto == historial_vacio())
corruptas = [n for n in os.listdir(tmpdir) if n.startswith("historial_fallos.json.corrupta_")]
check("el corrupto queda renombrado", len(corruptas) == 1, f"-> {corruptas}")
with open(ruta, "w", encoding="utf-8") as f:
    json.dump(["lista", "no", "dict"], f)
check("estructura no dict -> historial vacio", cargar_historial(ruta) == historial_vacio())

print("\n" + ("TODOS OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
sys.exit(1 if fallos else 0)
