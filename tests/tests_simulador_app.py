"""AppTest de la entrega anticipada del simulador (botón Terminar examen).

Cubre:
1. El botón "Terminar examen" está disponible en cualquier pregunta.
2. Pide confirmación antes de entregar.
3. Al confirmar, el reporte sale sin contar las no respondidas como erróneas.
4. El historial de fallos no registra las no respondidas en la entrega anticipada.
"""
import json
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

tmp_home = tempfile.mkdtemp(prefix="vce_test_simuladorapp_")
os.environ["HOME"] = tmp_home
data_dir = os.path.join(tmp_home, ".local", "share", "WhyNeedAVCEApp")
os.makedirs(os.path.join(data_dir, "imagenes_preguntas"), exist_ok=True)
ARCHIVO = os.path.join(data_dir, "preguntas.json")
ARCHIVO_HISTORIAL = os.path.join(data_dir, "historial_fallos.json")

BANCO = [
    {"id": 1, "pregunta": "p1", "imagen": None, "tag": "",
     "opciones": ["A) x", "B) y"], "correctas": ["A"]},
    {"id": 2, "pregunta": "p2", "imagen": None, "tag": "",
     "opciones": ["A) x", "B) y"], "correctas": ["B"]},
    {"id": 3, "pregunta": "p3", "imagen": None, "tag": "",
     "opciones": ["A) x", "B) y"], "correctas": ["A"]},
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


print("== Entrega anticipada desde la primera pregunta ==")
at = AppTest.from_file(os.path.join(REPO, "app.py"))
at.session_state["config_completed"] = True
at.session_state["pestana_actual"] = "🎮 Simulador"
at.run()
check("sin excepciones en la pantalla del simulador", not at.exception)
check("boton Iniciar Examen visible", click_por_texto(at, "Iniciar Examen"))
at.run()
check("examen activo con 3 preguntas",
      ss(at, "simulador_activo") is True and len(ss(at, "preguntas_simulador", [])) == 3)

# Responder solo la pregunta 0 (con Orden aleatorio se usa su letra correcta)
preg0 = ss(at, "preguntas_simulador")[0]
letra_correcta_0 = preg0["correctas"][0]
at.checkbox(key=f"opt_0_{letra_correcta_0}").check()
at.run()
check("respuesta registrada", ss(at, "respuestas_usuario", {}).get(0) == [letra_correcta_0])

check("boton Terminar examen visible en la primera pregunta",
      click_por_texto(at, "Terminar examen"))
at.run()
check("pide confirmacion y no entrega todavia",
      ss(at, "confirmar_terminar_examen") is True
      and ss(at, "mostrar_resultados") is not True)
check("boton Seguir contestando visible",
      click_por_texto(at, "Seguir contestando"))
at.run()
check("cancelar la confirmacion vuelve a la pregunta",
      ss(at, "confirmar_terminar_examen") is not True
      and ss(at, "mostrar_resultados") is not True)

check("boton Terminar examen visible otra vez", click_por_texto(at, "Terminar examen"))
at.run()
check("boton Si, terminar visible", click_por_texto(at, "Sí, terminar"))
at.run()
check("pantalla de resultados activa", ss(at, "mostrar_resultados") is True)
res = ss(at, "resultado_final")
check("reporte sin contar no respondidas como erróneas",
      res is not None and res["total"] == 3 and res["correctas"] == 1
      and res["incorrectas"] == 0 and res["no_respondidas"] == 2,
      f"-> {res}")
check("sin excepciones al entregar", not at.exception)

if os.path.exists(ARCHIVO_HISTORIAL):
    with open(ARCHIVO_HISTORIAL, encoding="utf-8") as f:
        historial = json.load(f)
    eventos = sum(len(d.get("eventos", [])) for d in historial.get("preguntas", {}).values())
else:
    eventos = -1
check("historial: solo la respondida registra evento (las no respondidas no son fallo)",
      eventos == 1, f"-> eventos={eventos}")

print("\n== Ver respuesta correcta en modo Practica ==")
at2 = AppTest.from_file(os.path.join(REPO, "app.py"))
at2.session_state["config_completed"] = True
at2.session_state["pestana_actual"] = "🎮 Simulador"
at2.run()
check("boton Iniciar Examen visible", click_por_texto(at2, "Iniciar Examen"))
at2.run()
preg0b = ss(at2, "preguntas_simulador")[0]
check("boton Ver respuesta correcta visible", click_por_texto(at2, "Ver respuesta correcta"))
at2.run()
check("la pregunta queda marcada como revelada",
      0 in ss(at2, "respuestas_reveladas", set()),
      f"-> {ss(at2, 'respuestas_reveladas', set())}")
check("se muestra la letra correcta",
      any(preg0b["correctas"][0] in (s.value or "") for s in at2.success))
check("sin excepciones al revelar", not at2.exception)

print("\n== Ver respuesta correcta en modo Examen ==")
at3 = AppTest.from_file(os.path.join(REPO, "app.py"))
at3.session_state["config_completed"] = True
at3.session_state["pestana_actual"] = "🎮 Simulador"
at3.run()
for r in at3.radio:
    if "Examen" in (r.options or []):
        r.set_value("Examen")
at3.run()
check("boton Iniciar Examen visible en modo Examen", click_por_texto(at3, "Iniciar Examen"))
at3.run()
preg0c = ss(at3, "preguntas_simulador")[0]
check("el timer esta activo en modo Examen", ss(at3, "timer_activo") is True)
check("boton Ver respuesta correcta visible en modo Examen",
      click_por_texto(at3, "Ver respuesta correcta"))
at3.run()
check("revelado tambien en modo Examen",
      0 in ss(at3, "respuestas_reveladas", set())
      and any(preg0c["correctas"][0] in (s.value or "") for s in at3.success))
check("sin excepciones en modo Examen", not at3.exception)

print("\n== Reporte de entrega anticipada: solo contestadas ==")
import re as _re
cabeceras = [m.value for m in at.markdown
             if getattr(m, "value", None)
             and _re.search(r"Pregunta \d+ - (CORRECTA|INCORRECTA|PARCIAL)", m.value)]
check("el reporte lista solo la pregunta contestada",
      len(cabeceras) == 1 and "Pregunta 1 -" in cabeceras[0], f"-> {cabeceras}")
check("avisa de las preguntas omitidas",
      any("no se muestran" in (getattr(m, "value", None) or "")
          for m in list(at.markdown) + list(getattr(at, "caption", []))))

print("\n" + ("TODOS OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
sys.exit(1 if fallos else 0)
