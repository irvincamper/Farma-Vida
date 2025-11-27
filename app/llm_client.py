"""Light wrapper for an LLM provider.

This module is configured to use the Google Gemini API (google-genai) and is 
enhanced to handle security blocks and integrate context (RAG) from the database.
"""
import os
from typing import Dict, Optional

# 1. CLAVE: Buscamos la variable de entorno GEMINI_API_KEY
GEMINI_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GEMINI_KEY')


# Modificamos la función para aceptar un contexto de base de datos opcional
def call_llm(
    prompt: str, 
    db_context: Optional[str] = None, # <--- NUEVO PARÁMETRO
    model: str = 'gemini-2.5-flash'
) -> Dict[str, str]:
    """Call an LLM provider and return a safe response dict, potentially enhanced with DB context.

    db_context: Cadena de texto que contiene información extraída de la base de datos.
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
        # 4. Inicializar el cliente
        client = genai.Client(api_key=GEMINI_KEY)

        # 5. Configurar la Instrucción del Sistema y el Contenido de la Solicitud
        
        # A. INSTRUCCIÓN MEJORADA (Soluciona el bloqueo de temas de salud)
        system_instruction = (
            'Eres un asistente experto en información general farmacéutica y en la administración del sistema Farma-Vida. '
            'Responde de forma profesional, precisa y concisa. **Nunca ofrezcas consejos médicos ni diagnósticos; solo proporciona información general y factual.**'
        )
        
        # B. CONSTRUCCIÓN DEL PROMPT (Integra el contexto de la DB)
        # El modelo sabrá si se le pasó información de la DB.
        full_prompt = f"Consulta del Usuario: {prompt}\n\n"
        if db_context:
            full_prompt += f"CONTEXTO DE LA BASE DE DATOS PARA RESPONDER: {db_context}\n\n"
        
        config = dict(
            system_instruction=system_instruction,
            temperature=0.2,
            max_output_tokens=600
        )
        
        # 6. Llamada a la API de Gemini (generate_content)
        completion = client.models.generate_content(
            model=model,
            contents=full_prompt, # Usamos el prompt completo (usuario + contexto DB)
            config=config
        )
        
        # 7. EXTRACCIÓN Y VERIFICACIÓN DE RESPUESTA DE GEMINI
        text = ''
        
        if completion.candidates and completion.candidates[0].finish_reason.name == 'SAFETY':
             text = "Lo siento, mi respuesta fue bloqueada por las políticas de seguridad de contenido. Intenta reformular tu pregunta."
        elif completion.text:
            text = completion.text
        else:
            text = "Lo siento, hubo un problema al generar la respuesta o la respuesta fue vacía."

        return {'ok': True, 'response': text}
        
    except Exception as e:
        return {'ok': False, 'response': f'Error al llamar al LLM: {e}'}