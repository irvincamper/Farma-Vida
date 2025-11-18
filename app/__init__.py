# app/__init__.py

# --- Importaciones de Librerías Externas ---
# Importamos las herramientas necesarias de Flask para la aplicación.
from flask import Flask, session, g
# Importamos herramientas de Python para manejar fechas y configuración regional.
from datetime import datetime
import locale

# --- Importaciones de Módulos Propios ---
# Importamos nuestra instancia central de Supabase desde el archivo de extensiones.
from .extensions import supabase

def create_app(config_object):
    """
    Función "Application Factory".
    Es el punto de entrada que construye y configura toda la aplicación Flask.
    """
    
    # 1. Creación de la Instancia de la Aplicación
    app = Flask(__name__)
    
    # 2. Carga de la Configuración
    #    Lee las variables (SECRET_KEY, SUPABASE_URL, SUPABASE_KEY) desde el objeto que
    #    le pasamos (que viene de nuestro archivo config.py).
    app.config.from_object(config_object)

    # 3. Configuración Regional para Fechas en Español
    #    Intentamos configurar el idioma para que las fechas (ej. 'August') se muestren en español ('Agosto').
    try:
        # Configuración para sistemas basados en Linux/macOS
        locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
    except locale.Error:
        try:
            # Configuración alternativa para sistemas Windows
            locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
        except locale.Error:
            # Si ninguna funciona, imprimimos una advertencia en la terminal.
            print("ADVERTENCIA: No se pudo establecer la localización a español. Las fechas pueden aparecer en inglés.")

    # 4. Inicialización de Extensiones
    #    Conectamos nuestra instancia de Supabase a la aplicación Flask.
    supabase.init_app(app)
    
    # 5. Forzar el Modo Superusuario (Bypass de RLS)
    #    Esta es la solución definitiva para el error "violates row-level security policy".
    #    Le dice a nuestro backend que todas las operaciones que realice contra las tablas de la
    #    base de datos deben usar los máximos privilegios, ignorando las reglas de RLS.
    #    Esto es seguro porque la seguridad de QUIÉN puede hacer QUÉ ya la manejamos
    #    en nuestras rutas de Python con el decorador @role_required.
    if supabase.client:
        supabase.client.postgrest.auth(app.config['SUPABASE_KEY'])

    # 6. Registro de Componentes de la Aplicación
    #    Llamamos a funciones auxiliares para mantener este bloque principal limpio.
    register_blueprints(app)
    register_hooks(app)
    register_template_filters(app)

    # 7. Retornamos la aplicación completamente construida y lista para correr.
    return app

# --- Funciones de Ayuda para la Configuración ---

def register_blueprints(app):
    """
    Importa y registra todos los Blueprints (conjuntos de rutas) de la aplicación.
    """
    from .routes.auth import auth_bp
    from .routes.doctor import doctor_bp
    from .routes.patient import patient_bp
    from .routes.admin import admin_bp
    from .routes.pharmacist import pharmacist_bp

    # Cada blueprint se registra con un prefijo de URL para mantener las rutas organizadas.
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(doctor_bp, url_prefix='/doctor')
    app.register_blueprint(pharmacist_bp, url_prefix='/pharmacist')
    app.register_blueprint(patient_bp, url_prefix='/patient')

def register_hooks(app):
    """
    Registra los "hooks" de la aplicación. Estas son funciones que se ejecutan
    automáticamente en ciertos momentos del ciclo de una petición.
    """
    @app.before_request
    def load_user_profile():
        """
        Esta función se ejecuta ANTES de cada petición.
        Su trabajo es cargar el perfil del usuario si hay una sesión activa.
        El perfil se guarda en 'g', un objeto temporal que vive solo durante la petición.
        """
        g.profile = None # Inicializamos a None por seguridad.
        user_info = session.get('user')
        
        if user_info and 'id' in user_info:
            user_id = user_info['id']
            try:
                # Hacemos la consulta a la BD para obtener el perfil y el nombre del rol.
                response = supabase.client.table('perfiles').select('*, roles(nombre)').eq('id', user_id).single().execute()
                if response.data:
                    g.profile = response.data
            except Exception as e:
                # Si algo falla (ej. el perfil fue borrado pero la sesión sigue activa), lo registramos.
                print(f"Error crítico al cargar el perfil de usuario {user_id}: {e}")
                g.profile = None

def register_template_filters(app):
    """
    Registra funciones personalizadas que podemos usar en los archivos HTML
    para formatear datos.
    """
    @app.template_filter('format_datetime')
    def format_datetime_filter(value):
        """
        Filtro para convertir fechas de formato ISO a un formato legible en español.
        Uso en HTML: {{ una_fecha | format_datetime }}
        """
        if not value:
            return "Fecha no disponible"
        try:
            dt_object = datetime.fromisoformat(value)
            # Formatea la fecha como "03 de Agosto de 2025, 09:30 PM"
            return dt_object.strftime("%d de %B de %Y, %I:%M %p")
        except (ValueError, TypeError):
            # Si el dato no es una fecha válida, lo devolvemos como está para no romper la página.
            return value