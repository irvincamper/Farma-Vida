from ..extensions import supabase
import random
import string 

class Doctor:
    def __init__(self):
        self.db = supabase.client

    def get_dashboard_stats(self, doctor_id):
        try:
            # Cuenta las recetas emitidas por este doctor
            prescriptions_res = self.db.table('prescripcioness').select('id', count='exact').eq('id_doctor', doctor_id).execute()
            
            # Cuenta los pacientes únicos atendidos por este doctor
            patients_data = self.db.table('prescripcioness').select('id_paciente').eq('id_doctor', doctor_id).execute()
            
            unique_patients = set()
            if patients_data.data:
                for p in patients_data.data:
                    if p.get('id_paciente'):
                        unique_patients.add(p['id_paciente'])
            
            stats = {
                'prescriptions_count': prescriptions_res.count or 0,
                'patients_count': len(unique_patients)
            }
            return stats, None
        except Exception as e: 
            print(f"Error en get_dashboard_stats: {e}")
            return {}, str(e)

    # --- MÉTODO: Obtener SOLO pacientes del doctor (Filtrado) ---
    def get_my_patients(self, doctor_id):
        """
        Obtiene la lista de pacientes que han recibido al menos una receta de este doctor.
        """
        try:
            # 1. Obtener IDs de pacientes de las recetas del doctor
            pres_res = self.db.table('prescripcioness').select('id_paciente').eq('id_doctor', doctor_id).execute()
            
            if not pres_res.data:
                return [], None 
            
            # Extraer IDs únicos usando un set
            patient_ids = list(set([p['id_paciente'] for p in pres_res.data]))
            
            if not patient_ids:
                return [], None

            # 2. Obtener los detalles completos de esos pacientes
            response = self.db.table('pacientes').select('*').in_('id', patient_ids).order('nombre_completo').execute()
            return response.data, None
            
        except Exception as e:
            print(f"Error obteniendo mis pacientes: {e}")
            return [], str(e)

    def get_all_patients(self):
        """Obtiene TODOS los pacientes del sistema (para búsqueda general/autocompletar)."""
        try:
            response = self.db.table('pacientes').select('*').order('nombre_completo').execute()
            return response.data, None
        except Exception as e: 
            return [], str(e)
            
    def search_patients_by_name(self, query):
        """Busca pacientes por nombre completo, útil para autocompletar."""
        try:
            if len(query) < 3:
                 response = self.db.table('pacientes').select('id, nombre_completo, curp').limit(10).order('nombre_completo').execute()
                 return response.data, None
            
            # Intenta búsqueda insensible a mayúsculas/minúsculas
            response = self.db.table('pacientes').select('id, nombre_completo, curp').ilike('nombre_completo', f'%{query}%').order('nombre_completo').limit(15).execute()
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
                    return None, f"El correo electrónico '{email}' ya está registrado."
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
            password_to_return = "El paciente ya existía."
            email_to_return = ""
            
            # 1. Búsqueda por ID 
            if patient_data.get('id_paciente'):
                patient_id = int(patient_data['id_paciente'])
                patient_res = self.db.table('pacientes').select('user_id').eq('id', patient_id).maybe_single().execute()
                if patient_res.data and patient_res.data[0].get('user_id'):
                    try:
                         user_info = self.db.auth.admin.get_user_by_id(patient_res.data[0]['user_id'])
                         email_to_return = user_info.user.email
                    except:
                         email_to_return = "Registrado"

            # 2. Búsqueda por CURP
            elif patient_data.get('curp'):
                curp_value = patient_data['curp']
                patient_res = self.db.table('pacientes').select('id, user_id').eq('curp', curp_value).execute()

                if patient_res.data:
                    patient_id = patient_res.data[0]['id']
                    email_to_return = "Paciente Existente"
                
                # 3. Creación de Nuevo Paciente
                else:
                    email_to_return = f"paciente.{curp_value.lower()}@farma-vida.com"
                    result, error = self.create_patient_full(
                        full_name=patient_data['nombre_completo'],
                        email=email_to_return,
                        curp=curp_value,
                        sexo=patient_data.get('sexo')
                    )
                    if error:
                        return None, f"No se pudo crear el nuevo paciente: {error}"
                    
                    password_to_return = result['password']
                    
                    new_patient_res = self.db.table('pacientes').select('id').eq('curp', curp_value).execute()
                    if new_patient_res.data:
                        patient_id = new_patient_res.data[0]['id']
                    else:
                        return None, "Error al recuperar ID del nuevo paciente."
            else:
                 return None, "Falta el ID del paciente o la CURP."

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
                return None, "Error interno: No se pudo determinar el ID del paciente."

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

    # --- NUEVO MÉTODO: Obtener perfil del doctor ---
    def get_doctor_profile(self, doctor_id):
        """Obtiene los datos del perfil del doctor desde la tabla perfiles."""
        try:
            response = self.db.table('perfiles').select('*, roles(nombre)').eq('id', doctor_id).maybe_single().execute()
            if response and response.data:
                return response.data, None
            return None, "Perfil no encontrado"
        except Exception as e:
            return None, str(e)