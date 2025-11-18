from supabase import create_client, Client

# =============================================================================
# ESTE ES UN CLIENTE DEDICADO EXCLUSIVAMENTE PARA OPERACIONES DE BACKEND
# QUE DEBEN TENER TODOS LOS PERMISOS Y SALTARSE LAS REGLAS DE RLS.
#
# Se inicializa directamente con la service_role_key para asegurar
# que todas las operaciones que lo usen tengan privilegios de administrador.
# =============================================================================

# Tu URL de Supabase
SUPABASE_URL = "https://gphtytezdwwfpuvwxtpn.supabase.co"

# Tu clave secreta de Supabase (service_role_key)
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdwaHR5dGV6ZHd3ZnB1dnd4dHBuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mzc2MjIwNywiZXhwIjoyMDY5MzM4MjA3fQ.o5hltHUTaKsf33y3Sg2K0xgxAVsuOeIBwxzRU9MNAQ4"

# Creación del cliente de administrador
supabase_admin_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)