"""AppTest Fase 4: purga de imagenes al borrar pregunta + metrica no respondidas."""
import json
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

tmp_home = tempfile.mkdtemp(prefix="vce_test_fase4_")
os.environ["HOME"] = tmp_home
data_dir = os.path.join(tmp_home, ".local", "share", "WhyNeedAVCEApp")
carpeta_imgs = os.path.join(data_dir, "imagenes_preguntas")
os.makedirs(carpeta_imgs, exist_ok=True)
ARCHIVO = os.path.join(data_dir, "preguntas.json")

# Banco: la pregunta 1 con imagen propia, la 2 con imagen compartida con la 1,
# la 3 sin imagen, y una imagen huerfana preexistente. PNGs reales de 1x1:
# st.image los abre con PIL y un PNG falso lanza UnidentifiedImageError.
import io
from PIL import Image

def png_1x1():
    buf = io.BytesIO()
    Image.new("RGB", (1, 1), color=(255, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()

for nombre in ("img_q1.png", "img_q2.png", "huerfana_vieja.png"):
    with open(os.path.join(carpeta_imgs, nombre), "wb") as f:
        f.write(png_1x1())

BANCO = [
    {"id": 1, "pregunta": "p1", "imagen": "imagenes_preguntas/img_q1.png", "tag": "",
     "opciones": ["A) x", "B) y"], "correctas": ["A"]},
    {"id": 2, "pregunta": "p2", "imagen": "imagenes_preguntas/img_q1.png", "tag": "",
     "opciones": ["A) x", "B) y"], "correctas": ["A"]},
    {"id": 3, "pregunta": "p3", "imagen": None, "tag": "",
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

def ss(at, clave, default=None):
    try:
        return at.session_state[clave]
    except KeyError:
        return default


def app_ver_preguntas():
    """AppTest fresco en Ver Preguntas.

    Se re-crea por cada borrado: tras eliminar una pregunta sus widgets
    (tag_edit_*) desaparecen y reutilizar la misma instancia AppTest lanza
    KeyError al serializar el arbol anterior (limitacion del harness, no de
    la app). El banco vive en disco, asi que el estado persiste igual.
    """
    at = AppTest.from_file(os.path.join(REPO, "app.py"))
    at.session_state["config_completed"] = True
    at.session_state["pestana_actual"] = "📊 Ver Preguntas"
    at.run()
    return at


def click_texto(at, texto):
    for b in at.button:
        if texto in (b.label or ""):
            b.click()
            return True
    return False


def app_simulador():
    at = AppTest.from_file(os.path.join(REPO, "app.py"))
    at.session_state["config_completed"] = True
    at.session_state["pestana_actual"] = "🎮 Simulador"
    at.run()
    return at


# NOTA de orden: las secciones de resultados van ANTES que los borrados.
# Escribir el banco a mano a mitad de test no invalida la cache
# @st.cache_data(ttl=10) de load_questions y el simulador veria un banco
# vacio; los caminos de la app (que si invalidan) son los unicos que mutan
# el banco durante el test.

print("\n== Resultados con no respondidas: metrica visible ==")
at2 = app_simulador()
click_texto(at2, "Iniciar Examen")
at2.run()
# Responder todas menos la ultima: esa queda no respondida (modo practica).
psim = ss(at2, "preguntas_simulador")
check("examen iniciado con 3 preguntas", psim is not None and len(psim) == 3)
for i, preg in enumerate(psim):
    if i < len(psim) - 1:
        at2.checkbox(key=f"opt_{i}_{preg['correctas'][0]}").check()
        at2.run()
        click_texto(at2, "Siguiente")
        at2.run()
click_texto(at2, "Finalizar")
at2.run()
check("resultados sin excepciones", not at2.exception)
res = ss(at2, "resultado_final")
check("hay 1 no respondida (practica)",
      res is not None and res["no_respondidas"] == 1, f"-> {res}")
labels = [m.label for m in at2.metric]
check("la metrica 'No respondidas' aparece",
      any("No respondidas" in (l or "") for l in labels), f"-> {labels}")

print("\n== Resultados sin no respondidas: sin metrica extra ==")
at3 = app_simulador()
click_texto(at3, "Iniciar Examen")
at3.run()
psim = ss(at3, "preguntas_simulador")
for i, preg in enumerate(psim):  # responder todas
    at3.checkbox(key=f"opt_{i}_{preg['correctas'][0]}").check()
    at3.run()
    if i < len(psim) - 1:
        click_texto(at3, "Siguiente")
        at3.run()
click_texto(at3, "Finalizar")
at3.run()
check("resultados sin excepciones", not at3.exception)
res3 = ss(at3, "resultado_final")
check("no hay no respondidas", res3 is not None and res3["no_respondidas"] == 0,
      f"-> {res3}")
labels3 = [m.label for m in at3.metric]
check("la metrica 'No respondidas' NO aparece",
      not any("No respondidas" in (l or "") for l in labels3), f"-> {labels3}")

print("\n== Borrar pregunta 3 (sin imagen): nada que purgar ==")
at = app_ver_preguntas()
check("Ver Preguntas sin excepciones", not at.exception)

at.button(key="del_3").click()
at.run()
check("sin excepciones tras borrar", not at.exception)
with open(ARCHIVO, encoding="utf-8") as f:
    ids = [p["id"] for p in json.load(f)]
check("la pregunta 3 desaparece del banco", ids == [1, 2], f"-> {ids}")
# La purga del borrado individual se limita a la imagen de la pregunta
# borrada (ninguna): ni las huérfanas preexistentes se tocan.
check("ninguna imagen se toca al borrar una pregunta sin imagen",
      sorted(os.listdir(carpeta_imgs)) ==
      ["huerfana_vieja.png", "img_q1.png", "img_q2.png"])

print("\n== Borrar pregunta 2: img_q1 la usa la 1 -> NO se purga ==")
at = app_ver_preguntas()
at.button(key="del_2").click()
at.run()
check("sin excepciones tras borrar", not at.exception)
check("img_q1 sobrevive (compartida con la 1)",
      os.path.exists(os.path.join(carpeta_imgs, "img_q1.png")))
check("las huérfanas ajenas tampoco se tocan (limitar_a)",
      os.path.exists(os.path.join(carpeta_imgs, "img_q2.png"))
      and os.path.exists(os.path.join(carpeta_imgs, "huerfana_vieja.png")))

print("\n== Borrar pregunta 1: img_q1 ya sin referencias -> se purga ==")
at = app_ver_preguntas()
at.button(key="del_1").click()
at.run()
check("sin excepciones tras borrar", not at.exception)
check("img_q1 se purga al quedar huerfana",
      not os.path.exists(os.path.join(carpeta_imgs, "img_q1.png")))
check("las huérfanas preexistentes siguen (solo las toca una purga global)",
      os.path.exists(os.path.join(carpeta_imgs, "img_q2.png")))

print("\n" + ("APPTEST OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
sys.exit(1 if fallos else 0)
