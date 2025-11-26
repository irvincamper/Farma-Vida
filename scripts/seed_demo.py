"""Seed demo data: crea un doctor, un paciente y unos mensajes en Supabase.

Usa las claves definidas en `config.py`. Ejecutar solo en entornos de desarrollo.
"""
import sys
from supabase import create_client
from config import Config

def main():
    url = Config.SUPABASE_URL
    key = Config.SUPABASE_KEY
    if not url or not key:
        print("Faltan SUPABASE_URL o SUPABASE_KEY en config.py")
        sys.exit(1)

    sb = create_client(url, key)

    # Crear dos perfiles en `perfiles` (doctor y paciente)
    import uuid
    doctor = {
        'id': str(uuid.uuid4()), 'nombre_completo': 'Dr. Demo', 'id_de_rol': 2
    }
    paciente = {
        'id': str(uuid.uuid4()), 'nombre_completo': 'Paciente Demo', 'id_de_rol': 3
    }

    try:
        # Insertar perfiles con gen_random_uuid() para id si la BD lo permite
        # Aquí usamos la inserción simple sin asegurar UUID — adapta según tu esquema
        res_doc = sb.table('perfiles').insert({'id': doctor['id'], 'nombre_completo': doctor['nombre_completo'], 'id_de_rol': 2}).execute()
        res_pat = sb.table('perfiles').insert({'id': paciente['id'], 'nombre_completo': paciente['nombre_completo'], 'id_de_rol': 3}).execute()

        doc_id = None
        pat_id = None
        if res_doc and res_doc.data:
            # cuando supabase devuelve la fila insertada
            doc_id = res_doc.data[0].get('id') if isinstance(res_doc.data, list) else res_doc.data.get('id')
        if res_pat and res_pat.data:
            pat_id = res_pat.data[0].get('id') if isinstance(res_pat.data, list) else res_pat.data.get('id')

        print('Doctor id:', doc_id)
        print('Paciente id:', pat_id)

        if not doc_id or not pat_id:
            print('Advertencia: no se pudieron recuperar IDs de perfiles insertados. Revisa la tabla `perfiles`.')

        # Insertar registro en 'pacientes' si es necesario (asociar user_id)
        try:
            if pat_id:
                sb.table('pacientes').insert({'nombre_completo': paciente['nombre_completo'], 'user_id': pat_id}).execute()
        except Exception as e:
            print('No se pudo insertar en tabla pacientes (opcional):', e)

        # Crear mensajes de ejemplo en `mensajes`
        if doc_id and pat_id:
            sb.table('mensajes').insert([
                {'sender_id': pat_id, 'receiver_id': doc_id, 'content': 'Hola doctor, necesito ayuda.'},
                {'sender_id': doc_id, 'receiver_id': pat_id, 'content': 'Hola, ¿en qué puedo ayudarte?'}
            ]).execute()
            print('Mensajes de demo creados.')

    except Exception as e:
        print('Error al sembrar datos de demo:', e)

if __name__ == '__main__':
    print('Sembrando datos de demo en Supabase (asegúrate de estar en desarrollo).')
    main()
