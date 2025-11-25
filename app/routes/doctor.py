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

    # support searching and ordering (A→Z / Z→A)
    q = (request.args.get('q') or '').strip().lower()
    order = (request.args.get('order') or 'asc').lower()

    if not patients_list:
        patients_list = []

    if q:
        patients_list = [p for p in patients_list if q in (p.get('nombre_completo') or '').lower() or q in (p.get('email') or '').lower()]

    patients_list.sort(key=lambda p: (p.get('nombre_completo') or '').lower(), reverse=(order == 'desc'))

    return render_template('doctor/patients.html', patients=patients_list, q=(q or ''), order=order)


@doctor_bp.route('/prescriptions')
@role_required(allowed_roles=['doctor'])
def prescriptions():
    doctor_handler = Doctor()
    doctor_id = g.profile['id']
    prescriptions_list, error = doctor_handler.get_all_prescriptions(doctor_id)
    
    # support search & ordering (by patient name) via GET params `q` and `order`
    q = (request.args.get('q') or '').strip().lower()
    order = (request.args.get('order') or 'asc').lower()

    if error:
        flash(f"Error al cargar el historial de recetas: {error}", "danger")
        prescriptions_list = []
    # Defensive: ensure list
    if not prescriptions_list:
        prescriptions_list = []

    # Filter by query: look into patient name or prescription id
    if q:
        def matches(pres):
            patient_name = ((pres.get('paciente') or {}).get('nombre_completo') or '')
            pres_id = str(pres.get('id') or '')
            return q in patient_name.lower() or q in pres_id
        prescriptions_list = [p for p in prescriptions_list if matches(p)]

    # Sort alphabetically by patient name (or fallback to id)
    def sort_key(p):
        patient_name = ((p.get('paciente') or {}).get('nombre_completo') or '').lower()
        pres_id = str(p.get('id') or '')
        return (patient_name, pres_id)

    prescriptions_list.sort(key=sort_key, reverse=(order == 'desc'))

    return render_template('doctor/prescriptions.html', prescriptions=prescriptions_list, q=(q or ''), order=order)


# --- INICIO DE LA CORRECCIÓN ---
@doctor_bp.route('/inventory')
@role_required(allowed_roles=['doctor'])
def inventory():
    pharma_handler = Pharmacist()
    # Se utiliza la función correcta 'get_filtered_inventory' y se elimina la llamada a 'get_all_supplies'.
    inventory_list, inv_error = pharma_handler.get_filtered_inventory()
    
    if inv_error:
        flash("Error al cargar los datos del inventario.", "danger")
        
    # accept q and order (A→Z / Z→A)
    q = (request.args.get('q') or '').strip().lower()
    order = (request.args.get('order') or 'asc').lower()

    if not inventory_list:
        inventory_list = []

    if q:
        def matches_it(it):
            name = (it.get('nombre') or '').lower()
            cat = (it.get('categoria') or '') if isinstance(it.get('categoria'), str) else (it.get('categoria') or {}).get('nombre', '') if it.get('categoria') else ''
            return q in name or q in (cat or '').lower()
        inventory_list = [it for it in inventory_list if matches_it(it)]

    inventory_list.sort(key=lambda it: (it.get('nombre') or '').lower(), reverse=(order == 'desc'))

    return render_template('doctor/inventory.html', inventory_items=inventory_list or [], q=(q or ''), order=order)
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
            return render_template('doctor/create_patient_form.html', nombre_completo=full_name, email=email, fecha_nacimiento=birth_date, info_contacto=contact_info, curp=curp_value, sexo=sexo)
        
        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('doctor/create_patient_form.html', nombre_completo=full_name, email=email, fecha_nacimiento=birth_date, info_contacto=contact_info, curp=curp_value, sexo=sexo)
        if len(password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres.', 'danger')
            return render_template('doctor/create_patient_form.html', nombre_completo=full_name, email=email, fecha_nacimiento=birth_date, info_contacto=contact_info, curp=curp_value, sexo=sexo)

        curp = curp_value.upper()
        doctor_handler = Doctor()
        
        _, error = doctor_handler.create_patient_full(
            full_name, email, curp, birth_date, contact_info, sexo, password=password
        )
        
        if error:
            flash(f'Error al crear el paciente: {error}', 'danger')
            return render_template('doctor/create_patient_form.html', nombre_completo=full_name, email=email, fecha_nacimiento=birth_date, info_contacto=contact_info, curp=curp_value, sexo=sexo)
        else:
            flash(f'¡Paciente "{full_name}" creado con éxito!', 'success')
            return redirect(url_for('doctor.patients'))
            
    return render_template('doctor/create_patient_form.html')


@doctor_bp.route('/inventory/request', methods=['GET', 'POST'])
@role_required(allowed_roles=['doctor'])
def inventory_request():
    # simple request form - for now we just accept the request and show a message
    if request.method == 'POST':
        nombre = (request.form.get('nombre') or '').strip()
        cantidad = request.form.get('cantidad')
        comentarios = request.form.get('comentarios')

        if not nombre or not cantidad:
            flash('Nombre y cantidad son obligatorios.', 'danger')
            return render_template('doctor/request_medication.html', nombre=nombre, cantidad=cantidad, comentarios=comentarios)

        # Here you may integrate with the pharmacist model or supabase to save the request.
        # For now we keep it simple and show a success message.
        flash(f'Solicitud enviada: {nombre} × {cantidad}.', 'success')
        return redirect(url_for('doctor.inventory'))

    return render_template('doctor/request_medication.html')


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