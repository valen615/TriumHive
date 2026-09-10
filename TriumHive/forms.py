"""
forms.py
--------
Formularios basados en Flask-WTF. Centralizar la validación aquí evita
lógica de validación duplicada o insegura en las rutas de app.py y
provee protección CSRF automática en cada formulario renderizado.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SelectField, BooleanField
from wtforms.validators import (
    DataRequired, Length, Email, EqualTo, Regexp, ValidationError
)

from models import User


class RegistroForm(FlaskForm):
    username = StringField(
        "Nombre de usuario",
        validators=[
            DataRequired(message="El nombre de usuario es obligatorio."),
            Length(min=3, max=30, message="Debe tener entre 3 y 30 caracteres."),
            Regexp(
                r"^[A-Za-z0-9_.]+$",
                message="Solo se permiten letras, números, puntos y guiones bajos.",
            ),
        ],
    )
    nombre_completo = StringField(
        "Nombre completo", validators=[DataRequired(), Length(max=120)]
    )
    grado_seccion = StringField("Grado y sección", validators=[Length(max=40)])
    email = StringField(
        "Correo institucional",
        validators=[DataRequired(), Email(message="Ingresa un correo válido.")],
    )
    password = PasswordField(
        "Contraseña",
        validators=[DataRequired(), Length(min=6, message="Mínimo 6 caracteres.")],
    )
    confirmar_password = PasswordField(
        "Confirmar contraseña",
        validators=[DataRequired(), EqualTo("password", message="Las contraseñas no coinciden.")],
    )

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError("Ese nombre de usuario ya está en uso.")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("Ya existe una cuenta registrada con ese correo.")


class LoginForm(FlaskForm):
    email = StringField("Correo institucional", validators=[DataRequired(), Email()])
    password = PasswordField("Contraseña", validators=[DataRequired()])
    recordarme = BooleanField("Mantener sesión iniciada")


class PostForm(FlaskForm):
    titulo = StringField(
        "Título",
        validators=[DataRequired(message="El título es obligatorio."), Length(max=150)],
    )
    categoria_id = SelectField("Categoría", coerce=int, validators=[DataRequired()])
    contenido = TextAreaField(
        "Contenido",
        validators=[DataRequired(message="Escribe el contenido de tu publicación."), Length(min=10)],
    )


class ComentarioForm(FlaskForm):
    contenido = TextAreaField(
        "Comentario",
        validators=[DataRequired(message="El comentario no puede estar vacío."), Length(max=500)],
    )
