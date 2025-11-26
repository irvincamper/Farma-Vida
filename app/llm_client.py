"""Light wrapper for an LLM provider.

This module is intentionally small and defensive: it reads the API key from
environment variables, attempts to use the `openai` package if present, and
returns a helpful message if no provider/key is configured.

We avoid hard-coding any secrets in the repository.
"""
import os
from typing import Dict

OPENAI_KEY = os.getenv('OPENAI_API_KEY') or os.getenv('OPENAI_KEY')


def call_llm(prompt: str, model: str = 'gpt-3.5-turbo') -> Dict[str, str]:
    """Call an LLM provider and return a safe response dict.

    Returns: { 'ok': True/False, 'response': str }
    """
    if not OPENAI_KEY:
        return {'ok': False, 'response': 'LLM no configurado. Establece OPENAI_API_KEY en las variables de entorno.'}

    try:
        import openai
    except Exception:
        return {'ok': False, 'response': 'Paquete openai no instalado en el entorno. Añádelo a requirements si quieres usar LLM real.'}

    try:
        openai.api_key = OPENAI_KEY
        # Chat completions (simple wrapper) - adjust to your plan/provider if needed
        completion = openai.ChatCompletion.create(
            model=model,
            messages=[{'role': 'system', 'content': 'Eres un asistente útil para el administrador del sistema.'},
                      {'role': 'user', 'content': prompt}],
            temperature=0.2,
            max_tokens=600
        )
        text = ''
        # extract assistant reply
        if completion and completion.choices:
            text = completion.choices[0].message.get('content', '')

        return {'ok': True, 'response': text}
    except Exception as e:
        return {'ok': False, 'response': f'Error al llamar al LLM: {e}'}
