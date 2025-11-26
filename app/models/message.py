from ..extensions import supabase
from flask import current_app, session
from datetime import datetime


_IN_MEMORY_STORE = {}


class Message:
    """
    Modelo simple para manejar mensajes directos entre usuarios (paciente <-> doctor).
    Asume una tabla `mensajes` en la base de datos con columnas mínimas:
    - id (serial/uuid)
    - sender_id (UUID): id del perfil que envía
    - receiver_id (UUID): id del perfil que recibe
    - content (text)
    - created_at (timestamp) con valor por defecto NOW()
    - read (boolean) opcional
    """

    def __init__(self):
        self.db = supabase.client

    def get_conversation(self, user_a_id, user_b_id, limit=100):
        """Devuelve la conversación entre dos perfiles ordenada ascendente por fecha."""
        try:
            # Consultar mensajes donde (sender = A AND receiver = B) OR (sender = B AND receiver = A)
            resp = self.db.table('mensajes') \
                .select('*') \
                .or_(f"and(sender_id.eq.{user_a_id},receiver_id.eq.{user_b_id}),and(sender_id.eq.{user_b_id},receiver_id.eq.{user_a_id})") \
                .order('created_at', asc=True) \
                .limit(limit) \
                .execute()
            return resp.data or [], None
        except Exception as e:
            # Fallback en modo desarrollo: usar almacenamiento en memoria si hay un perfil de dev en sesión
            try:
                if session and session.get('profile_data'):
                    key = tuple(sorted([str(user_a_id), str(user_b_id)]))
                    convo = _IN_MEMORY_STORE.get(key, [])
                    return convo[-limit:], None
            except Exception:
                pass
            return [], str(e)

    def create_message(self, sender_id, receiver_id, content):
        """Inserta un nuevo mensaje en la tabla `mensajes`."""
        try:
            payload = {
                'sender_id': sender_id,
                'receiver_id': receiver_id,
                'content': content
            }
            resp = self.db.table('mensajes').insert(payload).execute()
            # resp.data puede devolver el registro insertado dependiendo de la configuración
            return resp.data, None
        except Exception as e:
            # Fallback en modo desarrollo: almacenar mensaje en memoria si hay perfil de dev en sesión
            try:
                if session and session.get('profile_data'):
                    key = tuple(sorted([str(sender_id), str(receiver_id)]))
                    item = {
                        'sender_id': sender_id,
                        'receiver_id': receiver_id,
                        'content': content,
                        'created_at': datetime.utcnow().isoformat() + 'Z',
                        'read': False
                    }
                    _IN_MEMORY_STORE.setdefault(key, []).append(item)
                    return item, None
            except Exception:
                pass
            return None, str(e)

    def mark_as_read(self, sender_id, receiver_id):
        """Marca como leídos los mensajes enviados por `sender_id` a `receiver_id`."""
        try:
            resp = self.db.table('mensajes').update({'read': True}).eq('sender_id', sender_id).eq('receiver_id', receiver_id).execute()
            return resp.data if resp and getattr(resp, 'data', None) else None, None
        except Exception as e:
            # Fallback en memoria en modo dev
            try:
                if session and session.get('profile_data'):
                    key = tuple(sorted([str(sender_id), str(receiver_id)]))
                    changed = []
                    for m in _IN_MEMORY_STORE.get(key, []):
                        if str(m.get('sender_id')) == str(sender_id) and str(m.get('receiver_id')) == str(receiver_id):
                            m['read'] = True
                            changed.append(m)
                    return changed, None
            except Exception:
                pass
            return None, str(e)
