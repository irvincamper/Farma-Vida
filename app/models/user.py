# app/models/user.py

# ¡LA IMPORTACIÓN CORRECTA!
# Importamos la instancia 'supabase' desde nuestro archivo central de extensiones.
from ..extensions import supabase

class User:
    """
    Clase que encapsula las operaciones que un usuario puede realizar
    sobre su propio perfil.
    """
    def __init__(self, user_id):
        """
        El constructor recibe el user_id (UUID de autenticación) del usuario.
        """
        # ¡LA REFERENCIA CORRECTA! Usamos supabase.client.
        self.db = supabase.client
        self.user_id = user_id

    def update_profile_name(self, new_full_name):
        """
        Actualiza el 'nombre_completo' del usuario en la tabla 'perfiles'.
        """
        if not new_full_name or len(new_full_name.strip()) == 0:
            return None, "El nombre completo no puede estar vacío."
            
        try:
            response = self.db.table('perfiles') \
                .update({'nombre_completo': new_full_name}) \
                .eq('id', self.user_id) \
                .execute()
            return response.data, None
        except Exception as e:
            print(f"Error en modelo User al actualizar nombre para {self.user_id}: {e}")
            return None, "No se pudo actualizar el perfil."

    def get_profile(self):
        """
        Obtiene la información completa del perfil del propio usuario.
        """
        try:
            response = self.db.table('perfiles') \
                .select('*, roles(nombre)') \
                .eq('id', self.user_id) \
                .single() \
                .execute()
            return response.data, None
        except Exception as e:
            print(f"Error en modelo User al obtener perfil para {self.user_id}: {e}")
            return None, "No se pudo obtener el perfil."