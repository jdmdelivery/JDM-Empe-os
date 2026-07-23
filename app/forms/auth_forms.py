"""Formularios de autenticación."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class LoginForm(FlaskForm):
    username = StringField(
        "Usuario o correo",
        validators=[DataRequired(message="Ingrese su usuario o correo."), Length(max=120)],
    )
    password = PasswordField(
        "Contraseña",
        validators=[DataRequired(message="Ingrese su contraseña.")],
    )
    remember = BooleanField("Recordarme")
    submit = SubmitField("Iniciar sesión")


class ForgotPasswordForm(FlaskForm):
    email = StringField(
        "Correo electrónico",
        validators=[
            DataRequired(message="Ingrese su correo."),
            Email(message="Correo no válido."),
            Length(max=120),
        ],
    )
    submit = SubmitField("Enviar enlace")


class ResetPasswordForm(FlaskForm):
    password = PasswordField(
        "Nueva contraseña",
        validators=[
            DataRequired(message="Ingrese la nueva contraseña."),
            Length(min=8, message="Mínimo 8 caracteres."),
        ],
    )
    password2 = PasswordField(
        "Confirmar contraseña",
        validators=[
            DataRequired(message="Confirme la contraseña."),
            EqualTo("password", message="Las contraseñas no coinciden."),
        ],
    )
    submit = SubmitField("Actualizar contraseña")