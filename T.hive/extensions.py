"""
extensions.py
-------------
Aquí viven las instancias de las extensiones de Flask (SQLAlchemy,
LoginManager, CSRF, Migrate). Se declaran en un módulo separado y sin
inicializar con la app todavía (patrón "application factory") para que
tanto app.py como models.py puedan importarlas sin generar dependencias
circulares entre sí.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_migrate import Migrate

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

# Configuración del gestor de sesiones de Flask-Login
login_manager.login_view = "login"
login_manager.login_message = "Debes iniciar sesión para acceder a esta página."
login_manager.login_message_category = "info"
