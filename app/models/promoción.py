# app/models/promotion.py
from ..extensions import supabase

class Promotion:
    def __init__(self):
        self.db = supabase.client

    def get_all(self):
        try:
            # Tu código original - sin cambios
            res = self.db.table('promociones').select('*').order('fecha_fin', desc=True).execute()
            return res.data, None
        except Exception as e: return [], str(e)

    def get_by_id(self, promo_id):
        try:
            # Tu código original - sin cambios
            res = self.db.table('promociones').select('*').eq('id', promo_id).maybe_single().execute()
            if res and res.data:
                return res.data, None
            return None, None
        except Exception as e: return None, str(e)

    def create(self, titulo, descripcion, fecha_inicio, fecha_fin):
        try:
            # Tu código original - sin cambios
            res = self.db.table('promociones').insert({
                'titulo': titulo, 'descripcion': descripcion,
                'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin,
                'activa': True  # Asumo que al crear siempre está activa
            }).execute()
            return res.data, None
        except Exception as e: return None, str(e)

    def update(self, promo_id, titulo, descripcion, fecha_inicio, fecha_fin):
        try:
            # Tu código original - sin cambios
            res = self.db.table('promociones').update({
                'titulo': titulo, 'descripcion': descripcion,
                'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin
            }).eq('id', promo_id).execute()
            return res.data, None
        except Exception as e: return None, str(e)

    def toggle_status(self, promo_id, current_status):
        try:
            # Tu código original - sin cambios
            self.db.table('promociones').update({'activa': not current_status}).eq('id', promo_id).execute()
            return True, None
        except Exception as e: return False, str(e)

    # --- INICIO DE LA MODIFICACIÓN ---
    # He añadido este nuevo método sin tocar los demás.
    # Es específico para la acción del botón "Finalizar".
    def finalize(self, promo_id):
        """
        Finaliza (desactiva) una promoción específica. Establece 'activa' en False.
        """
        try:
            self.db.table('promociones').update({'activa': False}).eq('id', promo_id).execute()
            return True, None
        except Exception as e:
            return False, str(e)
    # --- FIN DE LA MODIFICACIÓN ---