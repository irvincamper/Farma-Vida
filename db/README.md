Instrucciones para crear la tabla `mensajes` (chat paciente <-> doctor)

1) Abrir Supabase -> Project -> SQL Editor.
2) Copiar y pegar el contenido de `create_mensajes_table.sql` y ejecutar.

Alternativa con Supabase CLI (si lo tienes instalado):

# Inicia sesión y selecciona proyecto según tu flujo de trabajo
# Luego ejecuta:
supabase db query "$(< db/create_mensajes_table.sql)"

Notas:
- El script crea la tabla `mensajes` con `id` tipo `uuid`. Si tu tabla `perfiles` usa otro tipo, adapta las columnas `sender_id` y `receiver_id`.
- Si usas Row Level Security (RLS) debes crear políticas que permitan al backend (o a roles específicos) leer/escribir. En este repo el backend usa la key admin en `app/__init__.py` para realizar operaciones con privilegios.
 - El script crea la tabla `mensajes` con `id` tipo `uuid`. Si tu tabla `perfiles` usa otro tipo, adapta las columnas `sender_id` y `receiver_id`.
 - Incluimos en el SQL ejemplos de políticas RLS (comentadas). Si quieres acceso directo desde el cliente (navegador) habilita RLS y crea las políticas adaptadas. Ejemplos:

	* SELECT: permitir si `sender_id = auth.uid()` o `receiver_id = auth.uid()`.
	* INSERT: permitir si `sender_id = auth.uid()`.
	* UPDATE (marcar read): permitir si `sender_id = auth.uid()` o `receiver_id = auth.uid()`.

 - Seguridad: NUNCA expongas la service_role key en el frontend. Solo la anon key (`anon`) puede ir al cliente y solo si configuras RLS apropiadamente.

 Exponer anon key a plantillas (opcional y conveniente)
 -----------------------------------------------------
 1) Define la variable de entorno `SUPABASE_ANON_KEY` en tu entorno de ejecución (no la mezcles con `SUPABASE_KEY` si esta es la service_role).
 2) En `config.py` añade `SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')` o configúralo de la forma que uses.
5) El proyecto ya incluye un context processor que inyecta `SUPABASE_URL` y `SUPABASE_ANON_KEY` en las plantillas (si están configuradas). En `app/templates/layout/base.html` se inyectan las variables `window.SUPABASE_URL` y `window.SUPABASE_ANON_KEY` cuando están disponibles; `chat.js` usa esas variables para inicializar Realtime.

Ejemplo seguro para desarrollo (PowerShell):

```powershell
$env:SUPABASE_ANON_KEY = 'eyJ...tu_anon_key...'
python run.py
```

O bien exportarla como variable de entorno permanente en tu sistema o en el contenedor.

6) Políticas RLS definitivas

	- El archivo `db/rls_mensajes.sql` contiene políticas RLS listas para ejecutar en Supabase.
	- Para aplicar RLS: copia/pega el contenido de `db/rls_mensajes.sql` en el SQL editor de tu proyecto Supabase y ejecútalo.

7) Probar Realtime

	- Crea la tabla `mensajes` con `db/create_mensajes_table.sql` (si no lo has hecho).
	- Ejecuta `db/rls_mensajes.sql` para crear las políticas.
	- Establece `SUPABASE_ANON_KEY` como variable de entorno (solo la anon key) y arranca la app.
	- Abre dos navegadores con sesiones diferentes (paciente y doctor) y prueba el chat; Realtime debe propagar nuevos mensajes sin polling o con el fallback de polling si no funciona.

8) Seguridad final

	- Nunca pongas `SUPABASE_KEY` (service_role) en el frontend.
	- Revisa los logs de Supabase y las políticas si observas accesos inesperados.

