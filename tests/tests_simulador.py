"""Tests de las mejoras del simulador (entrega anticipada, ver respuesta,
atajos de teclado). Aquí solo la lógica pura; los flujos de UI van en
tests_simulador_app.py.
"""
import os
import sys
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from src.historial import registrar_examen

fallos = []


def check(desc, cond, detail=""):
    marca = "OK " if cond else "FAIL"
    print(f"  [{marca}] {desc} {detail}")
    if not cond:
        fallos.append(desc)


BANCO = [
    {"id": 1, "pregunta": "p1", "tag": "t", "opciones": ["A) x", "B) y"], "correctas": ["A"]},
    {"id": 2, "pregunta": "p2", "tag": "t", "opciones": ["A) x", "B) y"], "correctas": ["B"]},
    {"id": 3, "pregunta": "p3", "tag": "t", "opciones": ["A) x", "B) y"], "correctas": ["A"]},
]
FECHA = datetime(2026, 1, 1)


def total_eventos(historial):
    return sum(len(d["eventos"]) for d in historial["preguntas"].values())


print("== registrar_examen con omitir_no_respondidas ==")
hist = registrar_examen({}, BANCO, {0: ["A"]}, fecha=FECHA, omitir_no_respondidas=True)
check("el examen se cuenta igual", hist["examenes"] == 1)
check("solo la respondida genera evento (las otras no son fallo)",
      total_eventos(hist) == 1, f"-> {total_eventos(hist)}")

hist_fallo = registrar_examen({}, BANCO, {0: ["B"]}, fecha=FECHA, omitir_no_respondidas=True)
check("una respondida mal sigue registrando su fallo",
      total_eventos(hist_fallo) == 1
      and any(d["eventos"][0]["resultado"] == "fallo" for d in hist_fallo["preguntas"].values()))

print("\n== registrar_examen sin omitir (comportamiento existente) ==")
hist_normal = registrar_examen({}, BANCO, {0: ["A"]}, fecha=FECHA)
check("las no respondidas siguen contando como fallo",
      total_eventos(hist_normal) == 3, f"-> {total_eventos(hist_normal)}")

print("\n== atajos de teclado ==")
from src.atajos_teclado import ACCIONES_VALIDAS, capturar_tecla

check("las acciones validas son adelante/atras",
      ACCIONES_VALIDAS == ("adelante", "atras"), f"-> {ACCIONES_VALIDAS}")
check("sin ejecucion de Streamlit no hay tecla (None)",
      capturar_tecla() is None, f"-> {capturar_tecla()}")

with open(os.path.join(REPO, "app.py"), encoding="utf-8") as f:
    app_fuente = f.read()
check("app.py captura la tecla y navega con las acciones del componente",
      "capturar_tecla" in app_fuente
      and '"adelante"' in app_fuente and '"atras"' in app_fuente)
with open(os.path.join(REPO, "src", "atajos_componente", "index.html"),
          encoding="utf-8") as f:
    componente = f.read()
check("el componente habla el protocolo de componentes de Streamlit",
      "streamlit:setComponentValue" in componente
      and "streamlit:componentReady" in componente)
check("el componente escucha el teclado en su propio documento y en el padre",
      'window.addEventListener("keydown"' in componente
      and 'window.parent.document.addEventListener("keydown"' in componente)

print("\n" + ("TODOS OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
sys.exit(1 if fallos else 0)
