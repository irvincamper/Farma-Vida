from flask import Blueprint, render_template, g, request, jsonify, redirect, url_for, flash
from ..decorators import role_required
from ..models.message import Message
from ..extensions import supabase

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/conversation/<string:other_user_id>')
@role_required(allowed_roles=['paciente', 'doctor'])
def conversation(other_user_id):
    if not g.profile:
        flash('No se ha podido identificar al usuario.', 'danger')
        return redirect(url_for('auth.login'))

    current_id = g.profile['id']
    # Obtener información básica del otro usuario para mostrar nombre
    try:
        other = supabase.client.table('perfiles').select('id, nombre_completo, roles(nombre)').eq('id', other_user_id).maybe_single().execute()
        other_profile = other.data if other and other.data else {'id': other_user_id, 'nombre_completo': 'Usuario'}
    except Exception:
        other_profile = {'id': other_user_id, 'nombre_completo': 'Usuario'}

    msg = Message()
    messages, err = msg.get_conversation(current_id, other_user_id)
    if err:
        flash('No se pudieron cargar los mensajes.', 'warning')
        messages = []
    else:
        # Marcar como leídos los mensajes enviados por la otra parte hacia el usuario actual
        try:
            msg.mark_as_read(other_user_id, current_id)
        except Exception:
            # no queremos romper la vista si marcar falla
            pass

    return render_template('chat/conversation.html', messages=messages, other=other_profile, me_id=current_id)



@chat_bp.route('/doctors')
@role_required(allowed_roles=['paciente'])
def doctors():
    """Lista simple de doctores para que un paciente inicie chat con cualquiera."""
    try:
        resp = supabase.client.table('perfiles').select('id, nombre_completo').eq('id_de_rol', 2).order('nombre_completo').execute()
        doctors_list = resp.data if resp and resp.data else []
    except Exception as e:
        doctors_list = []
    return render_template('chat/doctors.html', doctors=doctors_list)


@chat_bp.route('/conversations')
@role_required(allowed_roles=['paciente','doctor'])
def conversations():
    """Lista las conversaciones recientes del usuario (último mensaje por interlocutor)."""
    if not g.profile:
        flash('No se ha podido identificar al usuario.', 'danger')
        return redirect(url_for('auth.login'))

    me = g.profile['id']
    try:
        # Obtener mensajes donde el usuario sea remitente o receptor, ordenados por fecha descendente
        resp = supabase.client.table('mensajes') \
            .select('*') \
            .or_(f"and(sender_id.eq.{me},receiver_id.is.not.null),and(receiver_id.eq.{me},sender_id.is.not.null)") \
            .order('created_at', desc=True) \
            .execute()

        raw = resp.data if resp and resp.data else []
        partners = {}
        # construir mapa partner_id -> last_message
        for m in raw:
            # determinar interlocutor
            partner = m['receiver_id'] if m.get('sender_id') == me else m.get('sender_id')
            if not partner:
                continue
            if partner not in partners:
                partners[partner] = m

        # convertir a lista de tuplas (partner_id, message)
        convo_list = []
        for pid, msg in partners.items():
            # intentar obtener nombre del partner
            try:
                p = supabase.client.table('perfiles').select('id,nombre_completo').eq('id', pid).maybe_single().execute()
                name = p.data.get('nombre_completo') if p and p.data else pid
            except Exception:
                name = pid
            convo_list.append({'partner_id': pid, 'partner_name': name, 'last_message': msg})

    except Exception as e:
        flash(f'No se pudieron cargar las conversaciones: {e}', 'warning')
        convo_list = []

    return render_template('chat/conversations.html', conversations=convo_list)


@chat_bp.route('/api/conversation/<string:other_user_id>')
@role_required(allowed_roles=['paciente', 'doctor'])
def api_conversation(other_user_id):
    if not g.profile:
        return jsonify({'error': 'No autorizado'}), 401
    current_id = g.profile['id']
    msg = Message()
    messages, err = msg.get_conversation(current_id, other_user_id)
    if err:
        return jsonify({'error': err}), 500
    return jsonify({'messages': messages})


@chat_bp.route('/api/send', methods=['POST'])
@role_required(allowed_roles=['paciente', 'doctor'])
def api_send():
    if not g.profile:
        return jsonify({'error': 'No autorizado'}), 401
    data = request.get_json() or request.form
    receiver_id = data.get('receiver_id')
    content = data.get('content')
    if not receiver_id or not content:
        return jsonify({'error': 'receiver_id y content son requeridos'}), 400

    sender_id = g.profile['id']
    msg = Message()
    res, err = msg.create_message(sender_id, receiver_id, content)
    if err:
        return jsonify({'error': err}), 500
    return jsonify({'ok': True, 'message': res})


@chat_bp.route('/send', methods=['POST'])
@role_required(allowed_roles=['paciente', 'doctor'])
def send_form():
    if not g.profile:
        flash('No autorizado', 'danger')
        return redirect(url_for('auth.login'))
    receiver_id = request.form.get('receiver_id')
    content = request.form.get('content')
    if not receiver_id or not content:
        flash('Mensaje vacío o receptor no especificado.', 'danger')
        return redirect(request.referrer or url_for('patient.profile'))

    sender_id = g.profile['id']
    msg = Message()
    _, err = msg.create_message(sender_id, receiver_id, content)
    if err:
        flash(f'Error al enviar: {err}', 'danger')
    return redirect(request.referrer or url_for('patient.profile'))
