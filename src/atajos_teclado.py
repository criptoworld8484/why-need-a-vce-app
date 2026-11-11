"""Atajos de teclado para el simulador: captura de teclas y acciones.

Streamlit 1.54 no expone API de teclado. `src/atajos_componente/` es un
componente vanilla que captura las teclas (tenga el foco el documento padre
o el propio iframe del componente) y las devuelve a Python como valor del
componente mediante el protocolo de componentes de Streamlit. La navegación
la decide Python (app.py), sin depender del DOM de los botones.

Atajos: Enter o flecha derecha = 'adelante' (Siguiente, o Finalizar en la
última pregunta); flecha izquierda = 'atras' (Anterior).
"""
import os

import streamlit.components.v1 as components

_componente = components.declare_component(
    "atajos_simulador",
    path=os.path.join(os.path.dirname(__file__), "atajos_componente"),
)

# Acciones que el componente puede reportar.
ACCIONES_VALIDAS = ("adelante", "atras")


def capturar_tecla():
    """Devuelve {'tecla': 'adelante'|'atras', 'ts': int} o None.

    El 'ts' (marca de tiempo de la pulsación) sirve al llamador para no
    procesar dos veces la misma pulsación: el valor del componente persiste
    entre reruns hasta que llega una tecla nueva.
    """
    valor = _componente(default=None)
    if isinstance(valor, dict) and valor.get("tecla") in ACCIONES_VALIDAS:
        return valor
    return None
