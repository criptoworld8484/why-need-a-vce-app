"""AppTest Fase 6: historial de fallos reiteradas (end-to-end).

Cubre:
1. Al finalizar un examen se registra el historial en disco: un evento por
   pregunta (fallo para todo lo no acertado).
2. El mini-resumen del reporte final solo aparece cuando una pregunta del
   examen acumula 2+ fallos.
3. La pestaña "🔁 Sección Errores Reiterados" lista las preguntas reiteradas con sus
   respuestas correctas; el umbral y la ventana temporal filtran.
4. El botón de reset (con confirmación en 2 pasos) borra el historial.
"""
import json
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

tmp_home = tempfile.mkdtemp(prefix="vce_test_fase6app_")
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
from src.historial import clave_pregunta

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

def contiene_info(at, texto):
    return any(texto.lower() in (i.value or "").lower() for i in at.info)

def contiene_markdown(at, texto):
    return any(texto.lower() in (m.value or "").lower() for m in at.markdown)

def contiene_exito(at, texto):
    return any(texto.lower() in (s.value or "").lower() for s in at.success)

def responder_examen(at):
    """Fallar la pregunta 0 y acertar la 1; finalizar."""
    total = len(ss(at, "preguntas_simulador"))
    for idx in (0, 1):
        preg = ss(at, "preguntas_simulador")[idx]
        letras = [op[0] for op in preg["opciones"]]
        if idx == 0:
            marca = next(l for l in letras if l not in preg["correctas"])
        else:
            marca = preg["correctas"][0]
        at.checkbox(key=f"opt_{idx}_{marca}").check()
        at.run()
        click_por_texto(at, "Siguiente" if idx < total - 1 else "Finalizar")
        at.run()

def iniciar_examen(at):
    check("boton Iniciar Examen visible", click_por_texto(at, "Iniciar Examen"))
    at.run()
    return ss(at, "simulador_activo") is True and not at.exception


print("\n== Examen 1: registro del historial en disco ==")
at = AppTest.from_file(os.path.join(REPO, "app.py"))
at.session_state["config_completed"] = True
at.session_state["pestana_actual"] = "🎮 Simulador"
at.session_state["modo_aleatorio"] = False
at.run()
check("configuracion sin excepciones", not at.exception)

check("examen 1 iniciado", iniciar_examen(at))
responder_examen(at)
check("examen 1 finalizado", ss(at, "mostrar_resultados") is True)
check("sin excepciones al finalizar", not at.exception)

check("historial creado en disco", os.path.exists(ARCHIVO_HISTORIAL))
with open(ARCHIVO_HISTORIAL, encoding="utf-8") as f:
    hist = json.load(f)
clave_p1 = clave_pregunta(ss(at, "preguntas_simulador")[0])
clave_p2 = clave_pregunta(ss(at, "preguntas_simulador")[1])
check("cuenta 1 examen", hist.get("examenes") == 1)
ev1 = hist.get("preguntas", {}).get(clave_p1, {}).get("eventos", [])
check("p1 (fallada) registra 1 fallo",
      len(ev1) == 1 and ev1[0]["resultado"] == "fallo")
ev2 = hist.get("preguntas", {}).get(clave_p2, {}).get("eventos", [])
check("p2 (acertada) registra correcta",
      len(ev2) == 1 and ev2[0]["resultado"] == "correcta")
check("snapshot con tag y correctas",
      hist["preguntas"][clave_p1].get("tag") == "geo"
      and hist["preguntas"][clave_p1].get("correctas") == ss(at, "preguntas_simulador")[0]["correctas"])
check("mini-resumen ausente con solo 1 fallo", not contiene_info(at, "reiterada"))

print("\n== Examen 2: mismo fallo -> reiterada ==")
check("volver a configuracion", click_por_texto(at, "Nuevo Examen"))
at.run()
check("examen 2 iniciado", iniciar_examen(at))
responder_examen(at)
check("examen 2 finalizado", ss(at, "mostrar_resultados") is True)
check("sin excepciones en el 2º cierre", not at.exception)
with open(ARCHIVO_HISTORIAL, encoding="utf-8") as f:
    hist = json.load(f)
check("cuenta 2 examenes", hist.get("examenes") == 2)
ev1 = hist["preguntas"][clave_p1]["eventos"]
check("p1 acumula 2 fallos", len(ev1) == 2 and all(e["resultado"] == "fallo" for e in ev1))
check("flag de registro consumido una vez por examen",
      ss(at, "historial_examen_registrado") is True)
check("mini-resumen presente con 2 fallos", contiene_info(at, "reiterada"))

print("\n== Pestaña Sección Errores Reiterados ==")
at.radio[0].set_value("🔁 Sección Errores Reiterados")
at.run()
check("pestaña sin excepciones", not at.exception)
check("metrica de examenes = 2",
      any(str(m.value).strip() == "2" for m in at.metric))
check("p1 listada como reiterada", contiene_markdown(at, "capital de Francia"))
check("p2 no aparece (nunca fallada)", not contiene_markdown(at, "dos mas dos"))
check("muestra las respuestas correctas", contiene_markdown(at, "Respuesta(s) correcta(s)"))
check("sigue en el banco (sin aviso)", not contiene_markdown(at, "ya no está en el banco"))

at.slider(key="reiteradas_umbral").set_value(3)
at.run()
check("umbral 3 vacia el listado", contiene_exito(at, "Ninguna pregunta alcanza 3"))
at.slider(key="reiteradas_umbral").set_value(2)
at.run()
at.selectbox(key="reiteradas_ventana").set_value("Últimos 7 días")
at.run()
check("ventana de 7 dias mantiene la reiterada", contiene_markdown(at, "capital de Francia"))

print("\n== Reset con confirmacion ==")
boton_reset = next((b for b in at.button if "Reiniciar historial" in (b.label or "")), None)
check("boton de reset presente", boton_reset is not None)
check("boton deshabilitado sin confirmar", bool(boton_reset.disabled))
at.checkbox(key="confirmar_reset_historial").check()
at.run()
boton_reset = next((b for b in at.button if "Reiniciar historial" in (b.label or "")), None)
check("boton habilitado tras confirmar", not bool(boton_reset.disabled))
boton_reset.click()
at.run()
check("historial borrado de disco", not os.path.exists(ARCHIVO_HISTORIAL))
check("vista vacia tras el reset", contiene_info(at, "Aún no hay exámenes registrados"))
check("metrica de examenes = 0",
      any(str(m.value).strip() == "0" for m in at.metric))
check("sin excepciones tras el reset", not at.exception)

print("\n" + ("APPTEST OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
sys.exit(1 if fallos else 0)
