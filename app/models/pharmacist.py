# app/models/pharmacist.py
from ..supabase_admin import supabase_admin_client
from flask import g # Importante para registrar quién hace los cambios
from datetime import datetime # Necesario para la fecha de adquisición/registro

class Pharmacist:
    def __init__(self):
        self.db = supabase_admin_client

    def get_dashboard_stats(self):
        """Obtiene estadísticas básicas para el dashboard del farmacéutico."""
        try:
            medicines_res = self.db.table('inventario').select('id', count='exact').execute()
            supplies_res = self.db.table('suministros').select('id', count='exact').execute()
            # Asumiendo que el umbral es 10 para 'low_stock'
            low_stock_res = self.db.table('inventario').select('id', count='exact').lt('stock', 10).execute() 
            stats = {
                'medicines_count': medicines_res.count or 0,
                'supplies_count': supplies_res.count or 0,
                'low_stock_count': low_stock_res.count or 0
            }
            return stats, None
        except Exception as e:
            return {}, str(e)

    # --- MÉTODO AÑADIDO: Añadir Ítem (Soluciona el error de atributo 'add_inventory_item') ---
    def add_inventory_item(self, name, stock, category_id, provider_id=None):
        """Añade un nuevo ítem de inventario a la DB y registra en el historial."""
        try:
            # 1. Validación y conversión
            stock_int = int(stock)
            category_int = int(category_id)
            # El proveedor es opcional, puede ser None
            provider_int = int(provider_id) if provider_id else None
            
            if stock_int <= 0:
                return False, "El stock inicial debe ser mayor que cero."
            
            # 2. Inserción en Inventario
            response = self.db.table('inventario').insert({
                "nombre": name,
                "stock": stock_int,
                "id_categoria": category_int,
                "id_proveedor": provider_int,
                "fecha_adquisicion": datetime.now().isoformat()
            }).execute()
            
            # Obtenemos el ID del ítem recién creado para el historial
            new_item_id = response.data[0]['id'] if response.data else None
            
            if new_item_id:
                # 3. Registrar en el Historial
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
            print(f"Error al añadir ítem: {e}")
            if 'foreign key constraint' in str(e).lower():
                return False, "Categoría o Proveedor no existen (clave externa)."
            return False, f"Error de la base de datos: {str(e)}"

    # --- MÉTODO AÑADIDO: Reabastecer (Necesario para la ruta restock) ---
    def restock_medicine(self, med_id, quantity):
        """Actualiza el stock de un medicamento existente (reabastecimiento)."""
        try:
            med_id_int = int(med_id)
            quantity_int = int(quantity)

            # 1. Obtener stock actual
            res = self.db.table('inventario').select('stock').eq('id', med_id_int).maybe_single().execute()
            current = res.data
            
            if not current:
                return False, "Medicamento no encontrado."
                
            old_stock = current['stock']
            new_stock = old_stock + quantity_int
            
            # 2. Actualizar stock
            self.db.table('inventario').update({'stock': new_stock}).eq('id', med_id_int).execute()
            
            # 3. Registrar en el historial
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

    def get_full_inventory(self):
        """Obtiene una lista completa de todos los medicamentos del inventario."""
        try:
            # Selecciona inventario con la categoría relacionada
            response = self.db.table('inventario').select('*, categoria:categorias_inventario(id, nombre)').order('nombre').execute()
            return response.data, None
        except Exception as e:
            print(f"Error al obtener el inventario completo: {e}")
            return [], str(e)

    def get_all_supplies(self):
        """Obtiene una lista completa de todos los suministros."""
        try:
            response = self.db.table('suministros').select('*').order('nombre').execute()
            return response.data, None
        except Exception as e:
            print(f"Error al obtener todos los suministros: {e}")
            return [], str(e)

    def get_filtered_inventory(self, search_term='', category_id=None):
        """Obtiene inventario aplicando filtros opcionales de búsqueda y categoría."""
        try:
            query = self.db.table('inventario').select('*, categoria:categorias_inventario(id, nombre), proveedor:proveedores(nombre)').order('nombre')
            if search_term:
                # Búsqueda por nombre
                query = query.ilike('nombre', f'%{search_term}%')
            if category_id and category_id.isdigit():
                # Filtrado por categoría
                query = query.eq('id_categoria', int(category_id))
            response = query.execute()
            return response.data, None
        except Exception as e:
            return [], str(e)

    def update_medicine(self, med_id, new_stock, new_name, new_category_id):
        """Actualiza el nombre, stock y categoría de un medicamento y registra el cambio."""
        try:
            # 1. Obtener datos actuales para el historial
            res = self.db.table('inventario').select('stock, nombre, id_categoria').eq('id', med_id).maybe_single().execute()
            current = res.data if res and res.data else None
            
            update_data = {
                'stock': int(new_stock),
                'nombre': new_name,
                'id_categoria': int(new_category_id) if new_category_id and new_category_id.isdigit() else None
            }
            # 2. Ejecutar actualización
            response = self.db.table('inventario').update(update_data).eq('id', med_id).execute()

            # 3. Registrar en el historial
            if current:
                self.db.table('historial_inventario').insert({
                    'producto_id': med_id,
                    'usuario_id': g.profile['id'],
                    'accion': 'Actualización',
                    'valor_anterior': f"Nombre: {current.get('nombre')}, Stock: {current.get('stock')}",
                    'valor_nuevo': f"Nombre: {new_name}, Stock: {new_stock}"
                }).execute()
            
            return response.data, None
        except Exception as e:
            return None, str(e)

    def get_low_stock_items(self, threshold=5):
        """Obtiene todos los ítems de inventario que están por debajo del umbral de stock."""
        try:
            response = self.db.table('inventario').select('*, categoria:categorias_inventario(nombre)').lt('stock', threshold).order('stock').execute()
            return response.data, None
        except Exception as e:
            return [], str(e)

    def get_inventory_history(self, product_id=None):
        """Obtiene el historial de cambios del inventario, opcionalmente filtrado por producto."""
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
        """Obtiene todas las categorías de inventario."""
        try:
            response = self.db.table('categorias_inventario').select('id, nombre').order('nombre').execute()
            return response.data, None
        except Exception as e:
            return [], str(e)

    # --- Funciones de Recetas (Prescripciones) ---
    def get_all_prescriptions(self):
        """Obtiene todas las prescripciones con detalles de doctor y paciente."""
        try:
            # Nota: Usamos 'perfiles!prescripcioness_id_doctor_fkey' para el JOIN.
            response = self.db.table('prescripcioness').select(
                '*, doctor:perfiles!prescripcioness_id_doctor_fkey(nombre_completo), paciente:pacientes(nombre_completo)'
            ).order('created_at', desc=True).execute()
            return response.data, None
        except Exception as e:
            return [], str(e)

    def get_prescription_details(self, prescription_id):
        """Obtiene detalles de una prescripción específica."""
        try:
            response = self.db.table('prescripcioness').select(
                '*, doctor:perfiles!prescripcioness_id_doctor_fkey(nombre_completo), paciente:pacientes(*)'
            ).eq('id', prescription_id).maybe_single().execute()
            return response.data, None
        except Exception as e:
            return None, str(e) 