# app/routes/pharmacist.py

from flask import Blueprint, render_template, g, flash, request
from ..decorators import role_required
from ..models.pharmacist import Pharmacist 
from ..models.doctor import Doctor 

pharmacist_bp = Blueprint('pharmacist', __name__)

# --- RUTA NUEVA AÑADIDA ---
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
    
    # Asegúrate de tener una plantilla en 'pharmacist/dashboard.html'
    return render_template('pharmacist/dashboard.html', stats=stats)
# --- FIN DE LA RUTA NUEVA ---


@pharmacist_bp.route('/inventory')
@role_required(allowed_roles=['farmaceutico', 'administrador'])
def inventory():
    user_name = g.profile['nombre_completo'] if g.profile else "Farmacéutico"
    pharma_handler = Pharmacist()
    inventory_list, error = pharma_handler.get_full_inventory()
    if error:
        flash("No se pudo cargar el inventario.", "danger")
    # add search and order
    q = (request.args.get('q') or '').strip().lower()
    order = (request.args.get('order') or 'asc').lower()

    if not inventory_list:
        inventory_list = []

    if q:
        def matches_inv(it):
            name = (it.get('nombre') or '').lower()
            cat = (it.get('categoria') or {}).get('nombre', '') if it.get('categoria') else ''
            return q in name or q in (cat or '').lower()
        inventory_list = [it for it in inventory_list if matches_inv(it)]

    inventory_list.sort(key=lambda it: (it.get('nombre') or '').lower(), reverse=(order == 'desc'))

    return render_template('pharmacist/inventory.html', user_name=user_name, inventory_items=inventory_list, q=(q or ''), order=order)

@pharmacist_bp.route('/patients')
@role_required(allowed_roles=['farmaceutico', 'administrador'])
def view_patients():
    doctor_handler = Doctor()
    patients_list, err = doctor_handler.get_all_patients()
    if err:
        flash('Error al cargar la lista de pacientes.', "danger")
    # support searching and ordering by name
    q = (request.args.get('q') or '').strip().lower()
    order = (request.args.get('order') or 'asc').lower()

    if not patients_list:
        patients_list = []

    if q:
        patients_list = [p for p in patients_list if q in (p.get('nombre_completo') or '').lower()]

    patients_list.sort(key=lambda p: (p.get('nombre_completo') or '').lower(), reverse=(order == 'desc'))

    return render_template('pharmacist/patients.html', patients=patients_list, q=(q or ''), order=order)

@pharmacist_bp.route('/prescriptions')
@role_required(allowed_roles=['farmaceutico', 'administrador'])
def view_prescriptions():
    return render_template('pharmacist/prescriptions.html')