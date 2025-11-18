# app/models/provider.py
from ..extensions import supabase

class Provider:
    def __init__(self):
        self.db = supabase.client

    def create(self, nombre, telefono=None, email=None, direccion=None):
        """Crea un nuevo proveedor en la base de datos."""
        try:
            res = self.db.table('proveedores').insert({
                'nombre': nombre, 'telefono': telefono, 'email': email, 'direccion': direccion
            }).execute()
            return res.data, None
        except Exception as e:
            print(f"Error al crear proveedor: {e}")
            return None, str(e)

    # --- ¡NUEVO MÉTODO AÑADIDO! ---
    def get_all(self):
        """Obtiene una lista de todos los proveedores."""
        try:
            response = self.db.table('proveedores').select('*').order('nombre').execute()
            return response.data, None
        except Exception as e:
            print(f"Error al obtener proveedores: {e}")
            return [], str(e)