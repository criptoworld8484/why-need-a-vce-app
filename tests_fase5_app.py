"""AppTest Fase 5: editor de preguntas en "Ver Preguntas".

Cubre:
1. Abrir el editor desde una pregunta guardada (siembra de valores del
   banco, no de una sesion de edicion anterior).
2. Corregir la respuesta correcta (A->B) y editar el enunciado: el banco
   en disco se actualiza conservando id/imagen/tag y sin tocar el resto.
3. Validacion: guardar sin ninguna correcta muestra error y no toca el
   banco.
4. Cancelar cierra el editor, limpia las claves y no modifica el banco.
5. Con "Aleatorizar" activo el editor trabaja sobre la pregunta original.
"""
import json
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

tmp_home = tempfile.mkdtemp(prefix="vce_test_fase5_")
os.environ["HOME"] = tmp_home
data_dir = os.path.join(tmp_home, ".local", "share", "WhyNeedAVCEApp")
os.makedirs(os.path.join(data_dir, "imagenes_preguntas"), exist_ok=True)
ARCHIVO = os.path.join(data_dir, "preguntas.json")

BANCO = [
    {"id": 1, "pregunta": "p1", "imagen": None, "tag": "vendor1",
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

def leer_banco():
    with open(ARCHIVO, "r", encoding="utf-8") as f:
        return json.load(f)

def abrir_ver_preguntas():
    at = AppTest.from_file(os.path.join(REPO, "app.py"))
    at.session_state["config_completed"] = True
    at.session_state["pestana_actual"] = "📊 Ver Preguntas"
    at.run()
    return at


print("\n== Abrir editor ==")
at = abrir_ver_preguntas()
check("Ver Preguntas sin excepciones", not at.exception)
check("boton Editar presente", at.button(key="edit_1") is not None)

at.button(key="edit_1").click()
at.run()
check("editor abierto sin excepciones", not at.exception)
check("flag editando_1 activo", ss(at, "editando_1") is True)
check("enunciado sembrado", at.text_area(key="edit_enun_1").value == "p1")
check("opcion A sembrada", at.text_input(key="edit_texto_A_1").value == "x")
check("correcta A marcada", at.checkbox(key="edit_corr_A_1").value is True)
check("correcta B desmarcada", at.checkbox(key="edit_corr_B_1").value is False)


print("\n== Guardar: corregir respuesta A->B y enunciado ==")
at.checkbox(key="edit_corr_A_1").uncheck()
at.checkbox(key="edit_corr_B_1").check()
at.text_area(key="edit_enun_1").set_value("p1 corregida")
at.run()
check("sin excepciones al editar valores", not at.exception)

check("boton Guardar visible", click_por_texto(at, "Guardar cambios"))
at.run()
check("guardar sin excepciones", not at.exception)

banco = leer_banco()
p1 = banco[0]
check("correctas actualizada a B", p1["correctas"] == ["B"], f"-> {p1['correctas']}")
check("enunciado actualizado", p1["pregunta"] == "p1 corregida")
check("opciones reconstruidas", p1["opciones"] == ["A) x", "B) y"])
check("id conservado", p1["id"] == 1)
check("tag conservado", p1["tag"] == "vendor1")
check("imagen conservada", p1["imagen"] is None)
check("pregunta 2 intacta", banco[1] == BANCO[1])
check("editor cerrado tras guardar", ss(at, "editando_1") is None)


print("\n== Validacion: guardar sin correctas ==")
at2 = abrir_ver_preguntas()
at2.button(key="edit_1").click()
at2.run()
at2.checkbox(key="edit_corr_B_1").uncheck()
at2.run()
antes = leer_banco()

check("boton Guardar visible", click_por_texto(at2, "Guardar cambios"))
at2.run()
check("error de validacion visible", len(at2.error) > 0)
check("banco sin cambios", leer_banco() == antes)
check("editor sigue abierto", ss(at2, "editando_1") is True)


print("\n== Cancelar ==")
at3 = abrir_ver_preguntas()
at3.button(key="edit_1").click()
at3.run()
at3.text_input(key="edit_texto_A_1").set_value("texto alterado")
at3.run()
antes = leer_banco()

check("boton Cancelar visible", click_por_texto(at3, "Cancelar"))
at3.run()
check("cancelar sin excepciones", not at3.exception)
check("editor cerrado tras cancelar", ss(at3, "editando_1") is None)
check("banco sin cambios tras cancelar", leer_banco() == antes)
check("claves del editor limpiadas", ss(at3, "edit_texto_A_1") is None)

# Reabrir debe re-sembrar desde el banco, no desde la edicion cancelada.
at3.button(key="edit_1").click()
at3.run()
check("reapertura muestra valores del banco",
      at3.text_input(key="edit_texto_A_1").value == "x")


print("\n== Aleatorizar no contamina la edicion ==")
at4 = abrir_ver_preguntas()
at4.checkbox(key="mostrar_aleatorio").check()
at4.run()
at4.button(key="edit_1").click()
at4.run()
check("editor abre con aleatorizar activo", not at4.exception)
check("editor muestra la pregunta original",
      at4.text_area(key="edit_enun_1").value == "p1 corregida")
check("boton Guardar visible", click_por_texto(at4, "Guardar cambios"))
at4.run()
check("guardar sin cambios no reordena el banco",
      leer_banco()[0]["opciones"] == ["A) x", "B) y"])
check("sin excepciones al final", not at4.exception)

print("\n" + ("APPTEST OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
sys.exit(1 if fallos else 0)
