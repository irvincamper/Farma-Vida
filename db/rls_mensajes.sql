-- Políticas RLS para la tabla `mensajes` (productos para usar con Supabase)
-- Este script asume que los IDs `sender_id` y `receiver_id` son UUIDs
-- que coinciden con `auth.uid()` (el UUID del usuario autenticado).

-- Habilitar Row Level Security
ALTER TABLE public.mensajes ENABLE ROW LEVEL SECURITY;

-- Permitir SELECT cuando el usuario es remitente o receptor
CREATE POLICY select_mensajes_conversation
  ON public.mensajes
  FOR SELECT
  USING (
    sender_id = auth.uid()::uuid
    OR receiver_id = auth.uid()::uuid
  );

-- Permitir INSERT sólo cuando el sender_id coincida con auth.uid()
CREATE POLICY insert_mensajes
  ON public.mensajes
  FOR INSERT
  WITH CHECK (
    sender_id = auth.uid()::uuid
  );

-- Permitir UPDATE (p. ej. marcar como leído) sólo si el usuario es sender o receiver
CREATE POLICY update_mensajes_read
  ON public.mensajes
  FOR UPDATE
  USING (
    sender_id = auth.uid()::uuid
    OR receiver_id = auth.uid()::uuid
  )
  WITH CHECK (
    sender_id = auth.uid()::uuid
    OR receiver_id = auth.uid()::uuid
  );

-- Nota: Si permites operaciones desde el backend con la service_role key,
-- estas políticas no aplicarán al backend (service_role tiene acceso total).
-- Si deseas que el cliente (navegador) pueda leer/escribir directamente
-- usando la anon key, asegúrate de desplegar estas políticas y de nunca
-- exponer la service_role key en el frontend.
