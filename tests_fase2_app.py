"""AppTest Fase 2: JSON corrupto se respalda como .corrupta_* y no crashea.

Antes load_questions tragaba el JSONDecodeError devolviendo [] y el
siguiente guardado machacaba el archivo del usuario sin posibilidad de
recuperacion. Ahora se renombra a preguntas.json.corrupta_<ts>.
"""
import glob
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

tmp_home = tempfile.mkdtemp(prefix="vce_test_fase2_")
os.environ["HOME"] = tmp_home
data_dir = os.path.join(tmp_home, ".local", "share", "WhyNeedAVCEApp")
os.makedirs(os.path.join(data_dir, "imagenes_preguntas"), exist_ok=True)
archivo = os.path.join(data_dir, "preguntas.json")
with open(archivo, "w", encoding="utf-8") as f:
    f.write('{ esto no es json valido')

from streamlit.testing.v1 import AppTest

at = AppTest.from_file(os.path.join(REPO, "app.py"))
at.session_state["config_completed"] = True
at.run()

fallos = []
def check(nombre, cond, detalle=""):
    print(("  PASS  " if cond else "  FAIL  ") + nombre + ("" if cond else f" {detalle}"))
    if not cond:
        fallos.append(nombre)

check("la app no crashea con un preguntas.json corrupto",
      not at.exception, f"-> {[str(e.value) for e in at.exception]}")
backups = glob.glob(archivo + ".corrupta_*")
check("se creo un backup .corrupta_*", len(backups) == 1, f"-> {backups}")
if backups:
    with open(backups[0], "r", encoding="utf-8") as f:
        check("el backup conserva el contenido corrupto original",
              f.read() == "{ esto no es json valido")
check("el banco se trata como vacio (sin preguntas.json activo)",
      not os.path.exists(archivo))

print("\n" + ("APPTEST OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
sys.exit(1 if fallos else 0)
