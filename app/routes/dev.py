from flask import Blueprint, session, redirect, url_for, current_app

dev_bp = Blueprint('dev', __name__)


@dev_bp.route('/dev/login_demo')
def login_demo():
    """Setea en sesión un usuario demo (paciente) y un perfil de ejemplo para desarrollo.
    No modifica la base de datos; útil para probar la UI localmente.
    """
    # Demo profile (puedes adaptarlo)
    demo_profile = {
        'id': 'demo-patient',
        'nombre_completo': 'Paciente Demo',
        'email': 'demo@local',
        'roles': {'nombre': 'paciente'}
    }
    session['user'] = {'id': demo_profile['id']}
    session['profile_data'] = demo_profile
    return redirect(url_for('patient.profile'))


@dev_bp.route('/dev/clear_demo')
def clear_demo():
    session.pop('user', None)
    session.pop('profile_data', None)
    return redirect(url_for('auth.login'))
