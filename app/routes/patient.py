# app/routes/patient.py

from flask import Blueprint, render_template, g, flash
from ..decorators import role_required
from ..models.patient import Patient # Esta importación es correcta

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

    # Pasamos el historial a la plantilla
    return render_template('patient/profile.html', history=history)