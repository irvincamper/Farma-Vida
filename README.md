# Farma-Vida

Estado del CI: ![CI](https://github.com/irvincamper/Farma-Vida/actions/workflows/python-tests.yml/badge.svg)

Descripción: Aplicación Flask para gestión de farmacia y comunicación paciente-doctor.

Instrucciones rápidas para probar el chat localmente:

1. Crear la tabla `mensajes` en Supabase con `db/create_mensajes_table.sql`.
2. Aplicar políticas RLS con `db/rls_mensajes.sql` (opcional si usarás anon key desde el frontend).
3. Establecer la anon key en desarrollo (PowerShell):

```powershell
$env:SUPABASE_ANON_KEY = 'tu_anon_key'
python run.py
```

4. Abrir en el navegador y usar `/chat/doctors` para iniciar conversaciones.
