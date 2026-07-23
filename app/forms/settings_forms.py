"""Formularios de configuración."""

from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, SubmitField, DecimalField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional


class BusinessSettingsForm(FlaskForm):
    business_name = StringField(
        "Nombre del negocio",
        validators=[DataRequired(), Length(max=150)],
    )
    business_rnc = StringField("RNC", validators=[Optional(), Length(max=40)])
    business_phone = StringField("Teléfono", validators=[Optional(), Length(max=30)])
    business_whatsapp = StringField("WhatsApp", validators=[Optional(), Length(max=30)])
    business_email = StringField("Correo", validators=[Optional(), Email(), Length(max=120)])
    business_address = StringField("Dirección", validators=[Optional(), Length(max=255)])
    currency_symbol = StringField(
        "Símbolo de moneda",
        default="RD$",
        validators=[DataRequired(), Length(max=10)],
    )
    timezone = StringField(
        "Zona horaria",
        default="America/Santo_Domingo",
        validators=[DataRequired(), Length(max=80)],
    )
    default_interest_percent = DecimalField(
        "Porcentaje de interés predeterminado",
        places=2,
        validators=[DataRequired(), NumberRange(min=0, max=100)],
    )
    default_grace_days = IntegerField(
        "Días de gracia",
        validators=[DataRequired(), NumberRange(min=0, max=365)],
    )
    default_duration_days = IntegerField(
        "Duración predeterminada (días)",
        validators=[DataRequired(), NumberRange(min=1, max=3650)],
    )
    submit = SubmitField("Guardar configuración")