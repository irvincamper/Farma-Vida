# app/models/patient.py

# ¡LA IMPORTACIÓN CORRECTA!
# Importamos nuestra instancia 'supabase' desde el archivo central de extensiones.
from ..extensions import supabase

class Patient:
    """
    Clase que encapsula la lógica de negocio para las acciones de un Paciente.
    """
    def __init__(self, user_id):
        """
        El constructor recibe el user_id (el UUID de autenticación) del paciente.
        """
        self.db = supabase.client
        self.user_id = user_id

    def get_my_medical_history(self):
        """
        Obtiene el historial médico completo del paciente que ha iniciado sesión.
        """
        try:
            # 1. Buscamos el ID numérico del paciente en la tabla 'pacientes'
            patient_record = self.db.table('pacientes').select('id').eq('user_id', self.user_id).single().execute()
            if not patient_record.data:
                return [], "No se encontró un registro de paciente para este usuario."
            
            patient_id = patient_record.data['id']

            # 2. Obtenemos los registros médicos para ese paciente
            # (Asegúrate de que tus tablas se llamen 'registros_medicos', 'perfiles', 'recetas', 'inventario')
            response = self.db.table('registros_medicos') \
                .select('*, doctor:perfiles(nombre_completo), recetas(*, medicamento:inventario(nombre))') \
                .eq('patient_id', patient_id) \
                .order('fecha_consulta', desc=True) \
                .execute()
            
            return response.data, None
        except Exception as e:
            print(f"Error al obtener historial para {self.user_id}: {e}")
            return [], str(e)