"""OCR con Gemini: extracción de preguntas desde imágenes.

extract_text_from_image() siempre devuelve un dict: los datos parseados o
{"error": ...} con el centinela error == "cuota_excedida" (mas "mensaje")
para 429/cuota, error == "modelo_no_disponible" (mas "mensaje"/"detalle")
para el 404 de modelo retirado, y reintentos con backoff exponencial en el
resto. Los llamadores deben bifurcar sobre "error" in resultado.
"""

import json
import re
import time

from PIL import Image

from src.modelos_ocr import MODELO_OCR_PREDEFINIDO, es_error_modelo_no_disponible

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except Exception:
    GENAI_AVAILABLE = False


def extract_text_from_image(image_path, api_key, modelo=MODELO_OCR_PREDEFINIDO, max_retries=2):
    if not GENAI_AVAILABLE:
        return {"error": "google.genai no está instalado. Ejecuta: pip install google-genai"}
    
    for intento in range(max_retries):
        try:
            client = genai.Client(api_key=api_key)
            
            img = Image.open(image_path)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            import io
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=95)
            img_bytes = img_byte_arr.getvalue()
            
            prompt = """
            Eres un asistente experto en analizar capturas de pantalla de exámenes de certificación.
            Extrae el texto de la imagen y devuélvelo ESTRICTAMENTE en este formato JSON:
            {
                "pregunta": "Aquí el texto de la pregunta completa",
                "respuestas": [
                    "A) texto de la primera opción (usa \\n para saltos de línea si la opción tiene múltiples líneas)",
                    "B) texto de la segunda opción",
                    ...
                ]
            }
            
            IMPORTANTE:
            - Si una opción tiene múltiples líneas (código, listas, texto largo), preserva el formato usando \\n
            - Ignora cualquier texto de interfaz (botones, logos, horas, etc.)
            - Si no hay opciones de respuesta, deja la lista "respuestas" vacía
            - Devuelve SOLO el JSON válido, sin markdown
            """
            
            response = client.models.generate_content(
                model=modelo,
                contents=[
                    prompt,
                    types.Part.from_bytes(
                        data=img_bytes,
                        mime_type='image/jpeg'
                    )
                ]
            )
            
            if not response or not response.text:
                return {"error": "Gemini no devolvió contenido."}
            
            texto_limpio = response.text.strip()
            
            # Limpiar marcas de markdown
            if texto_limpio.startswith("```json"):
                texto_limpio = texto_limpio[7:].rstrip("```").strip()
            elif texto_limpio.startswith("```"):
                texto_limpio = texto_limpio[3:].rstrip("```").strip()
            
            # Validar que no esté vacío después de limpiar
            if not texto_limpio:
                return {"error": "La respuesta está vacía después de procesar."}
            
            try:
                data = json.loads(texto_limpio)
            except json.JSONDecodeError:
                return {"error": f"JSON inválido. La respuesta no es un JSON válido."}
            
            # Validar estructura del JSON
            if not isinstance(data, dict):
                return {"error": "JSON inválido: la raíz debe ser un objeto."}
            
            if "pregunta" not in data:
                return {"error": "JSON inválido: falta el campo 'pregunta'."}
            
            if "respuestas" not in data:
                return {"error": "JSON inválido: falta el campo 'respuestas'."}
            
            # Validar tipos
            if not isinstance(data.get("pregunta"), str):
                return {"error": "JSON inválido: 'pregunta' debe ser texto."}
            
            if not isinstance(data.get("respuestas"), list):
                return {"error": "JSON inválido: 'respuestas' debe ser una lista."}
                
            return data
            
        except json.JSONDecodeError as e:
            texto_error = response.text[:200] if response and hasattr(response, 'text') else 'Sin respuesta'
            return {"error": f"Error al parsear JSON: {str(e)}\n\nRespuesta: {texto_error}..."}
        
        except Exception as e:
            error_str = str(e)
            
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
                retry_match = re.search(r'retry in (\d+(?:\.\d+)?)', error_str)
                wait_seconds = int(float(retry_match.group(1))) if retry_match else 30
                
                return {
                    "error": "cuota_excedida",
                    "mensaje": f"""🚫 **Cuota de API agotada**

Has excedido los límites gratuitos de Google Gemini.

**Soluciones:**
1. ⏳ Espera {wait_seconds} segundos y reintenta
2. 🔑 Crea una nueva API Key: https://makersuite.google.com/app/apikey
3. ✍️ Usa la pestaña "Ingesta Manual"
                    """.strip()
                }
            
            if es_error_modelo_no_disponible(error_str):
                # Sin reintentos: el modelo no existe para esta cuenta y
                # volver a llamar devuelve el mismo 404.
                return {
                    "error": "modelo_no_disponible",
                    "mensaje": f"""⚠️ **Modelo no disponible**

El modelo `{modelo}` no está disponible para tu API Key (Google retira
modelos para usuarios nuevos aunque sigan activos en cuentas antiguas).

**Solución:** en **⚙️ Modelo** elige otro de la lista (por ejemplo
`{MODELO_OCR_PREDEFINIDO}`) y vuelve a procesar la imagen.
                    """.strip(),
                    "detalle": error_str,
                }
            
            if intento < max_retries - 1:
                time.sleep(2 ** intento)
                continue
            
            return {"error": f"Error: {str(e)}"}
    
    return {"error": "Máximo de reintentos alcanzado"}

