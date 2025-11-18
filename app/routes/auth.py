# app/routes/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from ..extensions import supabase

# ESTA LÍNEA ES LA QUE PROBABLEMENTE FALTA O ESTÁ ROTA.
# Aquí creamos el objeto Blueprint y lo asignamos a la variable 'auth_bp'.
auth_bp = Blueprint('auth', __name__)

# Diccionario para mapear roles a sus rutas de dashboard.
ROLE_DASHBOARDS = {
    'administrador': 'admin.dashboard',
    'doctor': 'doctor.dashboard',
    'paciente': 'patient.profile',
    'farmaceutico': 'pharmacist.dashboard'  # <-- Cambiado aquí
}

@auth_bp.route('/')
def index():
    """Ruta raíz. Redirige al login o al dashboard si ya hay sesión."""
    if g.profile:
        role = g.profile.get('roles', {}).get('nombre')
        if role in ROLE_DASHBOARDS:
            return redirect(url_for(ROLE_DASHBOARDS[role]))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Gestiona el inicio de sesión del usuario."""
    if g.profile:
        role = g.profile.get('roles', {}).get('nombre')
        if role in ROLE_DASHBOARDS:
            return redirect(url_for(ROLE_DASHBOARDS[role]))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            auth_response = supabase.client.auth.sign_in_with_password({"email": email, "password": password})
            session['user'] = auth_response.user.dict()
            flash('Inicio de sesión exitoso.', 'success')

            profile_data = supabase.client.table('perfiles').select('*, roles(nombre)').eq('id', auth_response.user.id).single().execute().data
            
            if not profile_data or not profile_data.get('roles') or not profile_data.get('roles').get('nombre'):
                flash('Perfil o rol no encontrado. Contacte al administrador.', 'danger')
                return redirect(url_for('auth.logout'))

            role = profile_data.get('roles').get('nombre')
            endpoint = ROLE_DASHBOARDS.get(role)
            
            if endpoint:
                return redirect(url_for(endpoint))
            else:
                flash('Rol de usuario no reconocido.', 'warning')
                return redirect(url_for('auth.login'))
                
        except Exception as e:
            print(f"Error detallado en login: {e}")
            flash('Error al iniciar sesión. Verifique sus credenciales.', 'danger')
            return redirect(url_for('auth.login'))
            
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """Cierra la sesión del usuario."""
    session.pop('user', None)
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('auth.login'))