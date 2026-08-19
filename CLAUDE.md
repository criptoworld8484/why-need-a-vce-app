# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"Why need a VCE app?" — a Streamlit certification-exam simulator (single-page, 4 tabs). UI text, comments and identifiers are in Spanish; keep new code in Spanish to match.

## Commands

```bash
pip install -r requirements.txt
python -m streamlit run app.py --server.port 8502     # dev server → http://localhost:8502

build/build_linux.sh                                   # package to dist/MyVCE_Certificacion/
build\build_windows.bat                                # same, Windows
build_installer.bat                                    # Inno Setup installer (setup.iss)
```

There is no test suite, linter, or CI checked in. For anything in `src/`, write a plain-Python script and run it directly. To exercise the Streamlit UI headlessly (widgets, reruns, session state) use `streamlit.testing.v1.AppTest` — `AppTest.from_file("app.py")`, seed `session_state["config_completed"] = True` to skip the API-key setup screen, then drive `at.radio[0]`, `at.checkbox(key=...)`, `at.button[...]` and assert on `at.exception`. This runs the real script, unlike hitting the HTTP port, which only serves the static shell.

Note: both build scripts copy `preguntas.json` and `imagenes_preguntas/` from the **repo root** and fail verification if absent — those are user data that live in the data dir at runtime, so create/seed them at the root before packaging.

## Architecture

`app.py` (~2400 lines) is the entire application: CSS block, constants, helper functions, then four top-level `if/elif` branches — one per tab — dispatched on a `st.radio` value kept in `st.session_state.pestana_actual`. Section boundaries are marked by `# ====== PESTAÑA N: ... ======` banners. There are no page modules; adding a tab means adding an entry to `opciones_pestanas` and another `elif` branch.

`src/` holds the extracted modules:
- `src/paths.py` — the app-dir vs data-dir split (see below), PyInstaller-`frozen`-aware.
- `src/api_key_manager.py` — Gemini API key encrypted at rest with Fernet in the config dir; degrades to no-op if `cryptography` is missing.
- `src/seleccion.py` — pure (Streamlit-free) exam pool selection: ordinal range, tag filter, duplicate detection. Kept importable so it can be unit-tested without a Streamlit session.

### App dir vs data dir (important)

`get_app_dir()` is read-only bundled resources (`_internal/` when frozen). `get_data_dir()` is user-writable: `~/.local/share/WhyNeedAVCEApp` (`%APPDATA%\WhyNeedAVCEApp` on Windows). All mutable state — `preguntas.json`, `imagenes_preguntas/` — lives in the data dir. `_initialize_resources()` seeds the data dir from the app dir on first run only. Never write into `APP_DIR`.

Image paths are stored **relative** to the data dir in JSON (`get_relative_image_path` on write, `resolve_image_path` on read) so ZIP export/import stays portable across machines.

### Question schema

```json
{"id": 1, "pregunta": "...", "imagen": "imagenes_preguntas/x.png",
 "tag": "vendor", "opciones": ["A) ...", "B) ..."], "correctas": ["A", "C"]}
```

`opciones` entries carry their letter prefix inline as text; `correctas` is a list of letters (multi-answer supported, up to A–F). `aleatorizar_pregunta()` re-parses that prefix with a regex accepting `A)`, `A.`, `A -`, `A:`, reshuffles, relabels, and remaps `correctas` — options that don't match any of those formats are silently dropped, so keep the prefix convention when generating options. IDs are assigned as `max(id) + 1`.

### Persistence

`load_questions()` is `@st.cache_data(ttl=10)`; `save_questions()` writes the full JSON and then calls `load_questions.clear()`. Any code path that mutates questions must go through `save_questions` or the cache will serve stale data for up to 10s.

### Optional dependencies

`cv2`, `google.genai`, `streamlit_autorefresh` and `st.fragment` are each imported inside try/except into an `*_AVAILABLE` flag, and the UI degrades rather than crashing. Preserve that pattern. OpenCV env vars (`QT_QPA_PLATFORM=offscreen`, etc.) are set before the `cv2` import and must stay at the top of the file.

### OCR

`extract_text_from_image()` calls Gemini (`gemini-2.5-flash`), strips markdown fences, and validates the JSON contract `{"pregunta": str, "respuestas": list}`. It **always returns a dict** — either the parsed data or `{"error": ...}`, with the sentinel `error == "cuota_excedida"` (plus a `mensaje`) for 429/quota, and exponential-backoff retries otherwise. Callers must branch on `"error" in result`.

### Simulator / timer

Exam mode sets `timer_activo` and uses `st_autorefresh(interval=1000)` for the countdown; the no-package fallback is `time.sleep(1)` + `st.rerun()`. Relevant session keys: `preguntas_simulador`, `indice_actual`, `respuestas_usuario`, `mostrar_resultados`, `resultado_final`, `tiempo_inicio`, `tiempo_limite`.

Pool selection goes through `seleccionar_pool()` and the order of operations is load-bearing:

1. **Ordinal range is a position in the full bank** — the `N.º` shown in "Ver Preguntas", *not* the `#id`. Ids have gaps from deletions (in a real 186-question bank, 141 questions have `id != position`), so treating the two as interchangeable returns the wrong tramo. Applying the range after the tag filter shifts the numbering the same way — don't reorder these steps.
2. Tag filter intersects with the range. `SIN_TAG` ("Sin tag") must stay in the options or untagged questions silently vanish from the simulator.
3. Dedup runs **before** sampling, so the exam gets the requested count instead of a short one.

Duplicate identity is `firma_pregunta()` = normalized text **+ normalized options** (order-independent), excluding `correctas`. Both halves matter: OCR produces same-question copies differing only in line breaks (missed by exact text comparison), while the bank also holds legitimately distinct questions that share an "Refer to the exhibits…" preamble and differ only in options (destroyed by text-only dedup). Excluding `correctas` is deliberate — same question + same options + different answer is a data error, surfaced via `detectar_conflictos()` rather than silently kept as two questions.

## Styling

A single large `st.markdown(..., unsafe_allow_html=True)` CSS block near the top of `app.py` themes the app via CSS variables and `[data-testid=...]` Streamlit internals. `.streamlit/config.toml` forces `base = "light"` (this is tracked in git deliberately; the rest of `.streamlit/` is ignored) because browser dark mode broke contrast — CSS dark-mode overrides in the block back this up. Streamlit selectors are version-sensitive; verify visually after changing them.
