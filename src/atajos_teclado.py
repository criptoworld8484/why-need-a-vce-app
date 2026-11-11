"""Atajos de teclado para el simulador.

Streamlit 1.54 no expone API de teclado, así que los atajos se inyectan con
un componente HTML same-origin que escucha el teclado sobre el documento
padre y dispara los botones de navegación por su etiqueta visible.

Atajos: Enter o flecha derecha = Siguiente (o Finalizar en la última
pregunta); flecha izquierda = Anterior.

Si una actualización de Streamlit cambia el DOM de los botones, este módulo
es el único a revisar: las etiquetas de ACCIONES deben coincidir con las de
app.py (lo pinnea tests/tests_simulador.py).
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
  // Guardia anti-doble-registro: cada rerun recarga el componente y sin este
  // flag cada listener duplicaría el avance.
  const destino = (window.parent && window.parent.document) ? window.parent.document : document;
  if (destino.__myvce_atajos_activos) return;
  destino.__myvce_atajos_activos = true;
  const etiquetas = {etiquetas};
  function pulsar(nombre) {{
    const botones = destino.querySelectorAll("button");
    for (const b of botones) {{
      const t = (b.textContent || "").trim();
      if (t.includes(etiquetas[nombre]) && !b.disabled) {{
        b.click();
        return true;
      }}
    }}
    return false;
  }}
  destino.addEventListener("keydown", function(e) {{
    if (e.ctrlKey || e.altKey || e.metaKey) return;
    const t = e.target || {{}};
    const tag = (t.tagName || "").toLowerCase();
    const tipo = (t.type || "").toLowerCase();
    // No secuestrar la escritura en campos de texto ni el Enter nativo de
    // un botón enfocado (que ya se activa solo).
    if (tag === "textarea" || tag === "select") return;
    if (tag === "input" && tipo !== "checkbox" && tipo !== "radio") return;
    if (t.isContentEditable) return;
    if (e.key === "Enter" && tag === "button") return;
    if (e.key === "Enter" || e.key === "ArrowRight") {{
      if (pulsar("siguiente") || pulsar("finalizar")) e.preventDefault();
    }} else if (e.key === "ArrowLeft") {{
      if (pulsar("anterior")) e.preventDefault();
    }}
  }}, true);
}})();
"""


def inyectar_atajos():
    """Renderiza el componente invisible que conecta el teclado con los
    botones de navegación del simulador."""
    js = _PLANTILLA_JS.format(etiquetas=json.dumps(ACCIONES, ensure_ascii=False))
    components.html(f"<script>{js}</script>", height=0)
