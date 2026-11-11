"""Tests de consistencia tras retirar el pipeline de empaquetado.

Invariantes:
1. Ningun archivo del repositorio referencia los scripts eliminados
   (build_installer.bat, setup.iss, build/*, MyVCE_Certificacion, dist/MyVCE).
2. instalar.bat / iniciar.bat solo referencian ficheros que existen en el repo.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

fallos = []


def check(desc, cond, detail=""):
    marca = "OK " if cond else "FAIL"
    print(f"  [{marca}] {desc} {detail}")
    if not cond:
        fallos.append(desc)


BANEADOS = ("build_installer", "setup.iss", "build/build_", "build\\build_",
            "MyVCE_Certificacion", "dist/MyVCE")
EXTENSIONES = (".md", ".py", ".bat", ".toml", ".txt")
OMITIR_DIRS = {".git", ".venv", "venv", "__pycache__", ".atl", ".claude",
               ".streamlit", ".idea", ".vscode"}
ESTE_ARCHIVO = os.path.basename(__file__)


def _archivos_del_repo():
    for dirpath, dirnames, nombres in os.walk(REPO):
        dirnames[:] = [d for d in dirnames if d not in OMITIR_DIRS]
        for nombre in nombres:
            if nombre == ESTE_ARCHIVO:
                continue
            if nombre.endswith(EXTENSIONES):
                yield os.path.join(dirpath, nombre)


print("== referencias a los scripts eliminados ==")
referencias_colgantes = []
for ruta in _archivos_del_repo():
    with open(ruta, encoding="utf-8", errors="ignore") as f:
        contenido = f.read()
    for baneado in BANEADOS:
        if baneado in contenido:
            referencias_colgantes.append(f"{os.path.relpath(ruta, REPO)} -> {baneado}")
check("ningun archivo referencia el pipeline eliminado",
      not referencias_colgantes, f"-> {referencias_colgantes}")

print("\n== consistencia de instalar.bat / iniciar.bat ==")
for bat in ("instalar.bat", "iniciar.bat"):
    ruta = os.path.join(REPO, bat)
    check(f"{bat} existe", os.path.exists(ruta))
    with open(ruta, encoding="utf-8") as f:
        contenido = f.read()
    # Quitar URLs (www.py de https://www...) y el prefijo batch %~dp0 antes
    # de buscar referencias a ficheros del repo
    contenido = re.sub(r"https?://\S+", "", contenido)
    contenido = contenido.replace("%~dp0", "")
    referencias = set(re.findall(r"[\w.-]+\.(?:bat|txt|py)", contenido))
    # .venv se crea en runtime; python/pip son binarios, no ficheros del repo
    referencias -= {"python.exe"}
    faltantes = [r for r in sorted(referencias)
                 if not os.path.exists(os.path.join(REPO, r))]
    check(f"{bat} solo referencia ficheros existentes",
          not faltantes, f"-> faltan: {faltantes}")

print("\n" + ("TODOS OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
sys.exit(1 if fallos else 0)
