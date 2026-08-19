"""Tests de la logica de seleccion del simulador (rango ordinal + duplicados)."""
import sys, os
sys.path.insert(0, "/home/criptoworld/Documents/OpenCode/AuditarSimuladorcerti/MyVCE_Funcional")

from src.seleccion import (
    firma_pregunta, deduplicar, coincide_tag, seleccionar_pool, detectar_conflictos,
)

def q(id, texto, opciones=("A) uno", "B) dos"), correctas=("A",), tag="T"):
    return {"id": id, "pregunta": texto, "opciones": list(opciones),
            "correctas": list(correctas), "tag": tag}

fallos = []
def check(nombre, cond, detalle=""):
    if cond:
        print(f"  PASS  {nombre}")
    else:
        print(f"  FAIL  {nombre} {detalle}")
        fallos.append(nombre)

print("\n== RC1: el rango debe seguir la posicion de 'Ver Preguntas' (ids con huecos) ==")
# Banco real: ids 1..189 con huecos por borrados. El usuario lee los numeros de Ver Preguntas.
banco = [q(1, "p1"), q(3, "p3"), q(7, "p7"), q(12, "p12"), q(20, "p20")]
pool, info = seleccionar_pool(banco, tags_seleccionados=[], rango=(2, 4))
check("rango 2-4 devuelve exactamente 3 preguntas", len(pool) == 3, f"-> {len(pool)}")
check("rango 2-4 devuelve las posiciones 2,3,4 del banco",
      [p["id"] for p in pool] == [3, 7, 12], f"-> {[p['id'] for p in pool]}")
check("info expone los numeros de posicion pedidos", info["rango"] == (2, 4), f"-> {info['rango']}")

print("\n== RC1b: el rango NO debe desplazarse al filtrar por tags ==")
banco2 = [q(1, "p1", tag="A"), q(2, "p2", tag="B"), q(3, "p3", tag="A"),
          q(4, "p4", tag="B"), q(5, "p5", tag="A")]
pool, info = seleccionar_pool(banco2, tags_seleccionados=["A"], rango=(1, 3))
check("rango 1-3 + tag A = interseccion (posiciones 1..3 que son tag A)",
      [p["id"] for p in pool] == [1, 3], f"-> {[p['id'] for p in pool]}")

print("\n== RC3: preguntas sin tag no deben desaparecer ==")
banco3 = [q(1, "p1", tag="A"), q(2, "p2", tag=""), q(3, "p3", tag="A")]
check("'Sin tag' selecciona las preguntas sin etiqueta",
      coincide_tag(banco3[1], ["Sin tag"]) is True)
check("un tag normal no arrastra las preguntas sin etiqueta",
      coincide_tag(banco3[1], ["A"]) is False)
pool, info = seleccionar_pool(banco3, tags_seleccionados=["A", "Sin tag"], rango=None)
check("seleccionar A + Sin tag devuelve las 3", len(pool) == 3, f"-> {len(pool)}")

print("\n== RC2: duplicados reales del banco (id 12 / id 14) ==")
# Mismo enunciado salvo saltos de linea del OCR, mismas opciones, misma respuesta.
d1 = q(12, "Refer to the exhibit, which shows an SD-WAN zone configuration on the FortiGate GUI. Based on the exhibit, which statement is true?",
       ("A) The Underlay zone is the zone by default.", "B) The Underlay zone contains no member."), ("B",))
d2 = q(14, "Refer to the exhibit,\nwhich shows an SD-WAN zone configuration on the FortiGate GUI.\n\nBased on the exhibit, which statement is true?",
       ("A) The Underlay zone is the zone by default.", "B) The Underlay zone contains no member."), ("B",))
check("misma firma pese a los saltos de linea", firma_pregunta(d1) == firma_pregunta(d2))
unicas, dups = deduplicar([d1, d2])
check("se conserva una sola copia", len(unicas) == 1, f"-> {len(unicas)}")
check("se reporta la copia descartada", [p["id"] for p in dups] == [14], f"-> {[p['id'] for p in dups]}")

print("\n== RC2b: preguntas distintas con el mismo enunciado NO se deben borrar (id 99 / id 187) ==")
# Mismo texto introductorio, pero opciones y respuesta distintas: son preguntas diferentes.
n1 = q(99, "Refer to the exhibits.\nYou have implemented the application sensor and the corresponding firewall policy as shown.",
       ("A) Set the action for Excessive-Bandwidth", "D) Set the action for Google"), ("D",))
n2 = q(187, "Refer to the exhibits.\nYou have implemented the application sensor and the corresponding firewall policy as shown.",
       ("A) Change the Inspection mode to Proxy-based.", "B) Set SSL inspection to deep-content-inspection"), ("B",))
check("firmas distintas cuando las opciones difieren", firma_pregunta(n1) != firma_pregunta(n2))
unicas, dups = deduplicar([n1, n2])
check("se conservan las dos", len(unicas) == 2 and dups == [], f"-> {len(unicas)}, {dups}")

print("\n== RC2c: duplicado con respuesta contradictoria (id 136 / id 137) ==")
c1 = q(136, "How does Strata Logging Service help resolve log retention needs?",
       ("A) Automatic selection", "C) It increases resilience", "D) It can scale"), ("C",))
c2 = q(137, "How does Strata Logging Service help resolve log retention needs?",
       ("A) Automatic selection", "C) It increases resilience", "D) It can scale"), ("D",))
unicas, dups = deduplicar([c1, c2])
check("solo entra una en el examen", len(unicas) == 1, f"-> {len(unicas)}")
conf = detectar_conflictos([c1, c2])
check("se avisa del conflicto de respuesta", len(conf) == 1 and set(conf[0]) == {136, 137}, f"-> {conf}")
check("no se avisa de conflicto cuando las respuestas coinciden", detectar_conflictos([d1, d2]) == [])

print("\n== RC4: deduplicar antes de muestrear, no despues ==")
banco4 = [d1, d2] + [q(100 + i, f"unica {i}") for i in range(8)]
pool, info = seleccionar_pool(banco4, tags_seleccionados=[], rango=None)
check("el pool ofrecido ya viene sin duplicados", len(pool) == 9, f"-> {len(pool)}")
check("se informa de cuantos duplicados se retiraron", info["duplicados"] == 1, f"-> {info['duplicados']}")
check("ninguna firma repetida en el pool",
      len({firma_pregunta(p) for p in pool}) == len(pool))

print("\n== Robustez del rango ==")
check("rango invertido se normaliza",
      [p["id"] for p in seleccionar_pool(banco, [], (4, 2))[0]] == [3, 7, 12])
check("rango fuera de limites se recorta",
      len(seleccionar_pool(banco, [], (3, 999))[0]) == 3)
check("sin rango devuelve el banco entero", len(seleccionar_pool(banco, [], None)[0]) == 5)

print("\n" + ("TODOS OK" if not fallos else f"{len(fallos)} FALLOS: {fallos}"))
sys.exit(1 if fallos else 0)
