# run.py

# Ya probamos que esta línea funciona.
from app import create_app

# Esta es la importación correcta para tu estructura plana.
# Busca 'config.py' al lado de 'run.py'.
from config import Config

# Pasamos el objeto de configuración a la fábrica
app = create_app(Config)

if __name__ == '__main__':
    # Ponemos en marcha el servidor
    app.run(debug=True, port=5001)