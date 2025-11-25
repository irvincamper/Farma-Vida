# app/models/admin.py

from ..supabase_admin import supabase_admin_client
import random
import string

class Admin:
    def __init__(self):
        self.db = supabase_admin_client

    def get_all_users_with_roles(self):
        try:
            response = self.db.table('perfiles').select('*, roles(id, nombre)').order('nombre_completo').execute()
            return response.data, None
        except Exception as e:
            print(f"Error al obtener todos los usuarios: {e}")
            return [], str(e)

    # --- FUNCIÓN MODIFICADA ---
    def create_any_user(self, full_name, email, role_id, password):
        """
        Crea un nuevo usuario completo con cualquier rol asignado,
        usando la contraseña proporcionada por el administrador.
        """
        try:
            auth_res = self.db.auth.sign_up({"email": email, "password": password})

            if not auth_res.user:
                return None, "Fallo al crear usuario en Auth."
            
            user_id = auth_res.user.id
            self.db.table('perfiles').insert({
                "id": user_id, 
                "nombre_completo": full_name, 
                "id_de_rol": int(role_id)
            }).execute()

            if int(role_id) == 3: # Asumiendo 3=paciente
                self.db.table('pacientes').insert({
                    "nombre_completo": full_name, 
                    "info_contacto": email, 
                    "user_id": user_id
                }).execute()
            
            return True, None
        except Exception as e:
            print(f"Error en create_any_user: {e}")
            if 'already registered' in str(e):
                return None, "El correo electrónico ya está en uso."
            return None, str(e)
    # --- FIN DE LA MODIFICACIÓN ---
            
    def get_user_by_id(self, user_id):
        try:
            response = self.db.table('perfiles').select('*, roles(id, nombre)').eq('id', user_id).maybe_single().execute()
            if response and response.data:
                return response.data, None
            return None, None
        except Exception as e:
            return None, str(e)

    def update_any_user(self, user_id, full_name, role_id):
        try:
            self.db.table('perfiles').update({
                'nombre_completo': full_name, 
                'id_de_rol': int(role_id)
            }).eq('id', user_id).execute()
            return True, None
        except Exception as e:
            return False, str(e)

    def delete_user_by_id(self, user_id):
        try:
            self.db.auth.admin.delete_user(user_id)
            return True, None
        except Exception as e:
            print(f"Error al eliminar usuario: {e}")
            return False, str(e)