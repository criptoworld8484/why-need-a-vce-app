"""AppTest Fase 1: el timeout del timer calcula resultados en vez de crashear.

Reproduce el bug original: tiempo agotado activaba mostrar_resultados sin
calcular resultado_final (quedaba None) y la pantalla de correccion explotaba
con TypeError al leer res['correctas'].

Usa un HOME temporal para no tocar el banco real del usuario.
"""
import json
import os
import sys
import tempfile
import time

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

tmp_home = tempfile.mkdtemp(prefix="vce_test_fase1_")
os.environ["HOME"] = tmp_home
data_dir = os.path.join(tmp_home, ".local", "share", "WhyNeedAVCEApp")
os.makedirs(os.path.join(data_dir, "imagenes_preguntas"), exist_ok=True)
with open(os.path.join(data_dir, "preguntas.json"), "w", encoding="utf-8") as f:
    json.dump([{"id": 1, "pregunta": "dummy", "imagen": None, "tag": "",
                "opciones": ["A) x", "B) y"], "correctas": ["A"]}], f)

from streamlit.testing.v1 import AppTest

at = AppTest.from_file(os.path.join(REPO, "app.py"))
at.session_state["config_completed"] = True
at.session_state["pestana_actual"] = "🎮 Simulador"
at.session_state["simulador_activo"] = True
at.session_state["mostrar_resultados"] = False
at.session_state["preguntas_simulador"] = [
    {"id": 1, "pregunta": "p1", "imagen": None, "tag": "",
     "opciones": ["A) x", "B) y"], "correctas": ["A"]},
    {"id": 2, "pregunta": "p2", "imagen": None, "tag": "",
     "opciones": ["A) x", "B) y"], "correctas": ["B"]},
]
at.session_state["respuestas_usuario"] = {0: ["A"]}
at.session_state["indice_actual"] = 0
at.session_state["timer_activo"] = True
at.session_state["tiempo_limite"] = 60
at.session_state["tiempo_inicio"] = time.time() - 120
at.run()

fallos = []
def check(nombre, cond, detalle=""):
    print(("  PASS  " if cond else "  FAIL  ") + nombre + ("" if cond else f" {detalle}"))
    if not cond:
        fallos.append(nombre)

check("sin excepcion en el flujo timeout -> resultados",
      not at.exception, f"-> {[str(e.value) for e in at.exception]}")
try:
    res = at.session_state["resultado_final"]
except KeyError:
    res = None
check("resultado_final calculado en el timeout", res is not None)
if res:
    check("1 correcta", res["correctas"] == 1, f"-> {res}")
    check("la no respondida cuenta como incorrecta (modo examen)",
          res["incorrectas"] == 1 and res["no_respondidas"] == 0, f"-> {res}")
    check("total 2", res["total"] == 2)
    check("porcentaje 50", abs(res["porcentaje"] - 50.0) < 0.01, f"-> {res}")
check("muestra la pantalla de resultados",
      at.session_state["mostrar_resultados"] is True)

print("\n" + ("APPTEST OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
sys.exit(1 if fallos else 0)
