"""
app.py
------
Punto de entrada de la aplicación "Triumphare Wiki". Define la instancia
de Flask, registra las extensiones y contiene todas las rutas de la
plataforma: autenticación, CRUD de publicaciones, likes asíncronos,
comentarios, perfiles y búsqueda.

Ejecutar en desarrollo:
    flask run
o bien:
    python app.py
"""

import os
from datetime import datetime

from flask import (
    Flask, render_template, redirect, url_for, flash, request, jsonify, abort
)
from flask_login import (
    login_user, logout_user, login_required, current_user
)
from sqlalchemy import or_

from config import config_by_name
from extensions import db, login_manager, csrf, migrate
from models import User, Post, Category, Comment, Like, PUNTOS
from forms import RegistroForm, LoginForm, PostForm, ComentarioForm


def create_app(config_name=None):
    """Application factory: construye y configura la instancia de Flask."""

    app = Flask(__name__, instance_relative_config=True)

    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app.config.from_object(config_by_name.get(config_name, "development"))

    # Asegura que exista la carpeta instance/ para la base de datos SQLite
    os.makedirs(app.instance_path, exist_ok=True)

    # --- Inicialización de extensiones ---
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # --- Variables globales disponibles en todas las plantillas Jinja2 ---
    @app.context_processor
    def inyectar_globales():
        return {
            "nombre_institucion": app.config["NOMBRE_INSTITUCION"],
            "categorias_nav": Category.query.order_by(Category.nombre.asc()).all(),
            "anio_actual": datetime.now().year,
        }

    registrar_rutas(app)
    registrar_manejadores_error(app)

    return app


def registrar_rutas(app):
    """Registra todas las rutas/vistas de la aplicación sobre la app dada."""

    # =========================================================
    #  PÁGINA PRINCIPAL
    # =========================================================
    @app.route("/")
    def index():
        pagina = request.args.get("pagina", 1, type=int)
        por_pagina = app.config["POSTS_POR_PAGINA"]

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
    #  EXPLORAR (listado con filtro por categoría + búsqueda)
    # =========================================================
    @app.route("/explorar")
    def explorar():
        categoria_slug = request.args.get("categoria", "todas")
        pagina = request.args.get("pagina", 1, type=int)
        por_pagina = app.config["POSTS_POR_PAGINA"]

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
    #  API DE BÚSQUEDA EN TIEMPO REAL (para search.js)
    # =========================================================
    @app.route("/api/buscar")
    def api_buscar():
        termino = request.args.get("q", "").strip()
        if len(termino) < 2:
            return jsonify({"resultados": []})

        posts = (
            Post.query.filter(Post.titulo.ilike(f"%{termino}%"))
            .order_by(Post.fecha_creacion.desc())
            .limit(8)
            .all()
        )

        resultados = [
            {
                "id": p.id,
                "titulo": p.titulo,
                "categoria": p.categoria.nombre,
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
            (c.id, c.nombre) for c in Category.query.order_by(Category.nombre.asc()).all()
        ]

        if form.validate_on_submit():
            post = Post(
                titulo=form.titulo.data.strip(),
                contenido=form.contenido.data.strip(),
                categoria_id=form.categoria_id.data,
                autor_id=current_user.id,
            )
            db.session.add(post)

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
            (c.id, c.nombre) for c in Category.query.order_by(Category.nombre.asc()).all()
        ]

        if request.method == "GET":
            form.categoria_id.data = post.categoria_id

        if form.validate_on_submit():
            post.titulo = form.titulo.data.strip()
            post.contenido = form.contenido.data.strip()
            post.categoria_id = form.categoria_id.data

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

        db.session.delete(post)
        db.session.commit()
        flash("La publicación fue eliminada.", "info")
        return redirect(url_for("explorar"))

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
            flash("No se pudo publicar el comentario. Verifica el contenido.", "danger")

        return redirect(url_for("post_detalle", post_id=post.id))

    # =========================================================
    #  LIKES ASÍNCRONOS (Fetch API desde likes.js)
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


def registrar_manejadores_error(app):
    """Páginas de error coherentes con la identidad visual del sitio."""

    @app.errorhandler(403)
    def prohibido(error):
        return render_template("error.html", codigo=403, mensaje="No tienes permiso para realizar esta acción."), 403

    @app.errorhandler(404)
    def no_encontrado(error):
        return render_template("error.html", codigo=404, mensaje="No encontramos lo que buscabas."), 404

    @app.errorhandler(500)
    def error_servidor(error):
        return render_template("error.html", codigo=500, mensaje="Ocurrió un error inesperado en el servidor."), 500


# Instancia de módulo, usada por "flask run" y por WSGI en producción.
app = create_app()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        # Siembra mínima e indispensable: las categorías estructurales del
        # foro. Esto NO es contenido inventado del colegio, son únicamente
        # las pestañas/etiquetas de organización solicitadas para que la
        # plataforma sea usable desde el primer arranque.
        categorias_base = [
            {"nombre": "Académico", "slug": "academico", "icono": "📚", "color": "#14213D",
             "descripcion": "Apuntes, dudas de clase, proyectos y recursos de estudio."},
            {"nombre": "Eventos", "slug": "eventos", "icono": "🎉", "color": "#E8A33D",
             "descripcion": "Actividades, ferias, aniversarios y novedades del colegio."},
            {"nombre": "Deportes", "slug": "deportes", "icono": "🏆", "color": "#2E8B77",
             "descripcion": "Torneos, resultados y convocatorias deportivas."},
            {"nombre": "Off-Topic", "slug": "off-topic", "icono": "💬", "color": "#8C5AA8",
             "descripcion": "Charla libre entre estudiantes, fuera de temas académicos."},
        ]

        for datos in categorias_base:
            if not Category.query.filter_by(slug=datos["slug"]).first():
                db.session.add(Category(**datos))

        db.session.commit()

    app.run(debug=True)
