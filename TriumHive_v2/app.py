"""
app.py
------
Punto de entrada de la plataforma TriumHive del Colegio Triumphare.
Incluye CRUD de publicaciones, adjuntos (fotos/archivos), perfil
con foto personalizable, likes asíncronos, comentarios, y búsqueda.
"""

import os
import uuid
from datetime import datetime

from flask import (
    Flask, render_template, redirect, url_for, flash, request, jsonify, abort, send_from_directory
)
from flask_login import (
    login_user, logout_user, login_required, current_user
)
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from config import config_by_name
from extensions import db, login_manager, csrf, migrate
from models import User, Post, Category, Comment, Like, PostAttachment, PUNTOS
from forms import RegistroForm, LoginForm, PostForm, ComentarioForm, EditarPerfilForm


# Extensiones permitidas
EXTENSIONES_IMAGEN = {"jpg", "jpeg", "png", "gif", "webp"}
EXTENSIONES_ARCHIVO = {"pdf", "docx", "xlsx", "txt", "zip"}
EXTENSIONES_PERMITIDAS = EXTENSIONES_IMAGEN | EXTENSIONES_ARCHIVO
MAX_ADJUNTOS_POR_POST = 5
MAX_FILE_SIZE_MB = 10


def extension_permitida(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in EXTENSIONES_PERMITIDAS


def es_imagen(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in EXTENSIONES_IMAGEN


def guardar_archivo(file, carpeta):
    """Guarda un archivo subido con nombre único. Devuelve el filename guardado."""
    ext = file.filename.rsplit(".", 1)[1].lower()
    nombre_unico = f"{uuid.uuid4().hex}.{ext}"
    ruta = os.path.join(carpeta, nombre_unico)
    file.save(ruta)
    return nombre_unico


def create_app(config_name=None):
    app = Flask(__name__, instance_relative_config=True)

    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_by_name.get(config_name, config_by_name["development"]))

    os.makedirs(app.instance_path, exist_ok=True)

    # Carpetas de uploads
    upload_base = os.path.join(app.root_path, "static", "uploads")
    app.config["UPLOAD_POSTS_DIR"] = os.path.join(upload_base, "posts")
    app.config["UPLOAD_AVATARS_DIR"] = os.path.join(upload_base, "avatars")
    app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE_MB * 1024 * 1024 * MAX_ADJUNTOS_POR_POST

    os.makedirs(app.config["UPLOAD_POSTS_DIR"], exist_ok=True)
    os.makedirs(app.config["UPLOAD_AVATARS_DIR"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Inicializar base de datos y categorías predeterminadas al arrancar la app
    with app.app_context():
        db.create_all()
        inicializar_categorias()

    @app.context_processor
    def inyectar_globales():
        return {
            "nombre_institucion": app.config.get("NOMBRE_INSTITUCION", "Colegio Triumphare"),
            "categorias_nav": Category.query.order_by(Category.nombre.asc()).all(),
            "anio_actual": datetime.now().year,
        }

    registrar_rutas(app)
    registrar_manejadores_error(app)

    return app


def inicializar_categorias():
    categorias_base = [
        {"nombre": "Información Real",  "slug": "info-real",   "icono": "📰", "color": "#1A2E6E",
         "descripcion": "Noticias, anuncios oficiales y datos verificados del colegio."},
        {"nombre": "Académico",             "slug": "academico",   "icono": "📚", "color": "#2563EB",
         "descripcion": "Apuntes, dudas de clase, proyectos y recursos de estudio."},
        {"nombre": "Eventos",               "slug": "eventos",     "icono": "🎉", "color": "#D97706",
         "descripcion": "Actividades, ferias, aniversarios y novedades del colegio."},
        {"nombre": "Deportes",              "slug": "deportes",    "icono": "🏆", "color": "#16A34A",
         "descripcion": "Torneos, resultados y convocatorias deportivas."},
        {"nombre": "Chismes",               "slug": "chismes",     "icono": "👀", "color": "#C8102E",
         "descripcion": "Rumores y comentarios informales. ¡Solo por diversión!"},
        {"nombre": "Off-Topic",             "slug": "off-topic",   "icono": "💬", "color": "#7C3AED",
         "descripcion": "Charla libre entre estudiantes, fuera de temas académicos."},
        {"nombre": "Arte & Creatividad", "slug": "arte",        "icono": "🎨", "color": "#DB2777",
         "descripcion": "Obras, proyectos artísticos, música, fotografía y más."},
        {"nombre": "Tecnología",          "slug": "tecnologia",  "icono": "💻", "color": "#0891B2",
         "descripcion": "Proyectos tech, programación, gadgets y Triumphare Digital."},
    ]

    for datos in categorias_base:
        if not Category.query.filter_by(slug=datos["slug"]).first():
            db.session.add(Category(**datos))

    db.session.commit()


def registrar_rutas(app):

    # =========================================================
    #  SERVIR UPLOADS
    # =========================================================
    @app.route("/uploads/posts/<path:filename>")
    def uploaded_post_file(filename):
        return send_from_directory(app.config["UPLOAD_POSTS_DIR"], filename)

    @app.route("/uploads/avatars/<path:filename>")
    def uploaded_avatar(filename):
        return send_from_directory(app.config["UPLOAD_AVATARS_DIR"], filename)

    # =========================================================
    #  PÁGINA PRINCIPAL
    # =========================================================
    @app.route("/")
    def index():
        pagina = request.args.get("pagina", 1, type=int)
        por_pagina = app.config.get("POSTS_POR_PAGINA", 10)

        posts_recientes = (
            Post.query.order_by(Post.fijado.desc(), Post.fecha_creacion.desc())
            .paginate(page=pagina, per_page=por_pagina, error_out=False)
        )

        top_estudiantes = (
            User.query.order_by(User.prestige_points.desc()).limit(5).all()
        )

        return render_template(
            "index.html",
            posts=posts_recientes,
            top_estudiantes=top_estudiantes,
        )

    # =========================================================
    #  EXPLORAR
    # =========================================================
    @app.route("/explorar")
    def explorar():
        categoria_slug = request.args.get("categoria", "todas")
        pagina = request.args.get("pagina", 1, type=int)
        por_pagina = app.config.get("POSTS_POR_PAGINA", 10)

        query = Post.query.order_by(Post.fecha_creacion.desc())

        categoria_activa = None
        if categoria_slug and categoria_slug != "todas":
            categoria_activa = Category.query.filter_by(slug=categoria_slug).first_or_404()
            query = query.filter(Post.categoria_id == categoria_activa.id)

        posts = query.paginate(page=pagina, per_page=por_pagina, error_out=False)

        return render_template(
            "explorar.html",
            posts=posts,
            categoria_activa=categoria_activa,
        )

    # =========================================================
    #  API DE BÚSQUEDA
    # =========================================================
    @app.route("/api/buscar")
    def api_buscar():
        termino = request.args.get("q", "").strip()
        if len(termino) < 2:
            return jsonify({"resultados": []})

        posts = (
            Post.query.filter(
                or_(Post.titulo.ilike(f"%{termino}%"), Post.contenido.ilike(f"%{termino}%"))
            )
            .order_by(Post.fecha_creacion.desc())
            .limit(8)
            .all()
        )

        resultados = [
            {
                "id": p.id,
                "titulo": p.titulo,
                "categoria": p.categoria.nombre,
                "categoria_icono": p.categoria.icono,
                "autor": p.autor.username,
                "url": url_for("post_detalle", post_id=p.id),
            }
            for p in posts
        ]
        return jsonify({"resultados": resultados})

    # =========================================================
    #  AUTENTICACIÓN
    # =========================================================
    @app.route("/registro", methods=["GET", "POST"])
    def registro():
        if current_user.is_authenticated:
            return redirect(url_for("index"))

        form = RegistroForm()
        if form.validate_on_submit():
            nuevo_usuario = User(
                username=form.username.data.strip(),
                email=form.email.data.strip().lower(),
                nombre_completo=form.nombre_completo.data.strip(),
                grado_seccion=form.grado_seccion.data.strip() if form.grado_seccion.data else None,
            )
            nuevo_usuario.set_password(form.password.data)

            db.session.add(nuevo_usuario)
            db.session.commit()

            flash("¡Cuenta creada con éxito! Ya puedes iniciar sesión.", "success")
            return redirect(url_for("login"))

        return render_template("registro.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("index"))

        form = LoginForm()
        if form.validate_on_submit():
            usuario = User.query.filter_by(email=form.email.data.strip().lower()).first()

            if usuario and usuario.check_password(form.password.data):
                login_user(usuario, remember=form.recordarme.data)
                flash(f"¡Bienvenido de nuevo, {usuario.nombre_completo or usuario.username}!", "success")
                siguiente = request.args.get("next")
                return redirect(siguiente or url_for("index"))

            flash("Correo o contraseña incorrectos.", "danger")

        return render_template("login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Sesión cerrada correctamente.", "info")
        return redirect(url_for("index"))

    # =========================================================
    #  CRUD DE PUBLICACIONES
    # =========================================================
    @app.route("/post/nuevo", methods=["GET", "POST"])
    @login_required
    def crear_post():
        form = PostForm()
        form.categoria_id.choices = [
            (c.id, f"{c.icono} {c.nombre}") for c in Category.query.order_by(Category.nombre.asc()).all()
        ]

        if form.validate_on_submit():
            post = Post(
                titulo=form.titulo.data.strip(),
                contenido=form.contenido.data.strip(),
                categoria_id=form.categoria_id.data,
                autor_id=current_user.id,
            )
            db.session.add(post)
            db.session.flush()

            archivos = request.files.getlist("adjuntos")
            conteo = 0
            for f in archivos:
                if f and f.filename and conteo < MAX_ADJUNTOS_POR_POST:
                    if extension_permitida(f.filename):
                        nombre = guardar_archivo(f, app.config["UPLOAD_POSTS_DIR"])
                        adj = PostAttachment(
                            post_id=post.id,
                            filename=nombre,
                            original_name=secure_filename(f.filename),
                            es_imagen=es_imagen(f.filename),
                            mime_type=f.content_type,
                        )
                        db.session.add(adj)
                        conteo += 1

            current_user.sumar_puntos(PUNTOS.CREAR_POST)
            db.session.commit()
            flash("Tu publicación fue creada correctamente.", "success")
            return redirect(url_for("post_detalle", post_id=post.id))

        return render_template("crear_post.html", form=form)

    @app.route("/post/<int:post_id>")
    def post_detalle(post_id):
        post = Post.query.get_or_404(post_id)
        form_comentario = ComentarioForm()
        return render_template("post_detalle.html", post=post, form_comentario=form_comentario)

    @app.route("/post/<int:post_id>/editar", methods=["GET", "POST"])
    @login_required
    def editar_post(post_id):
        post = Post.query.get_or_404(post_id)

        if post.autor_id != current_user.id and not current_user.es_admin:
            abort(403)

        form = PostForm(obj=post)
        form.categoria_id.choices = [
            (c.id, f"{c.icono} {c.nombre}") for c in Category.query.order_by(Category.nombre.asc()).all()
        ]

        if request.method == "GET":
            form.categoria_id.data = post.categoria_id

        if form.validate_on_submit():
            post.titulo = form.titulo.data.strip()
            post.contenido = form.contenido.data.strip()
            post.categoria_id = form.categoria_id.data

            archivos = request.files.getlist("adjuntos")
            conteo_actual = post.adjuntos.count()
            for f in archivos:
                if f and f.filename and conteo_actual < MAX_ADJUNTOS_POR_POST:
                    if extension_permitida(f.filename):
                        nombre = guardar_archivo(f, app.config["UPLOAD_POSTS_DIR"])
                        adj = PostAttachment(
                            post_id=post.id,
                            filename=nombre,
                            original_name=secure_filename(f.filename),
                            es_imagen=es_imagen(f.filename),
                            mime_type=f.content_type,
                        )
                        db.session.add(adj)
                        conteo_actual += 1

            db.session.commit()
            flash("La publicación fue actualizada.", "success")
            return redirect(url_for("post_detalle", post_id=post.id))

        return render_template("editar_post.html", form=form, post=post)

    @app.route("/post/<int:post_id>/eliminar", methods=["POST"])
    @login_required
    def eliminar_post(post_id):
        post = Post.query.get_or_404(post_id)

        if post.autor_id != current_user.id and not current_user.es_admin:
            abort(403)

        for adj in post.adjuntos.all():
            ruta = os.path.join(app.config["UPLOAD_POSTS_DIR"], adj.filename)
            if os.path.exists(ruta):
                os.remove(ruta)

        db.session.delete(post)
        db.session.commit()
        flash("La publicación fue eliminada.", "info")
        return redirect(url_for("explorar"))

    @app.route("/post/<int:post_id>/adjunto/<int:adj_id>/eliminar", methods=["POST"])
    @login_required
    def eliminar_adjunto(post_id, adj_id):
        adj = PostAttachment.query.get_or_404(adj_id)
        post = Post.query.get_or_404(post_id)

        if post.autor_id != current_user.id and not current_user.es_admin:
            abort(403)

        ruta = os.path.join(app.config["UPLOAD_POSTS_DIR"], adj.filename)
        if os.path.exists(ruta):
            os.remove(ruta)

        db.session.delete(adj)
        db.session.commit()
        flash("Adjunto eliminado.", "info")
        return redirect(url_for("editar_post", post_id=post_id))

    # =========================================================
    #  COMENTARIOS
    # =========================================================
    @app.route("/post/<int:post_id>/comentar", methods=["POST"])
    @login_required
    def comentar_post(post_id):
        post = Post.query.get_or_404(post_id)
        form = ComentarioForm()

        if form.validate_on_submit():
            comentario = Comment(
                contenido=form.contenido.data.strip(),
                post_id=post.id,
                autor_id=current_user.id,
            )
            db.session.add(comentario)

            current_user.sumar_puntos(PUNTOS.ESCRIBIR_COMENTARIO)
            if post.autor_id != current_user.id:
                post.autor.sumar_puntos(PUNTOS.RECIBIR_COMENTARIO)

            db.session.commit()
            flash("Comentario publicado.", "success")
        else:
            flash("No se pudo publicar el comentario.", "danger")

        return redirect(url_for("post_detalle", post_id=post.id))

    # =========================================================
    #  LIKES ASÍNCRONOS
    # =========================================================
    @app.route("/post/<int:post_id>/like", methods=["POST"])
    @login_required
    def toggle_like(post_id):
        post = Post.query.get_or_404(post_id)
        like_existente = Like.query.filter_by(usuario_id=current_user.id, post_id=post.id).first()

        if like_existente:
            db.session.delete(like_existente)
            if post.autor_id != current_user.id:
                post.autor.sumar_puntos(-PUNTOS.RECIBIR_LIKE)
            dio_like = False
        else:
            nuevo_like = Like(usuario_id=current_user.id, post_id=post.id)
            db.session.add(nuevo_like)
            if post.autor_id != current_user.id:
                post.autor.sumar_puntos(PUNTOS.RECIBIR_LIKE)
            dio_like = True

        db.session.commit()

        return jsonify({
            "ok": True,
            "dio_like": dio_like,
            "total_likes": post.total_likes,
        })

    # =========================================================
    #  PERFIL DE USUARIO
    # =========================================================
    @app.route("/perfil/<username>")
    def perfil(username):
        usuario = User.query.filter_by(username=username).first_or_404()
        posts_usuario = (
            Post.query.filter_by(autor_id=usuario.id)
            .order_by(Post.fecha_creacion.desc())
            .all()
        )
        return render_template("perfil.html", usuario=usuario, posts=posts_usuario)

    @app.route("/perfil/<username>/editar", methods=["GET", "POST"])
    @login_required
    def editar_perfil(username):
        if current_user.username != username and not current_user.es_admin:
            abort(403)

        usuario = User.query.filter_by(username=username).first_or_404()
        form = EditarPerfilForm(obj=usuario)

        if form.validate_on_submit():
            usuario.nombre_completo = (form.nombre_completo.data or "").strip() or None
            usuario.grado_seccion = (form.grado_seccion.data or "").strip() or None
            usuario.bio = (form.bio.data or "").strip() or None

            if form.eliminar_avatar.data and usuario.avatar_filename:
                ruta = os.path.join(app.config["UPLOAD_AVATARS_DIR"], usuario.avatar_filename)
                if os.path.exists(ruta):
                    os.remove(ruta)
                usuario.avatar_filename = None

            avatar_file = form.avatar.data
            if avatar_file and avatar_file.filename:
                if usuario.avatar_filename:
                    ruta_ant = os.path.join(app.config["UPLOAD_AVATARS_DIR"], usuario.avatar_filename)
                    if os.path.exists(ruta_ant):
                        os.remove(ruta_ant)
                nuevo_nombre = guardar_archivo(avatar_file, app.config["UPLOAD_AVATARS_DIR"])
                usuario.avatar_filename = nuevo_nombre

            db.session.commit()
            flash("Perfil actualizado correctamente.", "success")
            return redirect(url_for("perfil", username=usuario.username))

        return render_template("editar_perfil.html", form=form, usuario=usuario)


def registrar_manejadores_error(app):
    @app.errorhandler(403)
    def prohibido(error):
        return render_template("error.html", codigo=403, mensaje="No tienes permiso para realizar esta acción."), 403

    @app.errorhandler(404)
    def no_encontrado(error):
        return render_template("error.html", codigo=404, mensaje="No encontramos lo que buscabas."), 404

    @app.errorhandler(500)
    def error_servidor(error):
        return render_template("error.html", codigo=500, mensaje="Ocurrió un error inesperado en el servidor."), 500


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)