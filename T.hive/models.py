"""
models.py
---------
Modelos de datos de la plataforma, construidos sobre Flask-SQLAlchemy.

Entidades:
    - User:     cuenta de un estudiante/miembro de la comunidad.
    - Category: categoría temática de una publicación (Académico, Eventos...).
    - Post:     publicación creada por un usuario.
    - Comment:  comentario de un usuario sobre una publicación.
    - Like:     "me gusta" de un usuario sobre una publicación (relación N:M
                materializada, para poder saber quién ha dado like a qué).

Gamificación:
    Cada usuario acumula "Puntos de Prestigio" (prestige_points) según su
    participación. Las reglas de puntuación viven en la constante PUNTOS
    y se aplican mediante los métodos de ayuda de cada modelo, de forma
    que la lógica de negocio quede junto a los datos que modifica.
"""

from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db, login_manager


# ---------------------------------------------------------------------------
# Reglas de gamificación: puntos de prestigio otorgados por cada acción.
# Centralizarlas aquí facilita rebalancear el sistema sin tocar las rutas.
# ---------------------------------------------------------------------------
class PUNTOS:
    CREAR_POST = 10
    RECIBIR_LIKE = 2
    ESCRIBIR_COMENTARIO = 1
    RECIBIR_COMENTARIO = 1


def ahora_utc():
    """Devuelve la fecha/hora actual en UTC (evita el uso de utcnow() obsoleto)."""
    return datetime.now(timezone.utc)


@login_manager.user_loader
def load_user(user_id):
    """Callback requerido por Flask-Login para recuperar el usuario de la sesión."""
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    """Cuenta de un miembro de la comunidad educativa."""

    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Perfil
    nombre_completo = db.Column(db.String(120), nullable=True)
    grado_seccion = db.Column(db.String(40), nullable=True)  # ej. "5to Año - Sección B"
    bio = db.Column(db.String(280), nullable=True)
    avatar_color = db.Column(db.String(7), default="#14213D")  # color de respaldo si no hay foto

    # Gamificación
    prestige_points = db.Column(db.Integer, default=0, nullable=False)

    # Metadatos
    fecha_registro = db.Column(db.DateTime, default=ahora_utc)
    es_admin = db.Column(db.Boolean, default=False)

    # Relaciones
    posts = db.relationship("Post", backref="autor", lazy="dynamic", cascade="all, delete-orphan")
    comentarios = db.relationship("Comment", backref="autor", lazy="dynamic", cascade="all, delete-orphan")
    likes = db.relationship("Like", backref="usuario", lazy="dynamic", cascade="all, delete-orphan")

    # --- Contraseña ---
    def set_password(self, password_plano):
        self.password_hash = generate_password_hash(password_plano)

    def check_password(self, password_plano):
        return check_password_hash(self.password_hash, password_plano)

    # --- Gamificación ---
    def sumar_puntos(self, cantidad):
        self.prestige_points = (self.prestige_points or 0) + cantidad

    @property
    def rango(self):
        """Título honorífico calculado a partir de los puntos de prestigio."""
        p = self.prestige_points or 0
        if p >= 300:
            return "Leyenda Triumphare"
        if p >= 150:
            return "Mentor Destacado"
        if p >= 75:
            return "Colaborador Activo"
        if p >= 20:
            return "Miembro Comprometido"
        return "Nuevo Miembro"

    @property
    def iniciales(self):
        base = self.nombre_completo or self.username
        partes = base.strip().split()
        if len(partes) >= 2:
            return (partes[0][0] + partes[1][0]).upper()
        return base[:2].upper()

    def __repr__(self):
        return f"<User {self.username}>"


class Category(db.Model):
    """Categoría temática bajo la que se organizan las publicaciones."""

    __tablename__ = "categorias"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    icono = db.Column(db.String(10), default="📌")  # emoji/ícono representativo
    color = db.Column(db.String(7), default="#14213D")  # color de acento de la categoría
    descripcion = db.Column(db.String(160), nullable=True)

    posts = db.relationship("Post", backref="categoria", lazy="dynamic")

    def __repr__(self):
        return f"<Category {self.nombre}>"


class Post(db.Model):
    """Publicación creada por un estudiante dentro de una categoría."""

    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    contenido = db.Column(db.Text, nullable=False)

    autor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=False)

    fecha_creacion = db.Column(db.DateTime, default=ahora_utc)
    fecha_actualizacion = db.Column(db.DateTime, default=ahora_utc, onupdate=ahora_utc)
    fijado = db.Column(db.Boolean, default=False)  # permite destacar anuncios importantes

    comentarios = db.relationship(
        "Comment", backref="post", lazy="dynamic", cascade="all, delete-orphan",
        order_by="Comment.fecha_creacion.asc()"
    )
    likes = db.relationship("Like", backref="post", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def total_likes(self):
        return self.likes.count()

    @property
    def total_comentarios(self):
        return self.comentarios.count()

    def ha_dado_like(self, user):
        """Indica si un usuario dado ya marcó "me gusta" en esta publicación."""
        if user is None or not user.is_authenticated:
            return False
        return self.likes.filter_by(usuario_id=user.id).first() is not None

    @property
    def resumen(self):
        """Extracto corto del contenido para tarjetas/listados."""
        texto = self.contenido.strip()
        return texto if len(texto) <= 180 else texto[:180].rsplit(" ", 1)[0] + "…"

    def __repr__(self):
        return f"<Post {self.titulo!r}>"


class Comment(db.Model):
    """Comentario de un usuario sobre una publicación."""

    __tablename__ = "comentarios"

    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.String(500), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=ahora_utc)

    autor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)

    def __repr__(self):
        return f"<Comment {self.id} en Post {self.post_id}>"


class Like(db.Model):
    """
    Relación N:M materializada entre usuarios y publicaciones.
    Se modela como tabla propia (en vez de una simple tabla de asociación)
    para poder guardar metadatos como la fecha del like si se necesitara.
    """

    __tablename__ = "likes"
    __table_args__ = (
        db.UniqueConstraint("usuario_id", "post_id", name="uq_like_usuario_post"),
    )

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=ahora_utc)

    def __repr__(self):
        return f"<Like usuario={self.usuario_id} post={self.post_id}>"
