"""Formularios de persona que entrega."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import BooleanField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional  # DataRequired para customer_id


LEGITIMACY_DECLARATION = (
    "Declaro que soy propietario legítimo del artículo entregado o que cuento con "
    "autorización legal para entregarlo. Declaro que el artículo no es robado, no procede "
    "de actividades ilícitas y que toda la información suministrada es verdadera. Autorizo "
    "al negocio a conservar mis fotografías, documentos, firma y evidencias relacionadas "
    "con esta operación, conforme a las leyes aplicables."
)


class DelivererForm(FlaskForm):
    customer_id = SelectField("Cliente", coerce=int, validators=[DataRequired()])
    is_same_as_customer = BooleanField("El cliente es quien entrega")
    first_name = StringField("Nombres", validators=[Optional(), Length(max=100)])
    last_name = StringField("Apellidos", validators=[Optional(), Length(max=100)])
    national_id = StringField("Cédula", validators=[Optional(), Length(max=40)])
    passport = StringField("Pasaporte", validators=[Optional(), Length(max=40)])
    phone = StringField("Teléfono", validators=[Optional(), Length(max=30)])
    address = StringField("Dirección", validators=[Optional(), Length(max=255)])
    relationship_to_customer = StringField(
        "Relación con el cliente", validators=[Optional(), Length(max=120)]
    )
    delivery_reason = TextAreaField("Motivo de la entrega", validators=[Optional(), Length(max=2000)])
    photo = FileField(
        "Foto de la persona",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])],
    )
    document_front = FileField(
        "Foto frontal del documento",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])],
    )
    document_back = FileField(
        "Foto trasera del documento",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])],
    )
    holding_item_photo = FileField(
        "Foto sosteniendo el artículo",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])],
    )
    signature_data = TextAreaField("Firma digital", validators=[Optional()])
    legitimate_origin_accepted = BooleanField(
        "Acepto la declaración de procedencia legítima"
    )
    observations = TextAreaField("Observaciones", validators=[Optional(), Length(max=4000)])
    authorize_missing_photos = BooleanField("Autorizar continuar sin alguna fotografía")
    missing_photos_reason = TextAreaField("Motivo de excepción fotográfica", validators=[Optional()])
    submit = SubmitField("Guardar persona que entrega")