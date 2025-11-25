# app/models/doctor.py
from ..extensions import supabase
import random
import string

class Doctor:
    def __init__(self):
        self.db = supabase.client

    # --- INICIO DE LA MODIFICACIÓN: FUNCIÓN CORREGIDA ---
    def get_dashboard_stats(self, doctor_id):
        try:
            # Esta consulta para contar recetas es correcta y se mantiene.
            prescriptions_res = self.db.table('prescripcioness').select('id', count='exact').eq('id_doctor', doctor_id).execute()
            
            # Ahora llamamos a nuestra nueva función SQL para contar pacientes de forma correcta.
            patients_res = self.db.rpc('contar_pacientes_de_doctor', {'id_doctor_param': str(doctor_id)}).execute()
            
            stats = {
                'prescriptions_count': prescriptions_res.count or 0,
                'patients_count': patients_res.data or 0 # La función RPC devuelve el número directamente.
            }
            return stats, None
        except Exception as e: 
            print(f"Error en get_dashboard_stats: {e}") # Añadimos un print para futura depuración
            return {}, str(e)
    # --- FIN DE LA MODIFICACIÓN ---

    def get_all_patients(self):
        try:
            response = self.db.table('pacientes').select('*').order('nombre_completo').execute()
            return response.data, None
        except Exception as e: 
            return [], str(e)

    def create_patient_full(self, full_name, email, curp, birth_date=None, contact_info=None, sexo=None, password=None):
        try:
            curp_check = self.db.table('pacientes').select('id').eq('curp', curp).execute()
            if curp_check.data:
                return None, f"Ya existe un paciente registrado con la CURP: {curp}."

            user_id = None
            if not password:
                password_characters = string.ascii_letters + string.digits + string.punctuation
                password = ''.join(random.choice(password_characters) for i in range(12))

            try:
                auth_response = self.db.auth.sign_up({
                    "email": email, "password": password,
                    "options": {"data": {"rol": "paciente"}}
                })
                user_id = auth_response.user.id
            except Exception as e:
                error_message = str(e)
                if "User already registered" in error_message:
                    return None, f"El correo electrónico '{email}' ya está registrado. No se puede crear el paciente."
                else:
                    return None, error_message
            
            if not user_id:
                return None, "No se pudo crear el ID del usuario de autenticación."
            
            self.db.table('perfiles').insert({
                "id": user_id, "nombre_completo": full_name, "id_de_rol": 3
            }).execute()
            
            self.db.table('pacientes').insert({
                "nombre_completo": full_name, "curp": curp, "fecha_nacimiento": birth_date,
                "info_contacto": contact_info, "user_id": user_id, "sexo": sexo
            }).execute()
                
            return {"password": password}, None
        except Exception as e:
            return None, f"Hubo un error al guardar los datos del paciente: {e}"
            
    def get_patient_by_id(self, patient_id):
        try:
            response = self.db.table('pacientes').select('*').eq('id', patient_id).maybe_single().execute()
            if response and response.data:
                return response.data, None
            return None, None
        except Exception as e: 
            return None, str(e)

    def create_prescription(self, data):
        try:
            res = self.db.table('prescripcioness').insert(data).execute()
            return res.data[0], None
        except Exception as e: 
            return None, str(e)

    def find_or_create_patient_and_add_prescription(self, patient_data, prescription_data):
        try:
            patient_id = None
            password_to_return = "El paciente ya existía, no se generó nueva contraseña."
            email_to_return = ""

            patient_res = self.db.table('pacientes').select('id, user_id').eq('curp', patient_data['curp']).execute()

            if patient_res.data:
                patient_id = patient_res.data[0]['id']
                user_id = patient_res.data[0]['user_id']
                user_info = self.db.auth.admin.get_user_by_id(user_id)
                email_to_return = user_info.user.email
            else:
                email_to_return = f"paciente.{patient_data['curp'].lower()}@farma-vida.com"
                
                result, error = self.create_patient_full(
                    full_name=patient_data['nombre_completo'],
                    email=email_to_return,
                    curp=patient_data['curp'],
                    sexo=patient_data['sexo']
                )

                if error:
                    return None, f"No se pudo crear el nuevo paciente: {error}"
                
                password_to_return = result['password']
                
                new_patient_res = self.db.table('pacientes').select('id').eq('curp', patient_data['curp']).execute()
                if new_patient_res.data:
                    patient_id = new_patient_res.data[0]['id']
                else:
                    return None, "Se creó el paciente pero no se pudo encontrar para asignarle la receta."

            if patient_id:
                prescription_data['id_paciente'] = patient_id
                new_prescription, error = self.create_prescription(prescription_data)
                if error:
                    return None, f"Error al guardar la receta: {error}"
                
                return {
                    "email": email_to_return,
                    "password": password_to_return,
                    "prescription": new_prescription
                }, None
            else:
                return None, "No se pudo obtener el ID del paciente para crear la receta."

        except Exception as e:
            return None, str(e)

    def get_all_prescriptions(self, doctor_id):
        try:
            response = self.db.table('prescripcioness').select(
                '*, paciente:pacientes(nombre_completo)'
            ).eq('id_doctor', doctor_id).order('created_at', desc=True).execute()
            return response.data, None
        except Exception as e:
            return [], str(e)

    def get_prescription_by_id(self, prescription_id):
        try:
            response = self.db.table('prescripcioness').select(
                '*, paciente:pacientes(*), doctor:perfiles!prescripcioness_id_doctor_fkey(nombre_completo)'
            ).eq('id', prescription_id).maybe_single().execute()
            if response and response.data:
                return response.data, None
            return None, None
        except Exception as e:
            return None, str(e)