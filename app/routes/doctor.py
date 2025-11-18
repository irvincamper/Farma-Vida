# app/routes/doctor.py

from flask import Blueprint, render_template, g, flash, request, redirect, url_for
from markupsafe import Markup

from ..decorators import role_required
from ..models.doctor import Doctor
from ..models.pharmacist import Pharmacist

doctor_bp = Blueprint('doctor', __name__)


@doctor_bp.route('/dashboard')
@role_required(allowed_roles=['doctor'])
def dashboard():
    doctor_handler = Doctor()
    doctor_id = g.profile['id']
    stats, error = doctor_handler.get_dashboard_stats(doctor_id)
    if error:
        flash("No se pudieron cargar las estadísticas del panel.", "danger")
        stats = {'prescriptions_count': 'N/A', 'patients_count': 'N/A'}
    return render_template('doctor/dashboard.html', stats=stats)


@doctor_bp.route('/patients')
@role_required(allowed_roles=['doctor'])
def patients():
    handler = Doctor()
    patients_list, err = handler.get_all_patients()
    if err:
        flash(f'Error al cargar la lista de pacientes: {err}', 'danger')
        patients_list = []
    return render_template('doctor/patients.html', patients=patients_list)


@doctor_bp.route('/prescriptions')
@role_required(allowed_roles=['doctor'])
def prescriptions():
    doctor_handler = Doctor()
    doctor_id = g.profile['id']
    prescriptions_list, error = doctor_handler.get_all_prescriptions(doctor_id)
    
    if error:
        flash(f"Error al cargar el historial de recetas: {error}", "danger")
        prescriptions_list = []
        
    return render_template('doctor/prescriptions.html', prescriptions=prescriptions_list)


# --- INICIO DE LA CORRECCIÓN ---
@doctor_bp.route('/inventory')
@role_required(allowed_roles=['doctor'])
def inventory():
    pharma_handler = Pharmacist()
    # Se utiliza la función correcta 'get_filtered_inventory' y se elimina la llamada a 'get_all_supplies'.
    inventory_list, inv_error = pharma_handler.get_filtered_inventory()
    
    if inv_error:
        flash("Error al cargar los datos del inventario.", "danger")
        
    return render_template('doctor/inventory.html', inventory_items=inventory_list or [])
# --- FIN DE LA CORRECCIÓN ---


@doctor_bp.route('/patients/new', methods=['GET', 'POST'])
@role_required(allowed_roles=['doctor'])
def create_patient():
    if request.method == 'POST':
        full_name = request.form.get('nombre_completo')
        email = request.form.get('email')
        birth_date = request.form.get('fecha_nacimiento') or None
        contact_info = request.form.get('info_contacto') or None
        curp_value = request.form.get('curp')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        sexo = request.form.get('sexo')

        if not curp_value:
             flash('Error: El campo CURP es obligatorio.', 'danger')
             return render_template('doctor/create_patient_form.html')
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('doctor/create_patient_form.html')
        if len(password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres.', 'danger')
            return render_template('doctor/create_patient_form.html')

        curp = curp_value.upper()
        doctor_handler = Doctor()
        
        _, error = doctor_handler.create_patient_full(
            full_name, email, curp, birth_date, contact_info, sexo, password=password
        )
        
        if error:
            flash(f'Error al crear el paciente: {error}', 'danger')
            return render_template('doctor/create_patient_form.html')
        else:
            flash(f'¡Paciente "{full_name}" creado con éxito!', 'success')
            return redirect(url_for('doctor.patients'))
            
    return render_template('doctor/create_patient_form.html')


@doctor_bp.route('/patient/<int:patient_id>')
@role_required(allowed_roles=['doctor'])
def view_patient_history(patient_id):
    handler = Doctor()
    patient, error = handler.get_patient_by_id(patient_id)
    if error or not patient:
        flash("No se pudo encontrar la información del paciente.", "danger")
        return redirect(url_for('doctor.patients'))
    return render_template('doctor/view_patient.html', patient=patient)
    

@doctor_bp.route('/prescriptions/new', methods=['GET', 'POST'])
@role_required(allowed_roles=['doctor'])
def create_prescription():
    if request.method == 'POST':
        patient_data = {
            "nombre_completo": request.form.get('nombre_paciente'),
            "curp": request.form.get('curp_paciente').upper(),
            "sexo": request.form.get('sexo_paciente')
        }
        
        try:
            peso_str = request.form.get('peso_paciente_kg')
            altura_str = request.form.get('altura_paciente_cm')
            peso = float(peso_str) if peso_str else None
            altura = int(altura_str) if altura_str else None
        except (ValueError, TypeError):
            flash("Por favor, ingrese un valor numérico válido para peso y altura.", "danger")
            return render_template('doctor/create_prescription_form.html')

        prescription_data = {
            "id_doctor": g.profile['id'],
            "cedula_profesional": request.form.get('cedula_profesional'),
            "peso_paciente_kg": peso,
            "altura_paciente_cm": altura,
            "tratamiento": request.form.get('tratamiento'),
            "recomendaciones": request.form.get('recomendaciones')
        }
        doctor_handler = Doctor()
        
        result_data, error = doctor_handler.find_or_create_patient_and_add_prescription(
            patient_data, prescription_data
        )
        
        if error:
            flash(f"Error al generar la receta: {error}", "danger")
            return render_template('doctor/create_prescription_form.html')
        else:
            email = result_data.get('email')
            password = result_data.get('password')
            new_prescription_id = result_data.get('prescription', {}).get('id')

            success_message = f"""
            <strong>¡Receta #{new_prescription_id} generada con éxito!</strong><br>
            Puede entregarle las siguientes credenciales al paciente para que acceda al sistema:<br>
            <strong>Usuario:</strong> {email}<br>
            <strong>Contraseña:</strong> {password}
            """
            flash(Markup(success_message), "success")
            
            return redirect(url_for('doctor.view_prescription', prescription_id=new_prescription_id))
            
    return render_template('doctor/create_prescription_form.html')

@doctor_bp.route('/prescription/<int:prescription_id>')
@role_required(allowed_roles=['doctor'])
def view_prescription(prescription_id):
    doctor_handler = Doctor()
    prescription, error = doctor_handler.get_prescription_by_id(prescription_id)

    if error or not prescription:
        flash(f"No se pudo encontrar la receta con ID {prescription_id}.", "danger")
        return redirect(url_for('doctor.prescriptions'))

    return render_template('doctor/view_prescription.html', prescription=prescription)