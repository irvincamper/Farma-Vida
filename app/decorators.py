from functools import wraps
from flask import g, redirect, url_for, flash

def role_required(allowed_roles: list):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.profile:
                flash("Debes iniciar sesión para ver esta página.", "warning")
                return redirect(url_for('auth.login'))
            user_role = g.profile.get('roles', {}).get('nombre')
            if user_role not in allowed_roles:
                flash(f"No tienes permiso. Se requiere el rol: {', '.join(allowed_roles)}", "danger")
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

from flask import Flask, session, g
from supabase import create_client, Client

supabase_client: Client = None

def create_app(config_object):
    app = Flask(__name__)
    app.config.from_object(config_object)
    
    global supabase_client
    supabase_client = create_client(app.config['SUPABASE_URL'], app.config['SUPABASE_KEY'])
    
    from .routes.auth import auth_bp
    from .routes.doctor import doctor_bp
    from .routes.patient import patient_bp
    from .routes.admin import admin_bp
    from .routes.pharmacist import pharmacist_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(doctor_bp, url_prefix='/doctor')
    app.register_blueprint(patient_bp, url_prefix='/patient')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(pharmacist_bp, url_prefix='/pharmacist')
    
    @app.before_request
    def load_user_profile():
        g.profile = None
        user_info = session.get('user')
        if user_info and 'id' in user_info:
            user_id = user_info['id']
            try:
                response = supabase_client.table('perfiles').select('*, roles(nombre)').eq('id', user_id).maybe_single().execute()
                if response and response.data:
                    g.profile = response.data
            except Exception as e:
                print(f"Error al cargar perfil: {e}")
                g.profile = None
    
    return app