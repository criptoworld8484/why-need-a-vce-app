"""AppTest Fase 3: flujo completo del simulador y export ZIP bajo demanda.

Cubre:
1. Config -> iniciar examen -> responder -> navegar -> finalizar -> resultados
   (sin time.sleep que frene y sin excepciones).
2. El ZIP de exportacion NO se construye en cada rerun: solo al pulsar
   "Generar backup ZIP", y se invalida si el banco cambia en disco.
"""
import json
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

tmp_home = tempfile.mkdtemp(prefix="vce_test_fase3_")
os.environ["HOME"] = tmp_home
data_dir = os.path.join(tmp_home, ".local", "share", "WhyNeedAVCEApp")
os.makedirs(os.path.join(data_dir, "imagenes_preguntas"), exist_ok=True)
ARCHIVO = os.path.join(data_dir, "preguntas.json")

BANCO = [
    {"id": 1, "pregunta": "p1", "imagen": None, "tag": "",
     "opciones": ["A) x", "B) y"], "correctas": ["A"]},
    {"id": 2, "pregunta": "p2", "imagen": None, "tag": "",
     "opciones": ["A) x", "B) y"], "correctas": ["B"]},
]
with open(ARCHIVO, "w", encoding="utf-8") as f:
    json.dump(BANCO, f)

from streamlit.testing.v1 import AppTest

fallos = []
def check(nombre, cond, detalle=""):
    print(("  PASS  " if cond else "  FAIL  ") + nombre + ("" if cond else f" {detalle}"))
    if not cond:
        fallos.append(nombre)

def click_por_texto(at, texto):
    for b in at.button:
        if texto in (b.label or ""):
            b.click()
            return True
    return False

def ss(at, clave, default=None):
    try:
        return at.session_state[clave]
    except KeyError:
        return default


print("\n== Flujo completo del simulador (modo practica) ==")
at = AppTest.from_file(os.path.join(REPO, "app.py"))
at.session_state["config_completed"] = True
at.session_state["pestana_actual"] = "🎮 Simulador"
at.run()
check("pantalla de configuracion sin excepciones",
      not at.exception and ss(at, "simulador_activo") is not True)

check("boton Iniciar Examen visible", click_por_texto(at, "Iniciar Examen"))
at.run()
check("examen activo tras iniciar", ss(at, "simulador_activo") is True)
check("2 preguntas en el examen", len(ss(at, "preguntas_simulador", [])) == 2)
check("sin excepciones al iniciar", not at.exception)

# Con "Orden aleatorio" activo (default) el sample puede invertir el orden:
# se marca la letra correcta de la pregunta que haya caído en el indice 0.
preg0 = ss(at, "preguntas_simulador")[0]
letra_correcta_0 = preg0["correctas"][0]
at.checkbox(key=f"opt_0_{letra_correcta_0}").check()
at.run()
check("respuesta registrada al marcar checkbox",
      ss(at, "respuestas_usuario", {}).get(0) == [letra_correcta_0])

check("boton Siguiente visible", click_por_texto(at, "Siguiente"))
at.run()
check("indice avanza a 1", ss(at, "indice_actual") == 1)
check("sin excepciones al navegar", not at.exception)

check("boton Finalizar visible", click_por_texto(at, "Finalizar"))
at.run()
check("pantalla de resultados activa", ss(at, "mostrar_resultados") is True)
res = ss(at, "resultado_final")
check("resultados calculados", res is not None and res["total"] == 2)
if res:
    check("1 correcta / 1 no respondida (practica)",
          res["correctas"] == 1 and res["no_respondidas"] == 1, f"-> {res}")
check("sin excepciones al finalizar", not at.exception)

print("\n== Export ZIP bajo demanda ==")
at2 = AppTest.from_file(os.path.join(REPO, "app.py"))
at2.session_state["config_completed"] = True
at2.session_state["pestana_actual"] = "📊 Ver Preguntas"
at2.run()
check("Ver Preguntas sin excepciones", not at2.exception)
check("el ZIP NO se construye solo con renderizar",
      ss(at2, "zip_export_data") is None)

at2.button(key="gen_zip").click()
at2.run()
zip_data = ss(at2, "zip_export_data")
check("el ZIP se construye al pulsar Generar",
      isinstance(zip_data, (bytes, bytearray)) and len(zip_data) > 0)
check("los bytes son un ZIP real (firma PK)",
      isinstance(zip_data, (bytes, bytearray)) and bytes(zip_data[:2]) == b"PK")

# Invalidacion: el banco cambia en disco -> el ZIP guardado caduca.
BANCO.append({"id": 3, "pregunta": "p3", "imagen": None, "tag": "",
              "opciones": ["A) x", "B) y"], "correctas": ["A"]})
with open(ARCHIVO, "w", encoding="utf-8") as f:
    json.dump(BANCO, f)
at2.run()
check("el ZIP caduca cuando cambia el banco en disco",
      ss(at2, "zip_export_data") is None)

print("\n" + ("APPTEST OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
sys.exit(1 if fallos else 0)
