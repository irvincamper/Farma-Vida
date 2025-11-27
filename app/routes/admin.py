from flask import Blueprint, render_template, g, flash, request, redirect, url_for, jsonify
import csv
from io import StringIO
from flask import Response
from datetime import datetime
import re
from typing import Optional

from ..decorators import role_required
from ..extensions import supabase
from ..models.admin import Admin
from ..models.pharmacist import Pharmacist
from ..models.user import User
from ..models.provider import Provider
from ..models.promoción import Promotion

# Importamos la función LLM mejorada que acepta el contexto de la base de datos
from ..llm_client import call_llm

admin_bp = Blueprint('admin', __name__)

# --- Mapeo de Roles a IDs (CORREGIDO PARA COINCIDIR CON TUS DATOS REALES) ---
ROLE_MAP = {
    'administrador': 1, 
    'admin': 1,
    'doctor': 2,
    'paciente': 3,       # Pacientes tienen el ID 3
    'farmaceutico': 4,   # Farmacéuticos tienen el ID 4
}
# ----------------------------------------------------------------------
# FUNCIONES AUXILIARES DE BASE DE DATOS PARA EL LLM (RAG)
# ----------------------------------------------------------------------

def get_db_stats_context(prompt: str) -> tuple[Optional[str], str]:
    """
    Analiza el prompt del usuario y extrae los datos de la DB si es necesario (lógica RAG mejorada).
    
    Returns: (db_context: str | None, processed_prompt: str)
    """
    
    prompt_lower = prompt.lower().strip()
    db_context = None
    processed_prompt = prompt 
    
    try:
        # --- PATRONES DE CONTEO DE PACIENTES/USUARIOS/ROLES ---
        if re.search(r'cuant(o|a)s\s+(pacientes|usuarios|personas\s+registradas|farmaceuticos|doctores|administradores)\s+hay|total\s+de\s+(pacientes|usuarios|roles)', prompt_lower):
            
            # 1. Obtener conteo de usuarios/pacientes y roles específicos
            total_users_res = supabase.client.table('perfiles').select('*', count='exact').execute()
            total_users = total_users_res.count or 0
            
            # Conteo de roles individuales usando el ROLE_MAP corregido
            pacientes_count_res = supabase.client.table('perfiles').select('*', count='exact').eq('id_de_rol', ROLE_MAP['paciente']).execute()
            pacientes_count = pacientes_count_res.count or 0
            
            doctores_count_res = supabase.client.table('perfiles').select('*', count='exact').eq('id_de_rol', ROLE_MAP['doctor']).execute()
            doctores_count = doctores_count_res.count or 0
            
            farmaceuticos_count_res = supabase.client.table('perfiles').select('*', count='exact').eq('id_de_rol', ROLE_MAP['farmaceutico']).execute()
            farmaceuticos_count = farmaceuticos_count_res.count or 0
            
            # Conteo de Administradores
            admin_count_res = supabase.client.table('perfiles').select('*', count='exact').eq('id_de_rol', ROLE_MAP['administrador']).execute()
            admin_count = admin_count_res.count or 0
            
            # Cálculo de la suma de roles
            sum_of_roles = pacientes_count + doctores_count + farmaceuticos_count + admin_count

            # 2. Construir el contexto para el LLM (Claro y explícito)
            db_context = (
                f"La ÚNICA FUENTE DE DATOS es la siguiente: "
                f"El número TOTAL de usuarios registrados en el sistema es **{total_users}**. "
                f"El conteo DETALLADO por roles es: **Administradores={admin_count}**, **Pacientes={pacientes_count}**, "
                f"**Doctores={doctores_count}**, **Farmacéuticos={farmaceuticos_count}**. "
                f"La suma de todos los roles es {sum_of_roles}. Los datos son exactos."
            )
            # 3. Instrucción CLARA y ASESIVA para que el LLM use el dato
            processed_prompt = "URGENTE: Responde la pregunta del usuario sobre el conteo de usuarios y roles usando EXCLUSIVAMENTE los DATOS EXACTOS que se te proporcionaron en el contexto de la base de datos."
            
        # --- PATRONES DE CONTEO DE INVENTARIO/STOCK TOTAL ---
        elif re.search(r'(stock|unidades)\s+total|suma\s+de\s+productos|cuantas\s+unidades\s+hay\s+en\s+total|inventario\s+actual|cuantos\s+medicamentos', prompt_lower):
            
            # 1. Obtener conteo de inventario y el total de stock
            meds_count_res = supabase.client.table('inventario').select('*', count='exact').execute()
            total_stock_res = supabase.client.rpc('get_total_stock').execute() 
            
            meds_count = meds_count_res.count or 0
            total_stock = int(total_stock_res.data[0]['total_stock']) if total_stock_res and total_stock_res.data and total_stock_res.data[0].get('total_stock') is not None else 0
            
            # 2. Construir el contexto para el LLM
            db_context = (
                f"El total de productos/medicamentos diferentes en el inventario es {meds_count}. "
                f"El stock total combinado de todas las unidades es {total_stock}."
            )
            # 3. Instrucción CLARA y ASESIVA para que el LLM use el dato
            processed_prompt = "URGENTE: Usa EXCLUSIVAMENTE el CONTEXTO DE LA BASE DE DATOS proporcionado para responder la pregunta del usuario sobre el inventario actual y el stock total combinado."

        # --- RECHAZO DE BÚSQUEDA ESPECÍFICA ---
        elif re.search(r'informacion\s+de\s+(irvin|carlos\s+perez|persona)', prompt_lower):
            db_context = "El LLM no está configurado para buscar información detallada de usuarios individuales por seguridad. Solo puede dar estadísticas generales."
            processed_prompt = "El usuario está pidiendo información detallada de una persona, explica amablemente por qué no puedes proporcionar ese dato por seguridad en el sistema Cuida Mas."
        
        else:
            processed_prompt = prompt

    except Exception as e:
        # Manejo de error de DB: Se informa al LLM que no hay datos disponibles
        print(f"Error en RAG al consultar DB: {e}")
        db_context = None 
        processed_prompt = "El usuario ha preguntado por estadísticas. Se ha producido un error al intentar acceder a los datos de la base de datos de Cuida Mas. La respuesta debe ser informar al usuario que el sistema no puede acceder a los datos de la base de datos en este momento y que intente más tarde."
        
    return db_context, processed_prompt

# ----------------------------------------------------------------------
# RUTAS DE ADMINISTRADOR (El resto del código permanece igual)
# ----------------------------------------------------------------------

@admin_bp.route('/dashboard')
@role_required(allowed_roles=['administrador'])
def dashboard():
    try:
        user_count_res = supabase.client.table('perfiles').select('id', count='exact').execute()
        doctor_count_res = supabase.client.table('perfiles').select('id', count='exact').eq('id_de_rol', ROLE_MAP['doctor']).execute()
        meds_count_res = supabase.client.table('inventario').select('id', count='exact').execute()
        stats = {
            'total_users': user_count_res.count or 0,
            'total_doctors': doctor_count_res.count or 0,
            'total_meds': meds_count_res.count or 0
        }
    except Exception as e:
        flash("Error al obtener las estadísticas del sistema.", "danger")
        stats = {'total_users': 'N/A', 'total_doctors': 'N/A', 'total_meds': 'N/A'}
    return render_template('admin/dashboard.html', stats=stats)

@admin_bp.route('/users')
@role_required(allowed_roles=['administrador'])
def manage_users():
    admin_handler = Admin()
    users_list, error = admin_handler.get_all_users_with_roles()
    if error:
        flash("Error al cargar la lista de usuarios.", "danger")
    q = (request.args.get('q') or '').strip().lower()
    order = (request.args.get('order') or 'asc').lower()

    role_priority = {
        'administrador': 1,
        'doctor': 2,
        'farmaceutico': 3,
        'paciente': 4
    }

    if not users_list:
        users_list = []

    if q:
        def matches_query(u):
            name = (u.get('nombre_completo') or '').lower()
            email = (u.get('email') or '').lower()
            return q in name or q in email
        users_list = [u for u in users_list if matches_query(u)]

    def sort_key(u):
        role_name = ''
        try:
            role_name = (u.get('roles') or {}).get('nombre', '') or ''
        except Exception:
            role_name = ''
        pr = role_priority.get(role_name.lower(), 99)
        name = (u.get('nombre_completo') or '').lower()
        return (pr, name)

    users_list.sort(key=sort_key, reverse=(order == 'desc'))

    return render_template('admin/manage_users.html', users=users_list, q=(q or ''), order=order)

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@role_required(allowed_roles=['administrador'])
def create_user():
    if request.method == 'POST':
        full_name = request.form.get('nombre_completo')
        email = request.form.get('email')
        role_id = request.form.get('id_de_rol')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Las contraseñas no coinciden. Por favor, inténtelo de nuevo.', 'danger')
            return render_template('admin/create_user_form.html', nombre_completo=full_name, email=email, id_de_rol=role_id)
        
        if len(password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres.', 'danger')
            return render_template('admin/create_user_form.html', nombre_completo=full_name, email=email, id_de_rol=role_id)

        admin_handler = Admin()
        _, error = admin_handler.create_any_user(full_name, email, role_id, password)
        
        if error:
            flash(f'Error al crear usuario: {error}', 'danger')
            return render_template('admin/create_user_form.html', nombre_completo=full_name, email=email, id_de_rol=role_id)
        else:
            flash(f'Usuario "{full_name}" creado con éxito.', 'success')
            return redirect(url_for('admin.manage_users'))
            
    return render_template('admin/create_user_form.html')

@admin_bp.route('/users/edit/<user_id>', methods=['GET', 'POST'])
@role_required(allowed_roles=['administrador'])
def edit_user(user_id):
    admin_handler = Admin()
    if request.method == 'POST':
        full_name = request.form.get('nombre_completo')
        role_id = request.form.get('id_de_rol')
        _, error = admin_handler.update_any_user(user_id, full_name, role_id)
        if error: 
            flash(f"Error al actualizar usuario: {error}", 'danger')
        else: 
            flash("Usuario actualizado con éxito.", "success")
        return redirect(url_for('admin.manage_users'))
    user_data, error = admin_handler.get_user_by_id(user_id)
    if error or not user_data:
        flash("Usuario no encontrado.", "danger")
        return redirect(url_for('admin.manage_users'))
    return render_template('admin/edit_user_form.html', user=user_data)

@admin_bp.route('/users/delete/<user_id>', methods=['POST'])
@role_required(allowed_roles=['administrador'])
def delete_user(user_id):
    if user_id == g.profile['id']:
        flash('No puedes eliminar tu propia cuenta de administrador.', 'danger')
        return redirect(url_for('admin.manage_users'))

    admin_handler = Admin()
    success, error = admin_handler.delete_user_by_id(user_id)

    if success:
        flash('Usuario eliminado con éxito.', 'success')
    else:
        flash(f'Error al eliminar el usuario: {error}', 'danger')
    
    return redirect(url_for('admin.manage_users'))

@admin_bp.route('/inventory')
@role_required(allowed_roles=['administrador'])
def inventory():
    pharma_handler = Pharmacist()
    provider_handler = Provider()
    
    inventory_list, inv_error = pharma_handler.get_filtered_inventory()
    categories, cat_error = pharma_handler.get_all_categories()
    providers_list, prov_error = provider_handler.get_all()
    
    if inv_error or cat_error or prov_error:
        flash("Error al cargar datos del inventario.", "danger")
        
    q = (request.args.get('q') or '').strip().lower()
    order = (request.args.get('order') or 'asc').lower()

    if not inventory_list:
        inventory_list = []

    if q:
        def matches_inv(it):
            name = (it.get('nombre') or '').lower()
            cat = (it.get('categoria') or {}).get('nombre', '') if it.get('categoria') else ''
            prov = (it.get('proveedor') or {}).get('nombre', '') if it.get('proveedor') else ''
            return q in name or q in (cat or '').lower() or q in (prov or '').lower()
        inventory_list = [it for it in inventory_list if matches_inv(it)]

    inventory_list.sort(key=lambda it: (it.get('nombre') or '').lower(), reverse=(order == 'desc'))

    return render_template('admin/inventory.html', 
                            inventory_items=inventory_list or [],
                            categories=categories or [],
                            providers=providers_list or [],
                            q=(q or ''), order=order)

@admin_bp.route('/inventory/add', methods=['POST'])
@role_required(allowed_roles=['administrador', 'farmaceutico'])
def add_inventory_item():
    data = request.get_json()
    pharma_handler = Pharmacist()
    _, error = pharma_handler.add_inventory_item(data.get('name'), data.get('stock'), data.get('category_id'))
    
    if error: 
        return jsonify({'success': False, 'message': str(error)}), 400
    return jsonify({'success': True, 'message': 'Item añadido al inventario con éxito.'})

@admin_bp.route('/inventory/restock', methods=['POST'])
@role_required(allowed_roles=['administrador', 'farmaceutico'])
def restock_inventory():
    data = request.get_json()
    med_id = data.get('id')
    quantity = data.get('quantity')
    pharma_handler = Pharmacist()
    _, error = pharma_handler.restock_medicine(med_id, quantity)
    if error:
        return jsonify({'success': False, 'message': str(error)}), 400
    return jsonify({'success': True, 'message': 'Stock actualizado con éxito.'})

@admin_bp.route('/inventory/export')
@role_required(allowed_roles=['administrador'])
def export_inventory():
    pharma_handler = Pharmacist()
    inventory_list, error = pharma_handler.get_filtered_inventory()
    if error or not inventory_list:
        flash("No se pudo exportar el inventario.", "danger")
        return redirect(url_for('admin.inventory'))
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Producto', 'Stock', 'Categoría'])
    for item in inventory_list:
        category_name = item.get('categoria', {}).get('nombre') if item.get('categoria') else 'Sin categoría'
        writer.writerow([item.get('id'), item.get('nombre'), item.get('stock'), category_name])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=inventario.csv"}
    )

@admin_bp.route('/reports')
@role_required(allowed_roles=['administrador'])
def reports():
    return render_template('admin/reports.html')

@admin_bp.route('/promotions')
@role_required(allowed_roles=['administrador'])
def promotions():
    promotions_list = []
    q = (request.args.get('q') or '').strip().lower()
    order = (request.args.get('order') or 'asc').lower()

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
        
    if q:
        promotions_list = [p for p in promotions_list if q in (p.get('titulo','') or '').lower() or q in (p.get('descripcion','') or '').lower()]

    promotions_list.sort(key=lambda p: (p.get('titulo') or '').lower(), reverse=(order == 'desc'))

    return render_template('admin/promotions.html', promotions=promotions_list, now=datetime.utcnow(), q=(q or ''), order=order)
    
@admin_bp.route('/promotions/add', methods=['POST'])
@role_required(allowed_roles=['administrador'])
def add_promotion():
    try:
        name = request.form.get('titulo')
        description = request.form.get('descripcion')
        start_date = request.form.get('fecha_inicio')
        end_date = request.form.get('fecha_fin')
        
        supabase.client.table('promociones').insert({
            "titulo": name,
            "descripcion": description,
            "fecha_inicio": start_date,
            "fecha_fin": end_date
        }).execute()

        flash("Promoción creada con éxito", "success")
    except Exception as e:
        flash(f"Error al crear la promoción: {str(e)}", "danger")

    return redirect(url_for('admin.promotions'))

@admin_bp.route('/promotions/finalize/<int:promo_id>', methods=['POST'])
@role_required(allowed_roles=['administrador'])
def finalize_promotion(promo_id):
    promo_handler = Promotion()
    _, error = promo_handler.finalize(promo_id)
    if error:
        flash(f"Error al intentar finalizar la promoción: {error}", "danger")
    else:
        flash("La promoción ha sido finalizada correctamente.", "success")
    return redirect(url_for('admin.promotions'))


@admin_bp.route('/promotions/edit/<int:promo_id>', methods=['GET', 'POST'])
@role_required(allowed_roles=['administrador'])
def edit_promotion(promo_id):
    promo_handler = Promotion()
    if request.method == 'POST':
        _, error = promo_handler.update(
            promo_id,
            request.form.get('titulo'),
            request.form.get('descripcion'),
            request.form.get('fecha_inicio') or None,
            request.form.get('fecha_fin') or None
        )
        if error:
            flash(f"Error al actualizar la promoción: {error}", "danger")
        else:
            flash("Promoción actualizada con éxito.", "success")
        return redirect(url_for('admin.promotions'))

    promo, error = promo_handler.get_by_id(promo_id)
    if error or not promo:
        flash("Promoción no encontrada o error al cargarla.", "danger")
        return redirect(url_for('admin.promotions'))
    
    return render_template('admin/edit_promotion.html', promo=promo)

@admin_bp.route('/settings')
@role_required(allowed_roles=['administrador'])
def settings():
    return render_template('admin/settings.html')


@admin_bp.route('/assistant')
@role_required(allowed_roles=['administrador'])
def assistant():
    """Admin LLM assistant UI page. Se pasa el nombre del usuario para personalizar."""
    # OBTENEMOS EL NOMBRE DEL USUARIO DE g.profile (asumiendo que g se carga correctamente)
    user_name = g.profile.get('nombre_completo', 'Administrador') 
    return render_template('admin/assistant.html', user_name=user_name) 

@admin_bp.route('/assistant/api', methods=['POST'])
@role_required(allowed_roles=['administrador'])
def assistant_api():
    """Ruta API para el asistente LLM."""
    data = request.get_json() or {}
    user_prompt = data.get('message') or ''
    
    if not user_prompt:
        return jsonify({'ok': False, 'response': 'No message provided.'}), 400

    try:
        # 1. Ejecutar la lógica de Agente/RAG: Obtener contexto de la DB si aplica
        db_context, prompt_to_llm = get_db_stats_context(user_prompt)

        # 2. Llamar al LLM (ahora con el contexto de la DB)
        result = call_llm(user_prompt=prompt_to_llm, db_context=db_context)
        
        status_code = 200 if result.get('ok') else 503
        return jsonify(result), status_code

    except Exception as e:
        # 🚨 CORRECCIÓN IMPLEMENTADA: Captura de errores y devolución de JSON válido
        print(f"ERROR FATAL en assistant_api: {e}")
        return jsonify({
            'ok': False, 
            'response': 'Disculpa, ocurrió un error interno en el sistema al intentar procesar tu solicitud. Por favor, revisa la configuración de la base de datos (Supabase) y el cliente LLM.'
        }), 500

@admin_bp.route('/settings/update-profile', methods=['POST'])
@role_required(allowed_roles=['administrador'])
def update_settings_profile():
    new_name = request.form.get('nombre_completo')
    user_handler = User(g.profile['id'])
    _, error = user_handler.update_profile_name(new_name)
    if error:
        flash(f"Error al actualizar nombre: {error}", "danger")
    else:
        flash("Nombre de perfil actualizado.", "success")
    return redirect(url_for('admin.settings'))

@admin_bp.route('/maintenance/backup')
@role_required(allowed_roles=['administrador'])
def create_backup():
    flash("Iniciando proceso de respaldo (simulación)... ¡Respaldo completado!", "info")
    return redirect(url_for('admin.settings'))

@admin_bp.route('/maintenance/update')
@role_required(allowed_roles=['administrador'])
def check_for_updates():
    flash("Buscando actualizaciones... ¡Su sistema ya está en la última versión!", "success")
    return redirect(url_for('admin.settings'))

@admin_bp.route('/providers/new', methods=['GET', 'POST'])
@role_required(allowed_roles=['administrador'])
def create_provider():
    if request.method == 'POST':
        handler = Provider()
        _, error = handler.create(
            request.form.get('nombre'),
            request.form.get('telefono'),
            request.form.get('email'),
            request.form.get('direccion')
        )
        if error: 
            flash(f"Error al crear proveedor: {error}", "danger")
        else: 
            flash("Proveedor creado con éxito.", "success")
        return redirect(url_for('admin.inventory'))
        
    return render_template('admin/create_provider_form.html')