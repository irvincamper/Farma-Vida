class Config:
    SECRET_KEY = 'una-clave-secreta-muy-larga-y-dificil-de-adivinar'
    
    SUPABASE_URL = "https://gphtytezdwwfpuvwxtpn.supabase.co"
    
    # service role / admin key (mantener fuera del frontend)
    SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdwaHR5dGV6ZHd3ZnB1dnd4dHBuIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mzc2MjIwNywiZXhwIjoyMDY5MzM4MjA3fQ.o5hltHUTaKsf33y3Sg2K0xgxAVsuOeIBwxzRU9MNAQ4"

    # Opcional: la anon key que se puede inyectar al frontend si la config la define.
    # Recomendado: establecer esta variable vía variable de entorno en producción.
    SUPABASE_ANON_KEY = None

    # Habilitar rutas de desarrollo útiles (solo en entornos locales)
    ENABLE_DEV_ROUTES = True