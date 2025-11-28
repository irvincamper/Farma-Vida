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

        # A. INSTRUCCIÓN CRÍTICA Y MEJORADA para evitar la alucinación
        system_instruction = (
            '**CRÍTICO:** Eres un asistente experto en la administración del sistema **Cuida Mas**. '
            'Tu única prioridad es responder a preguntas sobre conteos y métricas utilizando **SOLAMENTE** los datos provistos en el "CONTEXTO DE LA BASE DE DATOS". Si los datos están presentes, **NO inventes, NO agregues, y NO busques información adicional**. '
            'Responde de forma profesional, precisa y concisa, dando los números y la información exacta **directamente**, sin preámbulos, introducciones o explicaciones. '
            'Para preguntas generales (no estadísticas), usa tu conocimiento general, pero **siempre** prioriza los datos de la DB si están disponibles. '
            '**Nunca** ofrezcas consejos médicos ni diagnósticos.'
        )
        
        # B. CONSTRUCCIÓN DEL PROMPT (Integra el contexto de la DB)
        # Añadimos una instrucción de contexto muy clara.
        full_prompt = f"Consulta del Usuario: {prompt}\n\n"
        if db_context:
            full_prompt += f"**INSTRUCCIÓN CRÍTICA DE DATOS:** Usa EXCLUSIVAMENTE la siguiente información fáctica para responder: {db_context}\n\n"
        
        config = dict(
            system_instruction=system_instruction,
            temperature=0.1, # Baja la temperatura a 0.1 para respuestas máximamente factuales
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