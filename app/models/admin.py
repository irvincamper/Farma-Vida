# app/models/admin.py

from ..supabase_admin import supabase_admin_client
import random
import string

# **NOTA IMPORTANTE:**
# Para mantener la coherencia con app/routes/admin.py:
# administrador: 1
# doctor: 2
# farmaceutico: 3
# paciente: 4 
ROLE_PACIENTE_ID = 4 

class Admin:
    def __init__(self):
        self.db = supabase_admin_client

    def get_all_users_with_roles(self):
        try:
            # Selecciona todos los campos de perfiles y hace JOIN con roles
            response = self.db.table('perfiles').select('*, roles(id, nombre)').order('nombre_completo').execute()
            return response.data, None
        except Exception as e:
            print(f"Error al obtener todos los usuarios: {e}")
            return [], str(e)

    def create_any_user(self, full_name, email, role_id, password):
        """
        Crea un nuevo usuario completo con cualquier rol asignado,
        usando la contraseña proporcionada por el administrador.
        """
        user_id = None
        role_id_int = None
        
        try:
            # 1. Validación y conversión del ID de rol
            role_id_int = int(role_id)
            
            # 2. Creación en Supabase Auth
            auth_res = self.db.auth.sign_up({"email": email, "password": password})

            if not auth_res.user:
                # Esto es poco común si no se lanza una excepción, pero es una buena verificación
                return None, "Fallo al crear usuario en Auth (usuario no retornado)."
            
            user_id = auth_res.user.id
            
            # 3. Inserción en la tabla de Perfiles (Obligatoria)
            self.db.table('perfiles').insert({
                "id": user_id, 
                "nombre_completo": full_name, 
                "id_de_rol": role_id_int
            }).execute()

            # 4. Inserción en la tabla de Pacientes (Condicional)
            # CORRECCIÓN: Usamos ROLE_PACIENTE_ID = 4 para consistencia (Punto 1)
            if role_id_int == ROLE_PACIENTE_ID: 
                self.db.table('pacientes').insert({
                    # Asume que la tabla 'pacientes' usa user_id como FK
                    "user_id": user_id,
                    "nombre_completo": full_name, 
                    "info_contacto": email, 
                }).execute()
            
            return True, None
            
        except Exception as e:
            print(f"Error en create_any_user: {e}")
            
            # Si el error ocurrió DESPUÉS del sign_up (ej. fallo en insertar perfil), 
            # se recomienda borrar el usuario de Auth para limpiar la cuenta huérfana.
            if user_id:
                try:
                    self.db.auth.admin.delete_user(user_id)
                    print(f"Usuario {user_id} eliminado de Auth debido a fallo en la DB.")
                except Exception as del_e:
                    print(f"Alerta: No se pudo eliminar la cuenta huérfana de Auth: {del_e}")
            
            # Manejo de error de correo ya registrado (más legible)
            if 'already registered' in str(e).lower() or 'unique constraint' in str(e).lower():
                return None, "El correo electrónico ya está en uso o la clave única ya existe."
            
            return None, str(e)
            
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
            # Al eliminar el usuario de Auth, las RLS (Row Level Security) 
            # de Supabase deberían encargarse de eliminar la entrada en 'perfiles' por cascada.
            # Si no tienes configurada la cascada, DEBERÍAS eliminar primero de 'perfiles'.
            
            # 1. Eliminar de Auth (lo que dispara la eliminación de la DB si tienes cascada)
            self.db.auth.admin.delete_user(user_id)
            return True, None
        except Exception as e:
            print(f"Error al eliminar usuario: {e}")
            return False, str(e)