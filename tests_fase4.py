"""Tests Fase 4: imagenes_referenciadas / purgar_imagenes_huerfanas."""
import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)

from src.preguntas import imagenes_referenciadas, purgar_imagenes_huerfanas

fallos = []
def check(nombre, cond, detalle=""):
    if cond:
        print(f"  PASS  {nombre}")
    else:
        print(f"  FAIL  {nombre} {detalle}")
        fallos.append(nombre)

print("\n== imagenes_referenciadas ==")
banco = [
    {"id": 1, "imagen": "imagenes_preguntas/a.png"},
    {"id": 2, "imagen": "/ruta/absoluta/b.png"},   # absoluta: cuenta el basename
    {"id": 3, "imagen": None},                      # sin imagen
    {"id": 4},                                      # sin clave imagen
    {"id": 5, "imagen": ""},                        # vacia
    "no soy dict",                                  # entrada basura
]
refs = imagenes_referenciadas(banco)
check("recoge a.png y b.png, ignora el resto",
      refs == {"a.png", "b.png"}, f"-> {refs}")
check("banco vacio -> set vacio", imagenes_referenciadas([]) == set())

print("\n== purgar_imagenes_huerfanas ==")
d = tempfile.mkdtemp(prefix="vce_imgs_")
imgs = os.path.join(d, "imagenes_preguntas")

def crear_imgs(*nombres):
    os.makedirs(imgs, exist_ok=True)
    for nombre in nombres:
        with open(os.path.join(imgs, nombre), "wb") as f:
            f.write(b"x")

# Caso base: referenciadas (rel y abs) + 2 huerfanas + un subdirectorio.
crear_imgs("a.png", "b.png", "c.png", "huerfana1.png", "huerfana2.png")
os.makedirs(os.path.join(imgs, "subdir"))

banco_ab = [
    {"id": 1, "imagen": "imagenes_preguntas/a.png"},
    {"id": 2, "imagen": os.path.join(imgs, "b.png")},
    {"id": 3, "pregunta": "sin imagen"},
]
borradas = purgar_imagenes_huerfanas(imgs, banco_ab)
# c.png no la referencia nadie: tambien es huerfana.
check("borra las 3 huerfanas",
      sorted(borradas) == ["c.png", "huerfana1.png", "huerfana2.png"], f"-> {borradas}")
check("las referenciadas sobreviven (rel y abs)",
      os.path.exists(os.path.join(imgs, "a.png"))
      and os.path.exists(os.path.join(imgs, "b.png")))
check("el subdirectorio no se toca", os.path.isdir(os.path.join(imgs, "subdir")))
check("segunda purga no borra nada mas", purgar_imagenes_huerfanas(imgs, banco_ab) == [])

# Imagen compartida: carpeta aislada con SOLO a.png para que el estado
# entre casos sea determinista.
imgs2 = os.path.join(d, "imagenes_compartida")
os.makedirs(imgs2)
with open(os.path.join(imgs2, "a.png"), "wb") as f:
    f.write(b"x")

compartida = [
    {"id": 1, "imagen": "imagenes_preguntas/a.png"},
    {"id": 2, "imagen": "imagenes_preguntas/a.png"},
]
check("imagen compartida no se purga",
      purgar_imagenes_huerfanas(imgs2, compartida) == [])
# Al borrar una de las dos (queda una referencia), sigue sobreviviendo.
compartida.pop(0)
check("con una sola referencia sigue viva",
      purgar_imagenes_huerfanas(imgs2, compartida) == [])
# Al desaparecer la ultima referencia, se purga.
compartida.pop(0)
check("sin referencias se purga",
      purgar_imagenes_huerfanas(imgs2, compartida) == ["a.png"])
check("banco vacio lo purga todo",
      purgar_imagenes_huerfanas(imgs2, []) == [])

print("\n== limitar_a: borrado individual sin arrastrar huerfanas ajenas ==")
crear_imgs("a.png", "b.png")
banco_a = [{"id": 1, "imagen": "imagenes_preguntas/a.png"}]

# Limitador sobre a.png, que esta referenciada: no se borra.
borradas = purgar_imagenes_huerfanas(imgs, banco_a, limitar_a={"a.png"})
check("limitado a a.png y referenciada -> no borra nada",
      borradas == [] and os.path.exists(os.path.join(imgs, "a.png")))

# b.png es huerfana pero esta FUERA del limitador -> sobrevive.
borradas = purgar_imagenes_huerfanas(imgs, banco_a, limitar_a={"a.png"})
check("huerfana fuera del limitador -> sobrevive",
      "b.png" not in borradas and os.path.exists(os.path.join(imgs, "b.png")))

# Mismo banco, limitador sobre b.png: ahora si se borra; a.png queda fuera
# del limitador y sobrevive aunque el banco la referencie de todos modos.
borradas = purgar_imagenes_huerfanas(imgs, banco_a, limitar_a={"b.png"})
check("huerfana dentro del limitador -> se borra",
      borradas == ["b.png"] and not os.path.exists(os.path.join(imgs, "b.png")))

# Sin limitador (purga global): con banco vacio cae todo.
borradas = purgar_imagenes_huerfanas(imgs, [])
check("purga global con banco vacio lo borra todo",
      sorted(borradas) == ["a.png"])

check("carpeta inexistente -> lista vacia sin error",
      purgar_imagenes_huerfanas(os.path.join(d, "no_existe"), []) == [])

shutil.rmtree(d, ignore_errors=True)

print("\n" + ("TODOS OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
sys.exit(1 if fallos else 0)
