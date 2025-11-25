# app/models/pharmacist.py
from ..supabase_admin import supabase_admin_client
from flask import g # Importante para registrar quién hace los cambios

class Pharmacist:
    def __init__(self):
        self.db = supabase_admin_client

    def get_dashboard_stats(self):
        try:
            medicines_res = self.db.table('inventario').select('id', count='exact').execute()
            supplies_res = self.db.table('suministros').select('id', count='exact').execute()
            low_stock_res = self.db.table('inventario').select('id', count='exact').lt('stock', 10).execute()
            stats = {
                'medicines_count': medicines_res.count or 0,
                'supplies_count': supplies_res.count or 0,
                'low_stock_count': low_stock_res.count or 0
            }
            return stats, None
        except Exception as e:
            return {}, str(e)

    # --- INICIO DE LA MODIFICACIÓN: MÉTODO AÑADIDO ---
    # Esta es la función que tu ruta 'doctor.py' estaba buscando.
    def get_full_inventory(self):
        """
        Obtiene una lista completa de todos los medicamentos del inventario.
        """
        try:
            # Es similar a get_filtered_inventory pero sin filtros.
            response = self.db.table('inventario').select('*, categoria:categorias_inventario(id, nombre)').order('nombre').execute()
            return response.data, None
        except Exception as e:
            print(f"Error al obtener el inventario completo: {e}")
            return [], str(e)

    # También añadimos una función para obtener todos los suministros, por si la necesitas.
    def get_all_supplies(self):
        """
        Obtiene una lista completa de todos los suministros.
        """
        try:
            response = self.db.table('suministros').select('*').order('nombre').execute()
            return response.data, None
        except Exception as e:
            print(f"Error al obtener todos los suministros: {e}")
            return [], str(e)
    # --- FIN DE LA MODIFICACIÓN ---

    def get_filtered_inventory(self, search_term='', category_id=None):
        try:
            query = self.db.table('inventario').select('*, categoria:categorias_inventario(id, nombre)').order('nombre')
            if search_term:
                query = query.ilike('nombre', f'%{search_term}%')
            if category_id and category_id.isdigit():
                query = query.eq('categoria_id', int(category_id))
            response = query.execute()
            return response.data, None
        except Exception as e:
            return [], str(e)

    def update_medicine(self, med_id, new_stock, new_name, new_category_id):
        try:
            res = self.db.table('inventario').select('stock, nombre, categoria_id').eq('id', med_id).maybe_single().execute()
            current = res.data if res and res.data else None
            
            update_data = {
                'stock': int(new_stock),
                'nombre': new_name,
                'categoria_id': int(new_category_id) if new_category_id and new_category_id.isdigit() else None
            }
            response = self.db.table('inventario').update(update_data).eq('id', med_id).execute()

            # Registrar en el historial
            self.db.table('historial_inventario').insert({
                'producto_id': med_id,
                'usuario_id': g.profile['id'],
                'accion': 'Actualización',
                'valor_anterior': f"Nombre: {current['nombre']}, Stock: {current['stock']}",
                'valor_nuevo': f"Nombre: {new_name}, Stock: {new_stock}"
            }).execute()
            
            return response.data, None
        except Exception as e:
            return None, str(e)

    def get_low_stock_items(self, threshold=5):
        try:
            response = self.db.table('inventario').select('*, categoria:categorias_inventario(nombre)').lt('stock', threshold).order('stock').execute()
            return response.data, None
        except Exception as e:
            return [], str(e)

    def get_inventory_history(self, product_id=None):
        try:
            query = self.db.table('historial_inventario').select(
                '*, producto:inventario(nombre), usuario:perfiles(nombre_completo)'
            ).order('fecha', desc=True)
            if product_id:
                query = query.eq('producto_id', product_id)
            response = query.execute()
            return response.data, None
        except Exception as e:
            return [], str(e)

    def get_all_categories(self):
        try:
            response = self.db.table('categorias_inventario').select('id, nombre').order('nombre').execute()
            return response.data, None
        except Exception as e:
            return [], str(e)

    # --- Funciones de Recetas ---
    def get_all_prescriptions(self):
        try:
            response = self.db.table('prescripcioness').select(
                '*, doctor:perfiles!prescripcioness_id_doctor_fkey(nombre_completo), paciente:pacientes(nombre_completo)'
            ).order('created_at', desc=True).execute()
            return response.data, None
        except Exception as e:
            return [], str(e)

    def get_prescription_details(self, prescription_id):
        try:
            response = self.db.table('prescripcioness').select(
                '*, doctor:perfiles!prescripcioness_id_doctor_fkey(nombre_completo), paciente:pacientes(*)'
            ).eq('id', prescription_id).maybe_single().execute()
            return response.data, None
        except Exception as e:
            return None, str(e)