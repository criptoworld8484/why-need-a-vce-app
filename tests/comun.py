"""Utilidades comunes de la suite: contador de fallos y salida estándar.

Cada script de tests es ejecutable por sí solo (python tests/<archivo>.py);
este módulo evita repetir el mismo check()/fallos/cierre en cada uno.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

fallos = []


def check(desc, cond, detail=""):
    marca = "OK " if cond else "FAIL"
    print(f"  [{marca}] {desc} {detail}")
    if not cond:
        fallos.append(desc)


def cerrar():
    print("\n" + ("TODOS OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
    sys.exit(1 if fallos else 0)
