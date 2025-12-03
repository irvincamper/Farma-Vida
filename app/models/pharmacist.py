# app/models/pharmacist.py
from ..supabase_admin import supabase_admin_client
from flask import g # Importante para registrar quién hace los cambios
from datetime import datetime # <--- ¡IMPORTACIÓN CRÍTICA AÑADIDA!

class Pharmacist:
    def __init__(self):
        self.db = supabase_admin_client

    # -------------------------------------------------------------------
    # ESTADÍSTICAS DEL DASHBOARD
    # -------------------------------------------------------------------

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

    # -------------------------------------------------------------------
    # GESTIÓN DE INVENTARIO (Añadidas funciones para 'Añadir Item')
    # -------------------------------------------------------------------

    def add_inventory_item(self, name, stock, category_id, provider_id=None):
        """Añade un nuevo ítem de inventario y registra el historial."""
        try:
            stock_int = int(stock)
            category_int = int(category_id)
            
            if stock_int <= 0:
                return False, "El stock inicial debe ser mayor que cero."

            # Crear el diccionario de datos base
            data_to_insert = {
                "nombre": name,
                "stock": stock_int,
                "categoria_id": category_int, 
                "created_at": datetime.now().isoformat()
            }

            # Si provider_id existe y es un número válido, lo añadimos al diccionario.
            if provider_id and str(provider_id).isdigit():
                # **DEJADO EN 'proveedor_id' TEMPORALMENTE** para probar una clave más antes de desactivarlo.
                try:
                    data_to_insert['proveedor_id'] = int(provider_id)
                except Exception as e:
                    data_to_insert['id_proveedor'] = int(provider_id)
                    
            
            response = self.db.table('inventario').insert(data_to_insert).execute()
            
            new_item_id = response.data[0]['id'] if response.data else None
            
            if new_item_id:
                # Registro en historial_inventario
                self.db.table('historial_inventario').insert({
                    'producto_id': new_item_id,
                    'usuario_id': g.profile['id'], 
                    'accion': 'Adición Inicial',
                    'valor_anterior': 'N/A',
                    'valor_nuevo': f"Stock: {stock_int}"
                }).execute()
            
            return True, None
            
        except ValueError:
            return False, "Error de tipo: Stock o ID de categoría/proveedor deben ser números enteros."
        except Exception as e:
            if 'foreign key constraint' in str(e).lower():
                return False, "Categoría o Proveedor no existen (clave externa)."
            # Devolvemos el error específico para el diagnóstico:
            return False, f"Error de la base de datos al añadir item: {str(e)}"
        
    def restock_medicine(self, med_id, quantity):
        """Actualiza el stock de un medicamento existente (reabastecimiento)."""
        try:
            med_id_int = int(med_id)
            quantity_int = int(quantity)

            res = self.db.table('inventario').select('stock').eq('id', med_id_int).maybe_single().execute()
            current = res.data
            
            if not current:
                return False, "Medicamento no encontrado."
                
            old_stock = current['stock']
            new_stock = old_stock + quantity_int
            
            self.db.table('inventario').update({'stock': new_stock}).eq('id', med_id_int).execute()
            
            self.db.table('historial_inventario').insert({
                'producto_id': med_id_int,
                'usuario_id': g.profile['id'],
                'accion': 'Reabastecimiento',
                'valor_anterior': f"Stock: {old_stock}",
                'valor_nuevo': f"Stock: {new_stock} (Adición: +{quantity_int})"
            }).execute()
            
            return True, None

        except ValueError:
            return False, "ID de medicamento y cantidad deben ser números enteros."
        except Exception as e:
            return False, f"Error al reabastecer: {str(e)}"
    
    # -------------------------------------------------------------------
    # FUNCIONES DE LECTURA DE DATOS
    # -------------------------------------------------------------------

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
            
    # -------------------------------------------------------------------
    # GESTIÓN DE PACIENTES (Añadida la función faltante)
    # -------------------------------------------------------------------
    
    def get_all_patients(self):
        """Obtiene la lista completa de pacientes."""
        try:
            # Supabase tabla 'pacientes'
            response = self.db.table('pacientes').select('*').order('nombre_completo').execute()
            return response.data, None
        except Exception as e:
            return [], f"Error al obtener pacientes: {str(e)}"
            
    # -------------------------------------------------------------------
    # FUNCIONES DE INVENTARIO RESTANTES
    # -------------------------------------------------------------------

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