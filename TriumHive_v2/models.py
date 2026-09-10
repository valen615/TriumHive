"""
models.py
---------
Modelos de datos de la plataforma TriumHive, construidos sobre Flask-SQLAlchemy.

Entidades:
    - User:        cuenta de un estudiante/miembro de la comunidad.
    - Category:    categoría temática de una publicación.
    - Post:        publicación creada por un usuario (soporta adjuntos).
    - PostAttachment: archivo/imagen adjunto a un post.
    - Comment:     comentario de un usuario sobre una publicación.
    - Like:        "me gusta" de un usuario sobre una publicación.
"""

from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db, login_manager


class PUNTOS:
    CREAR_POST = 10
    RECIBIR_LIKE = 2
    ESCRIBIR_COMENTARIO = 1
    RECIBIR_COMENTARIO = 1


def ahora_utc():
    return datetime.now(timezone.utc)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Perfil
    nombre_completo = db.Column(db.String(120), nullable=True)
    grado_seccion = db.Column(db.String(40), nullable=True)
    bio = db.Column(db.String(280), nullable=True)
    avatar_color = db.Column(db.String(7), default="#1A2E6E")
    avatar_filename = db.Column(db.String(255), nullable=True)  # foto de perfil personalizada

    # Gamificación
    prestige_points = db.Column(db.Integer, default=0, nullable=False)

    # Metadatos
    fecha_registro = db.Column(db.DateTime, default=ahora_utc)
    es_admin = db.Column(db.Boolean, default=False)

    # Relaciones
    posts = db.relationship("Post", backref="autor", lazy="dynamic", cascade="all, delete-orphan")
    comentarios = db.relationship("Comment", backref="autor", lazy="dynamic", cascade="all, delete-orphan")
    likes = db.relationship("Like", backref="usuario", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password_plano):
        self.password_hash = generate_password_hash(password_plano)

    def check_password(self, password_plano):
        return check_password_hash(self.password_hash, password_plano)

    def sumar_puntos(self, cantidad):
        self.prestige_points = (self.prestige_points or 0) + cantidad

    @property
    def tiene_avatar(self):
        return bool(self.avatar_filename)

    @property
    def rango(self):
        p = self.prestige_points or 0
        if p >= 500:
            return "Leyenda Triumphare"
        if p >= 300:
            return "Mentor Destacado"
        if p >= 150:
            return "Colaborador Activo"
        if p >= 50:
            return "Miembro Comprometido"
        return "Nuevo Miembro"

    @property
    def rango_icono(self):
        p = self.prestige_points or 0
        if p >= 500: return "👑"
        if p >= 300: return "🏆"
        if p >= 150: return "⭐"
        if p >= 50:  return "🎖️"
        return "🌱"

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
    __tablename__ = "categorias"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    icono = db.Column(db.String(10), default="📌")
    color = db.Column(db.String(7), default="#1A2E6E")
    descripcion = db.Column(db.String(160), nullable=True)

    posts = db.relationship("Post", backref="categoria", lazy="dynamic")

    def __repr__(self):
        return f"<Category {self.nombre}>"


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    contenido = db.Column(db.Text, nullable=False)

    autor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=False)

    fecha_creacion = db.Column(db.DateTime, default=ahora_utc)
    fecha_actualizacion = db.Column(db.DateTime, default=ahora_utc, onupdate=ahora_utc)
    fijado = db.Column(db.Boolean, default=False)

    comentarios = db.relationship(
        "Comment", backref="post", lazy="dynamic", cascade="all, delete-orphan",
        order_by="Comment.fecha_creacion.asc()"
    )
    likes = db.relationship("Like", backref="post", lazy="dynamic", cascade="all, delete-orphan")
    adjuntos = db.relationship("PostAttachment", backref="post", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def total_likes(self):
        return self.likes.count()

    @property
    def total_comentarios(self):
        return self.comentarios.count()

    @property
    def imagen_principal(self):
        """Devuelve el primer adjunto de imagen, si existe."""
        return self.adjuntos.filter(PostAttachment.es_imagen == True).first()

    def ha_dado_like(self, user):
        if user is None or not user.is_authenticated:
            return False
        return self.likes.filter_by(usuario_id=user.id).first() is not None

    @property
    def resumen(self):
        texto = self.contenido.strip()
        return texto if len(texto) <= 200 else texto[:200].rsplit(" ", 1)[0] + "…"

    def __repr__(self):
        return f"<Post {self.titulo!r}>"


class PostAttachment(db.Model):
    """Archivo o imagen adjunto a una publicación."""

    __tablename__ = "post_adjuntos"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    filename = db.Column(db.String(255), nullable=False)   # nombre guardado en disco
    original_name = db.Column(db.String(255), nullable=True)  # nombre original del usuario
    es_imagen = db.Column(db.Boolean, default=False)
    mime_type = db.Column(db.String(80), nullable=True)
    tamanio_bytes = db.Column(db.Integer, nullable=True)
    fecha_subida = db.Column(db.DateTime, default=ahora_utc)

    @property
    def tamanio_legible(self):
        b = self.tamanio_bytes or 0
        if b < 1024: return f"{b} B"
        if b < 1024**2: return f"{b/1024:.1f} KB"
        return f"{b/1024**2:.1f} MB"

    def __repr__(self):
        return f"<PostAttachment {self.filename}>"


class Comment(db.Model):
    __tablename__ = "comentarios"

    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.String(500), nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=ahora_utc)

    autor_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)

    def __repr__(self):
        return f"<Comment {self.id} en Post {self.post_id}>"


class Like(db.Model):
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
