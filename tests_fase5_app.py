"""AppTest Fase 5: bloqueo de avance en preguntas de respuesta múltiple.

Cubre:
1. Una pregunta con N respuestas correctas no deja avanzar (Siguiente ni
   Finalizar) hasta marcar exactamente N opciones, y muestra el aviso rojo
   "No puedes continuar aún".
2. El aviso ámbar de selección múltiple preexistente se mantiene.
3. Con selección en exceso (más de N) también se bloquea.
4. "⬅ Anterior" sigue permitido con la selección incompleta.
5. Las preguntas de respuesta única siguen permitiendo avanzar sin responder.

Nota: AppTest descarta el estado de los widgets que no se renderizan en un
run (navegar Anterior/Siguiente resetea los checkboxes), así que el estado
se re-marca explícitamente tras cada ida y vuelta.
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
    {"id": 1, "pregunta": "p1unica", "imagen": None, "tag": "",
     "opciones": ["A) x", "B) y"], "correctas": ["B"]},
    {"id": 2, "pregunta": "p2multiple", "imagen": None, "tag": "",
     "opciones": ["A) x", "B) y", "C) z"], "correctas": ["A", "B"]},
    {"id": 3, "pregunta": "p3unica", "imagen": None, "tag": "",
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

def contiene_markdown(at, texto):
    return any(texto.lower() in (m.value or "").lower() for m in at.markdown)

def ss(at, clave, default=None):
    try:
        return at.session_state[clave]
    except KeyError:
        return default


print("\n== Bloqueo de avance con selección múltiple incompleta ==")
at = AppTest.from_file(os.path.join(REPO, "app.py"))
at.session_state["config_completed"] = True
at.session_state["pestana_actual"] = "🎮 Simulador"
# Sin orden aleatorio el examen conserva el orden del banco:
# idx 0 = única, idx 1 = múltiple (2 de 3), idx 2 = única.
at.session_state["modo_aleatorio"] = False
at.run()
check("pantalla de configuración sin excepciones", not at.exception)

check("botón Iniciar Examen visible", click_por_texto(at, "Iniciar Examen"))
at.run()
check("examen activo tras iniciar", ss(at, "simulador_activo") is True)
check("sin excepciones al iniciar", not at.exception)

# idx 0: pregunta de respuesta ÚNICA sin responder -> sí puede avanzar (comportamiento previo).
check("Siguiente en única sin responder", click_por_texto(at, "Siguiente"))
at.run()
check("índice avanza a 1 (única no bloquea)", ss(at, "indice_actual") == 1)
check("sin excepciones al navegar", not at.exception)

# idx 1: múltiple. aleatorizar_pregunta() reordena y reetiqueta, así que las
# letras vigentes se leen del estado de sesión.
preg_m = ss(at, "preguntas_simulador")[1]
num_correctas = len(preg_m["correctas"])
letras = [op[0] for op in preg_m["opciones"]]
correctas = sorted(preg_m["correctas"])
incorrecta = [l for l in letras if l not in correctas][0]
check("aviso ámbar de selección múltiple visible",
      contiene_markdown(at, "SELECCIÓN MÚLTIPLE"))

# Solo 1 de 2 marcada -> Siguiente bloqueado + aviso rojo (faltan respuestas).
at.checkbox(key=f"opt_1_{correctas[0]}").check()
at.run()
check("Siguiente con 1 de 2 marcada", click_por_texto(at, "Siguiente"))
at.run()
check("índice sigue en 1 (bloqueado)", ss(at, "indice_actual") == 1)
check("aviso rojo 'No puedes continuar aún' visible",
      contiene_markdown(at, "No puedes continuar aún"))
check("bandera de aviso consumida al renderizar",
      ss(at, "aviso_bloqueo_multiple", None) is None)
check("sin excepciones al bloquear", not at.exception)

# Incompleta pero "⬅ Anterior" permitido (repasar hacia atrás no se bloquea).
check("Anterior permitido con selección incompleta", click_por_texto(at, "⬅ Anterior"))
at.run()
check("índice retrocede a 0", ss(at, "indice_actual") == 0)
check("Siguiente vuelve a la múltiple", click_por_texto(at, "Siguiente"))
at.run()
check("índice de nuevo en 1", ss(at, "indice_actual") == 1)

# Exceso: 3 de 2 marcadas -> también bloqueado, con mensaje de desmarcar.
for letra in letras:
    at.checkbox(key=f"opt_1_{letra}").check()
at.run()
check("Siguiente con 3 de 2 marcadas", click_por_texto(at, "Siguiente"))
at.run()
check("índice sigue en 1 (exceso bloqueado)", ss(at, "indice_actual") == 1)
check("aviso rojo visible con mensaje de exceso",
      contiene_markdown(at, "Desmarca"))
check("sin excepciones con exceso", not at.exception)

# Exactamente 2 (las correctas) -> avanza.
at.checkbox(key=f"opt_1_{incorrecta}").uncheck()
at.run()
check("Siguiente con 2 de 2 marcadas", click_por_texto(at, "Siguiente"))
at.run()
check("índice avanza a 2 (completa pasa)", ss(at, "indice_actual") == 2)
check("sin excepciones al completar", not at.exception)

# idx 2: única sin responder -> Finalizar permitido (comportamiento previo).
check("botón Finalizar visible", click_por_texto(at, "Finalizar"))
at.run()
check("pantalla de resultados activa", ss(at, "mostrar_resultados") is True)
res = ss(at, "resultado_final")
check("resultados calculados", res is not None and res["total"] == 3)
if res:
    check("1 correcta (la múltiple) y 2 no respondidas",
          res["correctas"] == 1 and res["no_respondidas"] == 2, f"-> {res}")
check("sin excepciones al finalizar", not at.exception)

print("\n" + ("APPTEST OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
sys.exit(1 if fallos else 0)
