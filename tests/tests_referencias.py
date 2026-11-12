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

from tests.comun import check, cerrar


BANEADOS = ("build_installer", "setup.iss", "build/build_", "build\\build_",
            "MyVCE_Certificacion", "dist/MyVCE")
EXTENSIONES = (".md", ".py", ".bat", ".toml", ".txt")
OMITIR_DIRS = {".git", ".venv", "venv", "__pycache__", ".atl", ".claude",
               ".streamlit", ".idea", ".vscode"}
ESTE_ARCHIVO = os.path.basename(__file__)


def _archivos_del_repo():
    """Solo archivos trackeados: el veredicto debe depender del repo, no del
    estado local del worktree (restos de builds, scratch, etc.)."""
    import subprocess
    salida = subprocess.run(["git", "-C", REPO, "ls-files"],
                            capture_output=True, text=True, check=True)
    for relativo in salida.stdout.splitlines():
        if os.path.basename(relativo) == ESTE_ARCHIVO:
            continue
        if relativo.endswith(EXTENSIONES):
            yield os.path.join(REPO, relativo)


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
    faltantes = [r for r in sorted(referencias)
                 if not os.path.exists(os.path.join(REPO, r))]
    check(f"{bat} solo referencia ficheros existentes",
          not faltantes, f"-> faltan: {faltantes}")

print("\n== comandos de test documentados en CLAUDE.md ==")
with open(os.path.join(REPO, "CLAUDE.md"), encoding="utf-8") as f:
    documentacion = f.read()
comandos_doc = re.findall(r"python (tests/[\w.]+\.py)", documentacion)
faltan_docs = [c for c in comandos_doc if not os.path.exists(os.path.join(REPO, c))]
check("todo comando de test documentado resuelve a un archivo real",
      bool(comandos_doc) and not faltan_docs,
      f"-> documentados: {len(comandos_doc)}, rotos: {faltan_docs}")

cerrar()
