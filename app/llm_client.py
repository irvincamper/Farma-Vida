"""Light wrapper for an LLM provider.

This module is configured to use the Google Gemini API (google-genai) and is 
enhanced to handle security blocks and integrate context (RAG) from the database.
"""
import os
from typing import Dict, Optional
from google import genai
from google.genai.errors import APIError

# 1. CLAVE: Buscamos la variable de entorno GEMINI_API_KEY.
GEMINI_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')


def call_llm(
    prompt: str, 
    db_context: Optional[str] = None, 
    model: str = 'gemini-2.5-flash'
) -> Dict[str, str]:
    """Call an LLM provider and return a safe response dict, potentially enhanced with DB context.

    db_context: Cadena de texto que contiene información extraída de la base de datos.
    Returns: { 'ok': True/False, 'response': str }
    """
    
    if not GEMINI_KEY:
        return {'ok': False, 'response': 'LLM no configurado. Establece GEMINI_API_KEY en las variables de entorno de la nube.'}

    try:
        client = genai.Client(api_key=GEMINI_KEY)

        # A. INSTRUCCIÓN CRÍTICA Y MEJORADA (Se añade el formato de respuesta y se hace el uso del contexto MANDATORIO)
        system_instruction = (
            '**CRÍTICO:** Eres un asistente experto en la administración del sistema **Cuida Mas**. '
            'Tu única prioridad es responder a preguntas sobre conteos y métricas. '
            
            '1. **RESPUESTAS CON DATOS (CONTEXTO DISPONIBLE):** Debes usar **SOLAMENTE** los datos provistos en el "CONTEXTO DE LA BASE DE DATOS". Responde de forma **directa, precisa y concisa, utilizando exclusivamente los números y el texto fáctico proporcionado**. **PROHIBIDO** inventar, buscar, o agregar cualquier otra información. El formato debe ser lo más escueto posible (ej: "38 usuarios registrados en total"). '
            
            '2. **RESPUESTAS SIN DATOS (CONTEXTO AUSENTE):** Para preguntas generales (no estadísticas), usa tu conocimiento. '
            
            '3. **RECHAZO DE SEGURIDAD:** Si el contexto te indica que el usuario pidió datos personales (ej: Irvin), **DEBES** rechazar la petición con la razón de "políticas de privacidad y seguridad del sistema Cuida Mas", no con razones de "dato no encontrado".'
            
            '**ATENCIÓN:** Tu TAREA PRINCIPAL es la precisión y la concisión, priorizando SIEMPRE la información de la DB.'
        )
        
        # B. CONSTRUCCIÓN DEL PROMPT (Integra el contexto de la DB)
        # Añadimos una instrucción de contexto muy clara.
        full_prompt = f"Consulta del Usuario: {prompt}\n\n"
        if db_context:
            full_prompt += f"**CONTEXTO DE LA BASE DE DATOS (MANDATORIO):** {db_context}\n\n"
        
        config = dict(
            system_instruction=system_instruction,
            temperature=0.0, # Temperatura reducida a 0.0 para la máxima predictibilidad y adherencia a la instrucción.
            max_output_tokens=600
        )
        
        completion = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=full_prompt, 
            config=config
        )
        
        text = ''
        
        if completion.candidates and completion.candidates[0].finish_reason.name == 'SAFETY':
            text = "Lo siento, mi respuesta fue bloqueada por las políticas de seguridad de contenido. Intenta reformular tu pregunta."
        elif completion.text:
            text = completion.text
        else:
            text = "Lo siento, hubo un problema al generar la respuesta o la respuesta fue vacía."

        return {'ok': True, 'response': text}
        
    except APIError as e:
        print(f"Error de API de Gemini: {e}")
        return {'ok': False, 'response': "Error de conexión con la API de Gemini. Revisa tu 'GEMINI_API_KEY' en la configuración de la nube."}
        
    except Exception as e:
        return {'ok': False, 'response': f'Error al llamar al LLM: {e}'}