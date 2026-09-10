"""
config.py
---------
Configuración centralizada de la aplicación. Todos los valores sensibles
o dependientes del entorno se leen desde variables de entorno (.env),
nunca se dejan escritos directamente en el código fuente.
"""

import os
from dotenv import load_dotenv

# Carga las variables definidas en el archivo .env (si existe) al entorno
# del proceso. En producción, estas variables normalmente las inyecta
# el propio servidor/plataforma de despliegue.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    """Configuración base compartida por todos los entornos."""

    # --- Seguridad ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "clave-insegura-solo-para-desarrollo")

    # --- Base de datos ---
    # NOTA: Flask-SQLAlchemy resuelve rutas relativas de SQLite
    # (ej. "sqlite:///archivo.db") automáticamente contra la carpeta
    # instance/ de la aplicación. Por eso NO se antepone "instance/"
    # aquí para evitar una ruta duplicada como "instance/instance/...".
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///triumphare_wiki.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Branding / identidad institucional ---
    NOMBRE_INSTITUCION = os.environ.get("NOMBRE_INSTITUCION", "Colegio Triumphare")

    # --- Paginación ---
    POSTS_POR_PAGINA = int(os.environ.get("POSTS_POR_PAGINA", 9))

    # --- Formularios ---
    WTF_CSRF_TIME_LIMIT = None  # los tokens CSRF no expiran por tiempo


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    # En producción, Flask-Talisman u otras medidas de endurecimiento
    # podrían añadirse aquí sin tocar el resto de la aplicación.


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
