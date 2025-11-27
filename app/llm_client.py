"""Light wrapper for an LLM provider.

This module is is now configured to use the Google Gemini API (google-genai)
as a free alternative to OpenAI, reading the GEMINI_API_KEY from environment 
variables.
"""
import os
from typing import Dict

# 1. CAMBIO DE CLAVE: Ahora buscamos la variable de entorno GEMINI_API_KEY
# Render leerá la variable que configuraste.
GEMINI_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GEMINI_KEY')


def call_llm(prompt: str, model: str = 'gemini-2.5-flash') -> Dict[str, str]:
    """Call an LLM provider and return a safe response dict.

    Returns: { 'ok': True/False, 'response': str }
    """
    # 2. Verificar la clave de GEMINI
    if not GEMINI_KEY:
        return {'ok': False, 'response': 'LLM no configurado. Establece GEMINI_API_KEY en las variables de entorno.'}

    # 3. Importar la librería de GEMINI
    try:
        from google import genai
    except Exception:
        return {'ok': False, 'response': 'Paquete google-genai no instalado. Añádelo a requirements.'}

    try:
        # 4. Inicializar el cliente (toma la clave GEMINI_KEY automáticamente)
        # Asegúrate de que GEMINI_API_KEY esté en las variables de entorno de Render.
        client = genai.Client(api_key=GEMINI_KEY)

        # 5. Configurar el contexto de sistema para el modelo
        # En Gemini, se recomienda usar 'system_instruction' para el rol del asistente.
        config = dict(
            system_instruction='Eres un asistente útil para el administrador del sistema.',
            temperature=0.2,
            max_output_tokens=600  # Máximo de tokens de respuesta
        )
        
        # 6. Llamada a la API de Gemini (generate_content)
        # Usamos el modelo gemini-2.5-flash
        completion = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config
        )
        
        # 7. Extraer respuesta de Gemini (.text)
        text = completion.text

        return {'ok': True, 'response': text}
    except Exception as e:
        # Ahora manejará errores de conexión o cuota de Google
        return {'ok': False, 'response': f'Error al llamar al LLM: {e}'}