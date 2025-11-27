"""Light wrapper for an LLM provider.

This module is is now configured to use the Google Gemini API (google-genai)
as a free alternative to OpenAI, reading the GEMINI_API_KEY from environment 
variables.
"""
import os
from typing import Dict

# 1. CLAVE: Buscamos la variable de entorno GEMINI_API_KEY
GEMINI_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GEMINI_KEY')


def call_llm(prompt: str, model: str = 'gemini-2.5-flash') -> Dict[str, str]:
    """Call an LLM provider and return a safe response dict.

    Returns: { 'ok': True/False, 'response': str }
    """
    # 2. Verificar la clave de GEMINI
    if not GEMINI_KEY:
        return {'ok': False, 'response': 'LLM no configurado. Establece GEMINI_API_KEY en las variables de entorno.'}

    # 3. Importar la librería de GEMINI (Se asume que ya está en requirements.txt)
    try:
        from google import genai
    except Exception:
        return {'ok': False, 'response': 'Paquete google-genai no instalado. Añádelo a requirements.'}

    try:
        # 4. Inicializar el cliente
        client = genai.Client(api_key=GEMINI_KEY)

        # 5. Configurar el contexto de sistema para el modelo
        config = dict(
            system_instruction='Eres un asistente útil para el administrador del sistema.',
            temperature=0.2,
            max_output_tokens=600
        )
        
        # 6. Llamada a la API de Gemini (generate_content)
        completion = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config
        )
        
        # 7. EXTRACCIÓN Y VERIFICACIÓN DE RESPUESTA DE GEMINI (El cambio crucial)
        text = ''
        
        # Si la respuesta fue bloqueada por filtros de seguridad, maneja el error.
        # Esto previene el error 'TypeError: Cannot read properties of null (reading 'replace')' en el frontend.
        if completion.candidates and completion.candidates[0].finish_reason.name == 'SAFETY':
             text = "Lo siento, mi respuesta fue bloqueada por las políticas de seguridad de contenido. Intenta reformular tu pregunta."
        elif completion.text:
            # Si el texto existe, usarlo
            text = completion.text
        else:
            # Manejar cualquier otro caso donde la respuesta está vacía o es inesperada.
            text = "Lo siento, hubo un problema al generar la respuesta o la respuesta fue vacía."

        return {'ok': True, 'response': text}
        
    except Exception as e:
        # Ahora manejará errores de conexión, cuota de Google, o errores de la API.
        return {'ok': False, 'response': f'Error al llamar al LLM: {e}'}