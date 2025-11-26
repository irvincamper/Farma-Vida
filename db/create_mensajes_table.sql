-- Script para crear la tabla `mensajes` usada por el chat directo
-- Ejecutar en Supabase SQL editor o con supabase CLI

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS mensajes (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  sender_id uuid NOT NULL,
  receiver_id uuid NOT NULL,
  content text NOT NULL,
  created_at timestamptz DEFAULT now(),
  "read" boolean DEFAULT false
);

-- Índices para búsquedas por conversación
CREATE INDEX IF NOT EXISTS idx_mensajes_sender_receiver_created_at ON mensajes (sender_id, receiver_id, created_at);
CREATE INDEX IF NOT EXISTS idx_mensajes_receiver_created_at ON mensajes (receiver_id, created_at);

-- Opcional: política RLS de ejemplo (si usas RLS, adáptala a tus roles)
-- ALTER TABLE mensajes ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY mensajes_full_access ON mensajes
--   USING (true)
--   WITH CHECK (true);

-- Ejemplo de políticas RLS recomendadas (más seguras):
-- Permitir que el propietario (sender) inserte/lea sus mensajes y que el receptor lea sus mensajes.
-- Requiere que la autenticación de cliente use JWT con "sub" = UUID del perfil (auth.uid()).
-- Ajusta los nombres de roles/claims según tu setup de Supabase.
-- Habilita RLS y crea las políticas:
-- ALTER TABLE mensajes ENABLE ROW LEVEL SECURITY;
--
-- -- Lectura: el remitente o el receptor puede seleccionar el mensaje
-- CREATE POLICY "select_mensajes_conversation" ON mensajes
--   FOR SELECT
--   USING (sender_id::text = auth.uid() OR receiver_id::text = auth.uid());
--
-- -- Inserción: cualquier usuario autenticado puede insertar mensajes donde sender_id == auth.uid()
-- CREATE POLICY "insert_mensajes" ON mensajes
--   FOR INSERT
--   WITH CHECK (sender_id::text = auth.uid());
--
-- -- Actualización: solo el receptor o el remitente puede marcar como leido
-- CREATE POLICY "update_mensajes_read" ON mensajes
--   FOR UPDATE
--   USING (sender_id::text = auth.uid() OR receiver_id::text = auth.uid())
--   WITH CHECK ((sender_id::text = auth.uid() OR receiver_id::text = auth.uid()));

-- Nota: Si tu backend usa la service_role key para todas las operaciones, RLS no aplicará al backend. Sin embargo
-- si permites acceso directo desde el cliente (browser), necesitas estas políticas y exponer SOLO la anon key al cliente.

-- Nota: Si tu tabla de perfiles usa UUIDs o serials ajusta el tipo de `sender_id`/`receiver_id` según corresponda.
