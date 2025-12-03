# app/routes/pharmacist.py

from flask import Blueprint, render_template, g, flash, request, redirect, url_for 
import json # <-- ¡Añadida para manejar JSON si es necesario!
from ..decorators import role_required
from ..models.pharmacist import Pharmacist 
from ..models.doctor import Doctor # Mantengo esta importación por si se usa en otro lado

pharmacist_bp = Blueprint('pharmacist', __name__)

# --- RUTA DASHBOARD ---
@pharmacist_bp.route('/dashboard')
@role_required(allowed_roles=['farmaceutico', 'administrador'])
def dashboard():
    pharma_handler = Pharmacist()
    stats, error = pharma_handler.get_dashboard_stats()

    if error:
        flash("No se pudieron cargar las estadísticas del panel.", "danger")
        stats = {
            'medicines_count': 'N/A',
            'supplies_count': 'N/A',
            'low_stock_count': 'N/A'
        }
    
    return render_template('pharmacist/dashboard.html', stats=stats)


# --- RUTA INVENTORY ---
@pharmacist_bp.route('/inventory')
@role_required(allowed_roles=['farmaceutico', 'administrador'])
def inventory():
    user_name = g.profile['nombre_completo'] if g.profile else "Farmacéutico"
    pharma_handler = Pharmacist()
    
    q = (request.args.get('q') or '').strip()
    order = (request.args.get('order') or 'asc').lower()
    
    inventory_list, error = pharma_handler.get_full_inventory()
    
    if error:
        flash("No se pudo cargar el inventario.", "danger")
        inventory_list = []

    if q:
        q_lower = q.lower()
        def matches_inv(it):
            name = (it.get('nombre') or '').lower()
            cat = (it.get('categoria') or {}).get('nombre', '') if it.get('categoria') else ''
            return q_lower in name or q_lower in (cat or '').lower()
        inventory_list = [it for it in inventory_list if matches_inv(it)]

    inventory_list.sort(key=lambda it: (it.get('nombre') or '').lower(), reverse=(order == 'desc'))

    return render_template('pharmacist/inventory.html', user_name=user_name, inventory_items=inventory_list, q=q, order=order)

# --- RUTA VIEW PATIENTS ---
@pharmacist_bp.route('/patients')
@role_required(allowed_roles=['farmaceutico', 'administrador'])
def view_patients():
    pharma_handler = Pharmacist() 
    patients_list, err = pharma_handler.get_all_patients()
    
    if err:
        flash('Error al cargar la lista de pacientes: ' + err, "danger")
        patients_list = []
        
    q = (request.args.get('q') or '').strip().lower()
    order = (request.args.get('order') or 'asc').lower()

    if q:
        patients_list = [p for p in patients_list if q in (p.get('nombre_completo') or '').lower()]

    patients_list.sort(key=lambda p: (p.get('nombre_completo') or '').lower(), reverse=(order == 'desc'))

    return render_template('pharmacist/patients.html', patients=patients_list, q=(q or ''), order=order)

# --- RUTA PRESCRIPTIONS (LISTADO) - ¡CORREGIDA! ---
@pharmacist_bp.route('/prescriptions')
@role_required(allowed_roles=['farmaceutico', 'administrador'])
def view_prescriptions():
    pharma_handler = Pharmacist()
    prescriptions, error = pharma_handler.get_all_prescriptions()
    
    if error:
        flash(f"Error al cargar la lista de recetas: {error}", "danger")
        prescriptions = []

    return render_template('pharmacist/prescriptions.html', prescriptions=prescriptions)

# --- RUTA PRESCRIPTIONS (DETALLE) - ¡CORREGIDA Y ROBUSTA! ---
@pharmacist_bp.route('/prescriptions/<int:prescription_id>')
@role_required(allowed_roles=['farmaceutico', 'administrador'])
def view_prescription_details(prescription_id):
    pharma_handler = Pharmacist()
    
    # Obtener los detalles de la receta
    prescription, error = pharma_handler.get_prescription_details(prescription_id)
    
    # Manejo de errores y receta no encontrada (importante para evitar errores 'NoneType')
    if error or not prescription:
        flash(f"Receta ID {prescription_id} no encontrada o error de carga: {error if error else 'Receta no encontrada'}", "danger")
        return redirect(url_for('pharmacist.view_prescriptions'))
        
    
    # NOTA: Si los detalles de medicamentos estuvieran en un campo como 'medicamentos_json' 
    # (y fuera una cadena de texto JSON), la lógica para decodificarlo iría aquí:
    """
    medicamentos_json_string = prescription.get('medicamentos_json')
    if medicamentos_json_string:
        try:
            # Ejemplo de decodificación si fuera necesario:
            prescription['medicamentos_data'] = json.loads(medicamentos_json_string) 
        except json.JSONDecodeError:
            flash("Advertencia: No se pudieron decodificar los detalles JSON de los medicamentos.", "warning")
            prescription['medicamentos_data'] = []
    else:
        prescription['medicamentos_data'] = []
    """
    
    return render_template('pharmacist/view_prescription_details.html', prescription=prescription)


# ======================================================================================
# --- RUTAS DE ACCIÓN PARA INVENTARIO ---
# ======================================================================================

# --- RUTA 1: Reponer Stock (POST) ---
@pharmacist_bp.route('/restock/<int:product_id>', methods=['POST'])
@role_required(allowed_roles=['farmaceutico', 'administrador'])
def restock_item(product_id):
    pharma_handler = Pharmacist()
    
    quantity_str = request.form.get('quantity')
    
    try:
        quantity = int(quantity_str)
        if quantity <= 0:
             flash("La cantidad a reponer debe ser un número positivo.", "warning")
             return redirect(url_for('pharmacist.inventory'))
        
        success, error_msg = pharma_handler.restock_medicine(product_id, quantity)
        
        if success:
            flash(f"Se repuso el stock del producto ID {product_id} en {quantity} unidades.", "success")
        else:
            flash(f"Error al reponer el stock: {error_msg}", "danger")
        
        return redirect(url_for('pharmacist.inventory'))
        
    except ValueError:
        flash("Error de cantidad. La cantidad debe ser un número entero.", "danger")
        return redirect(url_for('pharmacist.inventory'))
    except Exception as e:
        flash(f"Error al procesar la reposición: {str(e)}", "danger")
        return redirect(url_for('pharmacist.inventory'))


# --- RUTA 2: Editar Producto (GET para formulario, POST para guardar) ---
@pharmacist_bp.route('/edit_medicine/<int:med_id>', methods=['GET', 'POST'])
@role_required(allowed_roles=['farmaceutico', 'administrador'])
def edit_medicine_item(med_id):
    pharma_handler = Pharmacist()
    categories, _ = pharma_handler.get_all_categories() 

    # === MANEJO DEL FORMULARIO POST (GUARDAR CAMBIOS) ===
    if request.method == 'POST':
        try:
            new_name = request.form.get('name')
            new_stock = request.form.get('stock')
            new_category_id = request.form.get('category_id')

            success_data, error_msg = pharma_handler.update_medicine(med_id, new_stock, new_name, new_category_id)

            if error_msg is None:
                flash("Producto actualizado exitosamente.", "success")
                return redirect(url_for('pharmacist.inventory'))
            else:
                flash(f"Error al actualizar el producto: {error_msg}", "danger")
                
        except Exception as e:
            flash(f"Error interno al actualizar: {str(e)}", "danger")

    # === MANEJO DEL GET (MOSTRAR FORMULARIO) ===
    inventory_data, err = pharma_handler.get_full_inventory() 
    current_data = next((item for item in inventory_data if item.get('id') == med_id), None)
    
    if err or not current_data:
        flash("No se pudo cargar el producto para edición (ID no encontrado).", "danger")
        return redirect(url_for('pharmacist.inventory'))
        
    return render_template('pharmacist/edit_medicine.html', 
                           item=current_data, 
                           categories=categories,
                           page_title='Editar Medicamento')