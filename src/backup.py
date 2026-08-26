"""Exportación e importación de preguntas en ZIP.

Extraído de app.py para poder probarlo sin Streamlit. Endurecido frente a
ZIPs maliciosos: no usa extractall() (solo lee 'preguntas.json' y los
miembros de 'imagenes/'), aplica tope de tamaño descomprimido (zip bomb) y
usa os.path.basename() al escribir, así ningún miembro puede salirse de la
carpeta de imágenes.
"""

import io
import json
import os
import shutil
import zipfile

# Topes anti zip-bomb. Constantes de módulo para poder bajarlas en tests.
LIMITE_TOTAL_BYTES = 200 * 1024 * 1024       # 200 MB descomprimidos en total
LIMITE_ARCHIVO_BYTES = 20 * 1024 * 1024      # 20 MB por imagen


def _relativizar(abs_path, data_dir):
    """Convierte una ruta absoluta de imagen en relativa al data_dir."""
    if not abs_path or not os.path.isabs(abs_path):
        return abs_path
    try:
        return os.path.relpath(abs_path, data_dir)
    except ValueError:
        return abs_path


def export_questions_to_zip(preguntas, data_dir):
    """Exporta preguntas e imágenes a un archivo ZIP (bytes)."""
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        preguntas_export = []
        for p in preguntas:
            p_exp = p.copy()
            if p_exp.get("imagen"):
                p_exp["imagen"] = _relativizar(p_exp["imagen"], data_dir)
            preguntas_export.append(p_exp)

        json_data = json.dumps(preguntas_export, indent=4, ensure_ascii=False)
        zip_file.writestr('preguntas.json', json_data)

        # Una imagen compartida por varias preguntas se escribe una sola vez.
        nombres_vistos = set()
        for p in preguntas:
            if p.get("imagen"):
                nombre = _relativizar(p["imagen"], data_dir)
                abs_path = nombre if os.path.isabs(nombre) else os.path.join(data_dir, nombre)
                if abs_path and os.path.exists(abs_path):
                    entrada = f'imagenes/{os.path.basename(abs_path)}'
                    if entrada not in nombres_vistos:
                        nombres_vistos.add(entrada)
                        zip_file.write(abs_path, entrada)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def import_questions_from_zip(zip_bytes, data_dir):
    """Importa preguntas e imágenes desde un archivo ZIP.

    Devuelve la lista de preguntas (sin validar: eso hace
    validar_preguntas_importadas) o {"error": ...}.
    """
    carpeta_imagenes = os.path.join(data_dir, "imagenes_preguntas")

    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zip_file:
            # Validar todo ANTES de escribir nada en disco.
            total = sum(zi.file_size for zi in zip_file.infolist())
            if total > LIMITE_TOTAL_BYTES:
                return {"error": "El ZIP descomprime más de 200 MB en total; no se importa."}

            if 'preguntas.json' not in zip_file.namelist():
                return {"error": "El ZIP no contiene preguntas.json"}

            try:
                preguntas_importadas = json.loads(
                    zip_file.read('preguntas.json').decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return {"error": "El preguntas.json del ZIP no es un JSON válido."}

            miembros_imagenes = []
            for zi in zip_file.infolist():
                if zi.is_dir():
                    continue
                nombre = zi.filename.replace("\\", "/")
                if not nombre.startswith("imagenes/"):
                    continue
                img_filename = os.path.basename(nombre)
                if not img_filename:
                    continue
                if zi.file_size > LIMITE_ARCHIVO_BYTES:
                    return {"error": f"La imagen '{img_filename}' del ZIP pesa más de 20 MB descomprimida."}
                miembros_imagenes.append((zi, img_filename))

            # Escritura: solo los miembros validados, con basename() para que
            # ninguno pueda escapar de la carpeta de imágenes.
            os.makedirs(carpeta_imagenes, exist_ok=True)
            for zi, img_filename in miembros_imagenes:
                dst_path = os.path.join(carpeta_imagenes, img_filename)
                with zip_file.open(zi) as src, open(dst_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)

    except zipfile.BadZipFile:
        return {"error": "El archivo no es un ZIP válido."}

    if isinstance(preguntas_importadas, list):
        for p in preguntas_importadas:
            if isinstance(p, dict) and p.get("imagen"):
                p["imagen"] = _relativizar(p["imagen"], data_dir)

    return preguntas_importadas
