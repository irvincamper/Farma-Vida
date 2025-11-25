# app/routes/patient.py

from flask import Blueprint, render_template, g, flash, request, redirect, url_for
from datetime import datetime
from ..extensions import supabase
from ..decorators import role_required
from ..models.patient import Patient # Esta importación es correcta
from ..models.user import User

patient_bp = Blueprint('patient', __name__)

@patient_bp.route('/profile')
@role_required(allowed_roles=['paciente'])
def profile():
    # 'g.profile' es el perfil del usuario que ha iniciado sesión
    if not g.profile:
        flash("No se pudo cargar tu perfil.", "danger")
        return render_template('patient/profile.html', history=[])

    # Creamos una instancia del especialista Paciente, pasándole su propio user_id
    patient_handler = Patient(g.profile['id']) 
    
    # Obtenemos su historial médico
    history, error = patient_handler.get_my_medical_history()
    
    if error:
        flash("No se pudo cargar su historial médico.", "danger")

    # Pasamos el historial a la plantilla (summary only)
    return render_template('patient/profile.html', history=history, promotions=None)


@patient_bp.route('/history')
@role_required(allowed_roles=['paciente'])
def history():
    if not g.profile:
        flash("No se pudo cargar tu historial.", "danger")
        return render_template('patient/history.html', history=[])
    patient_handler = Patient(g.profile['id'])
    history, error = patient_handler.get_my_medical_history()
    if error:
        flash("Error al cargar su historial médico.", "danger")
        history = []
    return render_template('patient/history.html', history=history)


@patient_bp.route('/promotions')
@role_required(allowed_roles=['paciente'])
def promotions():
    promotions_list = []
    try:
        raw_promotions = supabase.client.table('promociones').select("*").execute().data
        if raw_promotions:
            for promo in raw_promotions:
                if promo.get('fecha_inicio'):
                    promo['fecha_inicio'] = datetime.strptime(promo['fecha_inicio'], '%Y-%m-%d').date()
                if promo.get('fecha_fin'):
                    promo['fecha_fin'] = datetime.strptime(promo['fecha_fin'], '%Y-%m-%d').date()
            promotions_list = raw_promotions
    except Exception as e:
        flash(f"Error al obtener promociones: {e}", "danger")

    return render_template('patient/promotions.html', promotions=promotions_list)


@patient_bp.route('/prescription/<int:prescription_id>')
@role_required(allowed_roles=['paciente'])
def view_prescription(prescription_id):
    # In future: fetch prescription by id for this patient. For now render template.
    return render_template('patient/view_prescription.html', prescription_id=prescription_id)


@patient_bp.route('/prescriptions')
@role_required(allowed_roles=['paciente'])
def prescriptions():
    if not g.profile:
        flash("No se pudo cargar tu perfil.", "danger")
        return render_template('patient/prescriptions.html', prescriptions=[])

    # Obtener ID numérico de paciente
    try:
        patient_record = supabase.client.table('pacientes').select('id').eq('user_id', g.profile['id']).single().execute()
        if not patient_record.data:
            flash("No se encontró el registro de paciente.", "warning")
            return render_template('patient/prescriptions.html', prescriptions=[])

        patient_id = patient_record.data['id']

        # Obtener recetas del paciente
        response = supabase.client.table('recetas').select('*').eq('patient_id', patient_id).order('created_at', desc=True).execute()
        prescriptions_list = response.data if response and response.data else []
    except Exception as e:
        flash(f"Error al cargar recetas: {e}", "danger")
        prescriptions_list = []

    return render_template('patient/prescriptions.html', prescriptions=prescriptions_list)


@patient_bp.route('/profile/edit', methods=['GET', 'POST'])
@role_required(allowed_roles=['paciente'])
def edit_profile():
    if not g.profile:
        flash("No se pudo cargar tu perfil.", "danger")
        return redirect(url_for('patient.profile'))

    user = User(g.profile['id'])

    if request.method == 'POST':
        # Campos permitidos para actualizar
        nombre_completo = request.form.get('nombre_completo')
        telefono = request.form.get('telefono')
        direccion = request.form.get('direccion')
        fecha_nacimiento = request.form.get('fecha_nacimiento') or None
        avatar_url = request.form.get('avatar_url') or None

        data = {
            'nombre_completo': nombre_completo,
            'telefono': telefono,
            'direccion': direccion,
            'fecha_nacimiento': fecha_nacimiento,
            'avatar_url': avatar_url
        }

        _, error = user.update_profile(data)
        if error:
            flash(f"Error al actualizar el perfil: {error}", "danger")
            # pasar campos para re-llenar el formulario
            return render_template('patient/edit_profile.html', form=data)

        flash("Perfil actualizado correctamente.", "success")
        return redirect(url_for('patient.profile'))

    # GET -> mostrar formulario con valores actuales
    return render_template('patient/edit_profile.html', form=g.profile)