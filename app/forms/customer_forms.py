"""Formularios de clientes."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, Length, Optional


class CustomerForm(FlaskForm):
    first_name = StringField("Nombres", validators=[DataRequired(), Length(max=100)])
    last_name = StringField("Apellidos", validators=[DataRequired(), Length(max=100)])
    national_id = StringField("Cédula", validators=[DataRequired(), Length(max=40)])
    passport = StringField("Pasaporte", validators=[Optional(), Length(max=40)])
    other_document = StringField("Otro documento", validators=[Optional(), Length(max=60)])
    birth_date = DateField("Fecha de nacimiento", validators=[Optional()])
    phone_primary = StringField("Teléfono principal", validators=[DataRequired(), Length(max=30)])
    phone_secondary = StringField("Teléfono alternativo", validators=[Optional(), Length(max=30)])
    whatsapp = StringField("WhatsApp", validators=[Optional(), Length(max=30)])
    email = StringField("Correo", validators=[Optional(), Email(), Length(max=120)])
    address = StringField("Dirección", validators=[Optional(), Length(max=255)])
    sector = StringField("Sector", validators=[Optional(), Length(max=120)])
    city = StringField("Ciudad", validators=[Optional(), Length(max=120)])
    province = StringField("Provincia", validators=[Optional(), Length(max=120)])
    country = StringField(
        "País", default="República Dominicana", validators=[Optional(), Length(max=80)]
    )
    occupation = StringField("Ocupación", validators=[Optional(), Length(max=120)])
    workplace = StringField("Lugar de trabajo", validators=[Optional(), Length(max=150)])
    approximate_income = DecimalField("Ingresos aproximados", places=2, validators=[Optional()])
    reference_name = StringField("Contacto de referencia", validators=[Optional(), Length(max=150)])
    reference_phone = StringField("Teléfono de referencia", validators=[Optional(), Length(max=30)])
    status = SelectField(
        "Estado",
        choices=[
            ("activo", "Activo"),
            ("bloqueado", "Bloqueado"),
            ("restringido", "Restringido"),
            ("en_revision", "En revisión"),
            ("inactivo", "Inactivo"),
        ],
        default="activo",
    )
    internal_notes = TextAreaField("Notas internas", validators=[Optional(), Length(max=4000)])
    photo = FileField("Foto del cliente", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])])
    document_front = FileField(
        "Foto frontal del documento",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])],
    )
    document_back = FileField(
        "Foto trasera del documento",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])],
    )
    signature_data = TextAreaField("Firma digital (data URL)", validators=[Optional()])
    authorize_duplicate = BooleanField("Autorizar cédula duplicada")
    duplicate_reason = TextAreaField("Motivo de autorización de duplicado", validators=[Optional()])
    submit = SubmitField("Guardar cliente")


class CustomerSearchForm(FlaskForm):
    q = StringField("Buscar", validators=[Optional(), Length(max=120)])
    status = SelectField(
        "Estado",
        choices=[
            ("", "Todos"),
            ("activo", "Activo"),
            ("bloqueado", "Bloqueado"),
            ("restringido", "Restringido"),
            ("en_revision", "En revisión"),
            ("inactivo", "Inactivo"),
        ],
        default="",
    )
    submit = SubmitField("Buscar")