"""Atajos de teclado para el simulador.

Streamlit 1.54 no expone API de teclado, así que los atajos se inyectan con
un componente HTML same-origin que escucha el teclado sobre el documento
padre y dispara los botones de navegación por su etiqueta visible.

Atajos: Enter o flecha derecha = Siguiente (o Finalizar en la última
pregunta); flecha izquierda = Anterior. Cada atajo lanzado muestra un
destello de confirmación en la esquina: si no aparece, el navegador no está
recibiendo el atajo (foco en otro marco, extensión que bloquea, etc.).

El match de tecla es por e.code (físico, independiente del layout) con e.key
de respaldo. Si una actualización de Streamlit cambia el DOM de los botones,
este módulo es el único a revisar: las etiquetas de ACCIONES deben coincidir
con las de app.py (lo pinnea tests/tests_simulador.py).
"""
import json

import streamlit.components.v1 as components

# Etiqueta visible del botón de app.py que dispara cada acción.
ACCIONES = {
    "siguiente": "Siguiente ➡",
    "anterior": "⬅ Anterior",
    "finalizar": "🏁 Finalizar",
}

_PLANTILLA_JS = """(function() {{
  const ventana = window.parent || window;
  const destino = ventana.document;
  // Guardia anti-doble-registro: cada rerun recarga el componente y sin este
  // flag cada listener duplicaría el avance.
  if (destino.__myvce_atajos_activos) return;
  destino.__myvce_atajos_activos = true;
  const etiquetas = {etiquetas};
  function pulsar(nombre) {{
    const botones = destino.querySelectorAll("button");
    for (const b of botones) {{
      const t = (b.textContent || "").trim();
      if (t.includes(etiquetas[nombre]) && !b.disabled) {{
        b.click();
        destello(etiquetas[nombre]);
        return true;
      }}
    }}
    return false;
  }}
  function destello(texto) {{
    const d = destino.createElement("div");
    d.textContent = texto;
    d.style.cssText = "position:fixed;bottom:18px;right:18px;background:#111827;" +
      "color:#fff;padding:8px 14px;border-radius:10px;font:600 14px sans-serif;" +
      "opacity:.92;z-index:2147483000;transition:opacity .45s;pointer-events:none;";
    destino.body.appendChild(d);
    setTimeout(function() {{
      d.style.opacity = "0";
      setTimeout(function() {{ d.remove(); }}, 480);
    }}, 600);
  }}
  function manejar(e) {{
    if (e.ctrlKey || e.altKey || e.metaKey) return;
    const t = e.target || {{}};
    const tag = (t.tagName || "").toLowerCase();
    const tipo = (t.type || "").toLowerCase();
    // No secuestrar la escritura en campos de texto ni el Enter nativo de
    // un botón enfocado (que ya se activa solo).
    if (tag === "textarea" || tag === "select") return;
    if (tag === "input" && tipo !== "checkbox" && tipo !== "radio") return;
    if (t.isContentEditable) return;
    const k = e.key || "";
    const c = e.code || "";
    const adelante = k === "Enter" || c === "Enter" || c === "NumpadEnter" ||
                     k === "ArrowRight" || c === "ArrowRight";
    const atras = k === "ArrowLeft" || c === "ArrowLeft";
    if (e.key === "Enter" && tag === "button") return;
    if (adelante) {{
      if (pulsar("siguiente") || pulsar("finalizar")) e.preventDefault();
    }} else if (atras) {{
      if (pulsar("anterior")) e.preventDefault();
    }}
  }}
  // Ventana y documento, en fase de captura: el evento llega pase donde
  // pase el foco dentro de la aplicación.
  ventana.addEventListener("keydown", manejar, true);
  destino.addEventListener("keydown", manejar, true);
}})();
"""


def inyectar_atajos():
    """Renderiza el componente invisible que conecta el teclado con los
    botones de navegación del simulador."""
    js = _PLANTILLA_JS.format(etiquetas=json.dumps(ACCIONES, ensure_ascii=False))
    components.html(f"<script>{js}</script>", height=0)
