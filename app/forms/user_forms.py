"""Formularios de usuarios."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError


class UserForm(FlaskForm):
    username = StringField(
        "Usuario",
        validators=[DataRequired(message="El usuario es obligatorio."), Length(max=80)],
    )
    email = StringField(
        "Correo",
        validators=[
            DataRequired(message="El correo es obligatorio."),
            Email(message="Correo no válido."),
            Length(max=120),
        ],
    )
    first_name = StringField(
        "Nombres",
        validators=[DataRequired(message="Los nombres son obligatorios."), Length(max=100)],
    )
    last_name = StringField(
        "Apellidos",
        validators=[DataRequired(message="Los apellidos son obligatorios."), Length(max=100)],
    )
    phone = StringField("Teléfono", validators=[Optional(), Length(max=30)])
    role_id = SelectField(
        "Rol",
        coerce=int,
        validators=[DataRequired(message="Seleccione un rol.")],
    )
    branch_id = SelectField("Sucursal", coerce=int, validators=[Optional()], default=0)
    password = PasswordField("Contraseña", validators=[Optional(), Length(min=8)])
    password2 = PasswordField(
        "Confirmar contraseña",
        validators=[EqualTo("password", message="Las contraseñas no coinciden.")],
    )
    account_active = BooleanField("Activo", default=True)
    must_change_password = BooleanField("Debe cambiar contraseña", default=True)
    notes = TextAreaField("Notas", validators=[Optional(), Length(max=2000)])
    submit = SubmitField("Guardar")

    def validate_password(self, field):  # type: ignore[no-untyped-def]
        # En creación se exige contraseña; en edición puede quedar vacía.
        if getattr(self, "_require_password", False) and not field.data:
            raise ValidationError("La contraseña es obligatoria.")


class ProfilePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Contraseña actual",
        validators=[DataRequired(message="Ingrese su contraseña actual.")],
    )
    password = PasswordField(
        "Nueva contraseña",
        validators=[DataRequired(), Length(min=8, message="Mínimo 8 caracteres.")],
    )
    password2 = PasswordField(
        "Confirmar contraseña",
        validators=[DataRequired(), EqualTo("password", message="Las contraseñas no coinciden.")],
    )
    submit = SubmitField("Cambiar contraseña")