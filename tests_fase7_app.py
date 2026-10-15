"""AppTest Fase 7: test de práctica con las preguntas reiteradas.

Cubre:
1. La pestaña "🔁 Sección Errores Reiterados" ofrece un expander con la
   pregunta completa (enunciado íntegro + opciones del banco) solo para las
   reiteradas que siguen en el banco.
2. Las reiteradas que ya no están en el banco quedan excluidas del test y
   se avisa de ello por pantalla.
3. El botón "Hacer test de práctica" lanza el Simulador en modo Práctica
   (sin temporizador) solo con las reiteradas presentes en el banco.
4. Al finalizar ese test, el intento queda registrado en el historial.
"""
import json
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

tmp_home = tempfile.mkdtemp(prefix="vce_test_fase7app_")
os.environ["HOME"] = tmp_home
data_dir = os.path.join(tmp_home, ".local", "share", "WhyNeedAVCEApp")
os.makedirs(os.path.join(data_dir, "imagenes_preguntas"), exist_ok=True)
ARCHIVO = os.path.join(data_dir, "preguntas.json")
ARCHIVO_HISTORIAL = os.path.join(data_dir, "historial_fallos.json")

BANCO = [
    {"id": 1, "pregunta": "capital de Francia", "imagen": None, "tag": "geo",
     "opciones": ["A) Paris", "B) Madrid"], "correctas": ["B"]},
    {"id": 2, "pregunta": "dos mas dos", "imagen": None, "tag": "mates",
     "opciones": ["A) 3", "B) 4"], "correctas": ["B"]},
]
with open(ARCHIVO, "w", encoding="utf-8") as f:
    json.dump(BANCO, f)

from streamlit.testing.v1 import AppTest
from src.historial import (clave_pregunta, historial_vacio, registrar_examen,
                           guardar_historial)

# Dos exámenes anteriores: p1 (capital de Francia) fallada 2 veces -> reiterada,
# p2 acertada. Además una "fantasma" fallada 2 veces que ya no está en el banco.
historial = historial_vacio()
for _ in range(2):
    historial = registrar_examen(historial, BANCO, {0: ["A"], 1: ["B"]})
historial["preguntas"]["clave_fantasma"] = {
    "enunciado": "pregunta borrada del banco", "tag": "vieja", "id_actual": 99,
    "correctas": ["C"], "eventos": [
        {"fecha": "2026-01-01T10:00:00", "resultado": "fallo"},
        {"fecha": "2026-01-02T10:00:00", "resultado": "fallo"},
    ],
}
guardar_historial(ARCHIVO_HISTORIAL, historial)
clave_p1 = clave_pregunta(BANCO[0])

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

def contiene_markdown(at, texto):
    return any(texto.lower() in (m.value or "").lower() for m in at.markdown)

def contiene_caption(at, texto):
    return any(texto.lower() in (c.value or "").lower() for c in at.caption)


print("\n== Pestaña 5: tarjetas, expander y aviso de excluidas ==")
at = AppTest.from_file(os.path.join(REPO, "app.py"))
at.session_state["config_completed"] = True
at.session_state["pestana_actual"] = "🔁 Sección Errores Reiterados"
at.run()
check("pestaña sin excepciones", not at.exception)
check("metrica de examenes = 2",
      any(str(m.value).strip() == "2" for m in at.metric))
check("p1 listada como reiterada", contiene_markdown(at, "capital de Francia"))
check("fantasma marcada fuera del banco",
      contiene_markdown(at, "ya no está en el banco"))
check("aviso de excluidas del test", contiene_caption(at, "quedan fuera del test"))

expanders_pregunta = [e for e in at.expander
                      if "Ver pregunta completa" in (e.label or "")]
check("un expander solo para la reiterada del banco",
      len(expanders_pregunta) == 1, f"encontrados: {len(expanders_pregunta)}")

print("\n== Botón: lanza el Simulador en modo Práctica ==")
boton = next((b for b in at.button if "Hacer test de práctica" in (b.label or "")), None)
check("botón presente", boton is not None)
check("botón habilitado (hay reiteradas en el banco)",
      boton is not None and not bool(boton.disabled))
boton.click()
at.run()
check("sin excepciones tras lanzar", not at.exception)
check("salta a la pestaña Simulador", at.radio[0].value == "🎮 Simulador")
check("examen activo", ss(at, "simulador_activo") is True)
check("solo la reiterada del banco (fantasma excluida)",
      len(ss(at, "preguntas_simulador")) == 1)
check("modo Práctica sin temporizador",
      ss(at, "modo_examen") == "Práctica" and ss(at, "timer_activo") is False)
check("flag de historial listo para registrar",
      ss(at, "historial_examen_registrado") is False)
check("pregunta visible en pantalla", contiene_markdown(at, "capital de Francia"))

print("\n== Finalizar el test registra el intento ==")
preg = ss(at, "preguntas_simulador")[0]
at.checkbox(key=f"opt_0_{preg['correctas'][0]}").check()
at.run()
check("sin excepciones al responder", not at.exception)
check("botón Finalizar visible", click_por_texto(at, "Finalizar"))
at.run()
check("resultados visibles", ss(at, "mostrar_resultados") is True)
check("sin excepciones al finalizar", not at.exception)
with open(ARCHIVO_HISTORIAL, encoding="utf-8") as f:
    hist = json.load(f)
check("cuenta 3 examenes", hist.get("examenes") == 3)
ev1 = hist.get("preguntas", {}).get(clave_p1, {}).get("eventos", [])
check("p1 acumula 2 fallos + 1 correcta",
      [e["resultado"] for e in ev1] == ["fallo", "fallo", "correcta"])
check("fantasma intacta (sin eventos nuevos)",
      len(hist["preguntas"]["clave_fantasma"]["eventos"]) == 2)

print("\n" + ("APPTEST OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
sys.exit(1 if fallos else 0)
