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
    
    # Obtenemos su historial médico (raw) y normalizamos un pequeño resumen para la vista
    history_raw, error = patient_handler.get_my_medical_history()

    history_summary = []
    if history_raw:
        for rec in history_raw:
            fecha = rec.get('fecha_consulta') or rec.get('created_at') or rec.get('fecha')
            resumen = rec.get('tratamiento') or rec.get('resumen') or rec.get('nota') or ''
            doctor = None
            if rec.get('doctor') and isinstance(rec.get('doctor'), dict):
                doctor = rec['doctor'].get('nombre_completo')
            elif rec.get('doctor_nombre'):
                doctor = rec.get('doctor_nombre')

            pres_id = None
            if rec.get('recetas'):
                if isinstance(rec['recetas'], list) and len(rec['recetas'])>0:
                    pres_id = rec['recetas'][0].get('id') or rec['recetas'][0].get('prescription_id')
                elif isinstance(rec['recetas'], dict):
                    pres_id = rec['recetas'].get('id') or rec['recetas'].get('prescription_id')

            history_summary.append({
                'fecha': fecha,
                'resumen': resumen,
                'doctor_nombre': doctor,
                'prescripcion_id': pres_id
            })

    if error:
        flash("No se pudo cargar su historial médico.", "danger")

    # Obtener un par de promociones para mostrar en el perfil (si las hay)
    promotions_list = []
    try:
        # Some test fakes may not implement `.limit()`; call it only if available.
        q = supabase.client.table('promociones').select('*').order('fecha_inicio', desc=True)
        if hasattr(q, 'limit'):
            q = q.limit(3)
        resp_pr = q.execute()
        raw_promotions = resp_pr.data if resp_pr and resp_pr.data else []
        for promo in raw_promotions:
            if promo.get('fecha_inicio'):
                try:
                    promo['fecha_inicio'] = datetime.strptime(promo['fecha_inicio'], '%Y-%m-%d').date()
                except Exception:
                    pass
            if promo.get('fecha_fin'):
                try:
                    promo['fecha_fin'] = datetime.strptime(promo['fecha_fin'], '%Y-%m-%d').date()
                except Exception:
                    pass
        promotions_list = raw_promotions
    except Exception as e:
        # No queremos romper la vista, solo loguear/flashear
        flash(f"Error al obtener promociones: {e}", "warning")

    # Pasamos al template el resumen de historial y un pequeño conjunto de promociones
    return render_template('patient/profile.html', history=history_summary, promotions=promotions_list)


@patient_bp.route('/history')
@role_required(allowed_roles=['paciente'])
def history():
    if not g.profile:
        flash("No se pudo cargar tu historial.", "danger")
        return render_template('patient/history.html', history=[])
    patient_handler = Patient(g.profile['id'])
    history_raw, error = patient_handler.get_my_medical_history()
    history = []
    # Normalize records for the template
    if history_raw:
        for rec in history_raw:
            # fecha: prefer 'fecha_consulta', then created_at
            fecha = rec.get('fecha_consulta') or rec.get('created_at') or rec.get('fecha')
            # resumen: tratamiento or resumen or nota
            resumen = rec.get('tratamiento') or rec.get('resumen') or rec.get('nota') or ''
            # doctor name
            doctor = None
            if rec.get('doctor') and isinstance(rec.get('doctor'), dict):
                doctor = rec['doctor'].get('nombre_completo')
            elif rec.get('doctor_nombre'):
                doctor = rec.get('doctor_nombre')
            elif rec.get('doctor_nombre_completo'):
                doctor = rec.get('doctor_nombre_completo')

            # get prescription id if nested
            pres_id = None
            # recetas may be a list or dict
            if rec.get('recetas'):
                if isinstance(rec['recetas'], list) and len(rec['recetas'])>0:
                    pres_id = rec['recetas'][0].get('id') or rec['recetas'][0].get('prescription_id')
                elif isinstance(rec['recetas'], dict):
                    pres_id = rec['recetas'].get('id') or rec['recetas'].get('prescription_id')

            history.append({
                'fecha': fecha,
                'resumen': resumen,
                'doctor_nombre': doctor,
                'prescripcion_id': pres_id
            })
    if error:
        flash("Error al cargar su historial médico.", "danger")
        history = []
    return render_template('patient/history.html', history=history)


@patient_bp.route('/promotions')
@role_required(allowed_roles=['paciente'])
def promotions():
    promotions_list = []
    try:
        resp_pr = supabase.client.table('promociones').select("*").execute()
        raw_promotions = resp_pr.data if resp_pr and resp_pr.data else []
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
    # Fetch prescription by id (ensure it belongs to logged-in patient)
    prescription = None
    try:
        # Try to read prescription with nested doctor and medicamento info
        resp = supabase.client.table('recetas').select('*, doctor:perfiles(nombre_completo), medicamento:inventario(nombre)').eq('id', prescription_id).maybe_single().execute()
        if resp and resp.data:
            prescription = resp.data
        else:
            flash('Receta no encontrada.', 'warning')
            return render_template('patient/view_prescription.html', prescription_id=prescription_id)
    except Exception as e:
        flash(f'Error al obtener receta: {e}', 'danger')
        return render_template('patient/view_prescription.html', prescription_id=prescription_id)

    # Security: ensure the prescription belongs to the logged-in patient
    try:
        pat_rec = supabase.client.table('pacientes').select('id').eq('user_id', g.profile['id']).maybe_single().execute()
        pat_id = pat_rec.data['id'] if pat_rec and pat_rec.data else None
        # possible keys in prescription: patient_id or id_paciente
        pres_owner = prescription.get('patient_id') or prescription.get('id_paciente')
        if pat_id and pres_owner and str(pres_owner) != str(pat_id):
            flash('No tienes permiso para ver esta receta.', 'danger')
            return redirect(url_for('patient.profile'))
    except Exception:
        # if any problem checking ownership, continue but don't crash
        pass

    return render_template('patient/view_prescription.html', prescription=prescription)


@patient_bp.route('/prescriptions')
@role_required(allowed_roles=['paciente'])
def prescriptions():
    if not g.profile:
        flash("No se pudo cargar tu perfil.", "danger")
        return render_template('patient/prescriptions.html', prescriptions=[])

    # Obtener ID numérico de paciente
    try:
        patient_record = supabase.client.table('pacientes').select('id').eq('user_id', g.profile['id']).maybe_single().execute()
        if not patient_record or not patient_record.data:
            flash("No se encontró el registro de paciente.", "warning")
            return render_template('patient/prescriptions.html', prescriptions=[])

        patient_id = patient_record.data['id']

        # Obtener recetas del paciente (incluimos información del doctor si está relacionada)
        response = supabase.client.table('recetas').select('*, doctor:perfiles(nombre_completo)').eq('patient_id', patient_id).order('created_at', desc=True).execute()
        raw_list = response.data if response and response.data else []
        prescriptions_list = []
        for r in raw_list:
            pres_id = r.get('id') or r.get('prescription_id')
            created = r.get('created_at') or r.get('fecha') or r.get('fecha_emision')
            # doctor may be nested as dict { nombre_completo: ... }
            doctor_name = None
            if r.get('doctor') and isinstance(r.get('doctor'), dict):
                doctor_name = r['doctor'].get('nombre_completo')
            elif r.get('doctor_nombre'):
                doctor_name = r.get('doctor_nombre')

            # medicamentos may be nested: recetas table may store medicamento references
            meds = []
            if r.get('medicamento'):
                if isinstance(r['medicamento'], list):
                    for m in r['medicamento']:
                        if isinstance(m, dict):
                            meds.append(m.get('nombre') or str(m))
                        else:
                            meds.append(str(m))
                elif isinstance(r['medicamento'], dict):
                    meds.append(r['medicamento'].get('nombre') or str(r['medicamento']))
                else:
                    meds.append(str(r['medicamento']))

            prescriptions_list.append({
                'id': pres_id,
                'created_at': created,
                'doctor_nombre': doctor_name,
                'medicamentos': meds
            })
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