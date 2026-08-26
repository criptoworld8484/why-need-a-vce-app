"""Tests Fase 2: ZIP endurecido (src/backup.py) y api_key_manager."""
import io
import json
import os
import shutil
import sys
import tempfile
import zipfile

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

import src.backup as backup

fallos = []
def check(nombre, cond, detalle=""):
    if cond:
        print(f"  PASS  {nombre}")
    else:
        print(f"  FAIL  {nombre} {detalle}")
        fallos.append(nombre)

def hacer_zip(miembros):
    """Crea bytes de ZIP con {nombre: contenido} dados."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for nombre, data in miembros.items():
            z.writestr(nombre, data)
    return buf.getvalue()


print("\n== Exportar / importar roundtrip ==")
d1 = tempfile.mkdtemp(prefix="vce_d1_")
d2 = tempfile.mkdtemp(prefix="vce_d2_")
os.makedirs(os.path.join(d1, "imagenes_preguntas"))
with open(os.path.join(d1, "imagenes_preguntas", "x.png"), "wb") as f:
    f.write(b"datos-png-falsos")

banco = [
    {"id": 1, "pregunta": "p1", "imagen": "imagenes_preguntas/x.png", "tag": "T",
     "opciones": ["A) x", "B) y"], "correctas": ["A"]},
    # imagen como ruta absoluta: debe relativizarse al exportar
    {"id": 2, "pregunta": "p2",
     "imagen": os.path.join(d1, "imagenes_preguntas", "x.png"), "tag": "",
     "opciones": ["A) x", "B) y"], "correctas": ["B"]},
]
zip_bytes = backup.export_questions_to_zip(banco, d1)
with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
    nombres = set(z.namelist())
check("el ZIP contiene preguntas.json y la imagen una sola vez",
      nombres == {"preguntas.json", "imagenes/x.png"}, f"-> {nombres}")
en_zip = json.loads(zipfile.ZipFile(io.BytesIO(zip_bytes)).read("preguntas.json"))
check("la imagen absoluta se exporto como relativa",
      all(p["imagen"] == "imagenes_preguntas/x.png" for p in en_zip),
      f"-> {[p['imagen'] for p in en_zip]}")

importadas = backup.import_questions_from_zip(zip_bytes, d2)
check("import devuelve la lista (no dict de error)",
      isinstance(importadas, list) and len(importadas) == 2, f"-> {importadas}")
check("la imagen se copio al data dir destino",
      os.path.exists(os.path.join(d2, "imagenes_preguntas", "x.png")))
check("las preguntas no se mutan en el export",
      banco[1]["imagen"].startswith(d1) or os.path.isabs(banco[1]["imagen"]))

print("\n== ZIPs invalidos ==")
r = backup.import_questions_from_zip(b"esto no es un zip", d2)
check("bytes basura -> dict de error", isinstance(r, dict) and "error" in r, f"-> {r}")
r = backup.import_questions_from_zip(
    hacer_zip({"otra_cosa.json": "[]"}), d2)
check("sin preguntas.json -> dict de error", isinstance(r, dict) and "error" in r, f"-> {r}")
r = backup.import_questions_from_zip(
    hacer_zip({"preguntas.json": "{no soy json"}), d2)
check("preguntas.json corrupto -> dict de error",
      isinstance(r, dict) and "error" in r, f"-> {r}")

print("\n== Zip bomb: topes de tamano ==")
lim_total_orig = backup.LIMITE_TOTAL_BYTES
lim_arch_orig = backup.LIMITE_ARCHIVO_BYTES
try:
    backup.LIMITE_TOTAL_BYTES = 100
    r = backup.import_questions_from_zip(
        hacer_zip({"preguntas.json": json.dumps(banco)}), d2)
    check("total descomprimido por encima del tope -> error",
          isinstance(r, dict) and "error" in r, f"-> {r}")

    backup.LIMITE_TOTAL_BYTES = lim_total_orig
    backup.LIMITE_ARCHIVO_BYTES = 10
    r = backup.import_questions_from_zip(
        hacer_zip({"preguntas.json": json.dumps(banco),
                   "imagenes/gorda.png": b"x" * 50}), d2)
    check("imagen individual por encima del tope -> error",
          isinstance(r, dict) and "error" in r, f"-> {r}")
    check("ante el error no se copia nada a medias",
          not os.path.exists(os.path.join(d2, "imagenes_preguntas", "gorda.png")))
finally:
    backup.LIMITE_TOTAL_BYTES = lim_total_orig
    backup.LIMITE_ARCHIVO_BYTES = lim_arch_orig

print("\n== Path traversal en nombres de miembros ==")
d3 = tempfile.mkdtemp(prefix="vce_d3_")
r = backup.import_questions_from_zip(
    hacer_zip({"preguntas.json": json.dumps(banco),
               "imagenes/../evil.png": b"malicioso"}), d3)
check("importa sin error", isinstance(r, list), f"-> {r}")
check("evil.png cae DENTRO de imagenes_preguntas (basename)",
      os.path.exists(os.path.join(d3, "imagenes_preguntas", "evil.png")))
check("nada escapa del data dir",
      not os.path.exists(os.path.join(d3, "evil.png")))

print("\n== api_key_manager: delete borra key y keyfile ==")
tmp_home = tempfile.mkdtemp(prefix="vce_home_")
os.environ["HOME"] = tmp_home
from src.api_key_manager import save_api_key, load_api_key, has_api_key, delete_api_key
from src.paths import get_config_dir

check("sin key al principio", has_api_key() is False)
check("save_api_key funciona", save_api_key("AIzaSyFAKE-123") is True)
check("has_api_key la detecta", has_api_key() is True)
keyfile = os.path.join(get_config_dir(), ".keyfile")
check("la keyfile existe junto a la key", os.path.exists(keyfile))
check("load_api_key devuelve la clave", load_api_key() == "AIzaSyFAKE-123")
check("delete_api_key funciona", delete_api_key() is True)
check("key eliminada", has_api_key() is False)
check("la keyfile huerfana tambien se elimina", not os.path.exists(keyfile))

shutil.rmtree(d1, ignore_errors=True)
shutil.rmtree(d2, ignore_errors=True)
shutil.rmtree(d3, ignore_errors=True)
shutil.rmtree(tmp_home, ignore_errors=True)

print("\n" + ("TODOS OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
sys.exit(1 if fallos else 0)
