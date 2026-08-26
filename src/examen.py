"""Cálculo de resultados del simulador.

Función pura compartida por el botón Finalizar y por el timeout del timer:
antes el timeout activaba los resultados sin calcularlos y la pantalla de
corrección crasheaba con resultado_final = None.
"""


def calcular_resultado(preguntas_simulador, respuestas_usuario,
                       contar_no_respondidas_como_incorrectas=False):
    """Devuelve el resumen de un examen: correctas/parciales/incorrectas/etc.

    Una pregunta es correcta solo si el conjunto de respuestas coincide
    exactamente con las correctas; parcial si acierta alguna; el resto,
    incorrecta. Las no respondidas van a su propio cubo salvo que se pida
    contarlas como incorrectas (modo examen).
    """
    correctas = 0
    parciales = 0
    incorrectas = 0
    no_respondidas = 0

    for i, p in enumerate(preguntas_simulador):
        resp = respuestas_usuario.get(i, [])
        if not isinstance(resp, list):
            resp = [resp] if resp else []

        if not resp:
            no_respondidas += 1
            continue

        correctas_p = set(p.get("correctas", []))
        respuestas_s = set(resp)

        if respuestas_s == correctas_p:
            correctas += 1
        elif respuestas_s.intersection(correctas_p):
            parciales += 1
        else:
            incorrectas += 1

    if no_respondidas > 0 and contar_no_respondidas_como_incorrectas:
        incorrectas += no_respondidas
        no_respondidas = 0

    total = len(preguntas_simulador)
    return {
        "correctas": correctas,
        "parciales": parciales,
        "incorrectas": incorrectas,
        "no_respondidas": no_respondidas,
        "total": total,
        "porcentaje": (correctas / total) * 100 if total else 0.0,
    }
