"""Formularios de sucursales."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional


class BranchForm(FlaskForm):
    code = StringField(
        "Código",
        validators=[DataRequired(message="El código es obligatorio."), Length(max=30)],
    )
    name = StringField(
        "Nombre",
        validators=[DataRequired(message="El nombre es obligatorio."), Length(max=150)],
    )
    phone = StringField("Teléfono", validators=[Optional(), Length(max=30)])
    whatsapp = StringField("WhatsApp", validators=[Optional(), Length(max=30)])
    email = StringField("Correo", validators=[Optional(), Email(), Length(max=120)])
    address = StringField("Dirección", validators=[Optional(), Length(max=255)])
    sector = StringField("Sector", validators=[Optional(), Length(max=120)])
    city = StringField("Ciudad", validators=[Optional(), Length(max=120)])
    province = StringField("Provincia", validators=[Optional(), Length(max=120)])
    country = StringField(
        "País",
        default="República Dominicana",
        validators=[Optional(), Length(max=80)],
    )
    rnc = StringField("RNC", validators=[Optional(), Length(max=40)])
    is_active = BooleanField("Activa", default=True)
    is_main = BooleanField("Sucursal principal")
    notes = TextAreaField("Notas", validators=[Optional(), Length(max=2000)])
    submit = SubmitField("Guardar")