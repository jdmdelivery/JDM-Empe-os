"""Formularios de artículos y categorías."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    BooleanField,
    DecimalField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class ItemForm(FlaskForm):
    category_id = SelectField("Categoría", coerce=int, validators=[DataRequired()])
    customer_id = SelectField("Cliente", coerce=int, validators=[Optional()])
    deliverer_id = SelectField("Persona que entrega", coerce=int, validators=[Optional()])
    brand = StringField("Marca", validators=[Optional(), Length(max=100)])
    model = StringField("Modelo", validators=[Optional(), Length(max=120)])
    serial_number = StringField("Número de serie", validators=[Optional(), Length(max=120)])
    imei = StringField("IMEI", validators=[Optional(), Length(max=40)])
    chassis_number = StringField("Chasis", validators=[Optional(), Length(max=80)])
    plate_number = StringField("Matrícula / placa", validators=[Optional(), Length(max=40)])
    color = StringField("Color", validators=[Optional(), Length(max=60)])
    year = IntegerField("Año", validators=[Optional(), NumberRange(min=1900, max=2100)])
    description = TextAreaField("Descripción", validators=[Optional(), Length(max=4000)])
    physical_condition = StringField("Estado físico", validators=[Optional(), Length(max=80)])
    functional_condition = StringField("Estado funcional", validators=[Optional(), Length(max=80)])
    damages = TextAreaField("Daños", validators=[Optional(), Length(max=2000)])
    scratches = TextAreaField("Rayones", validators=[Optional(), Length(max=2000)])
    missing_parts = TextAreaField("Piezas faltantes", validators=[Optional(), Length(max=2000)])
    accessories = TextAreaField("Accesorios incluidos", validators=[Optional(), Length(max=2000)])
    estimated_value = DecimalField("Valor estimado", places=2, validators=[Optional()])
    purchase_price = DecimalField("Precio de compra", places=2, validators=[Optional()])
    loan_amount = DecimalField("Monto prestado", places=2, validators=[Optional()])
    min_sale_price = DecimalField("Precio mínimo de venta", places=2, validators=[Optional()])
    sale_price = DecimalField("Precio normal de venta", places=2, validators=[Optional()])
    location = StringField("Ubicación física", validators=[Optional(), Length(max=120)])
    shelf = StringField("Estante", validators=[Optional(), Length(max=60)])
    warehouse = StringField("Almacén", validators=[Optional(), Length(max=120)])
    status = SelectField(
        "Estado",
        choices=[
            ("en_evaluacion", "En evaluación"),
            ("pendiente_documentacion", "Pendiente de documentación"),
            ("empenado", "Empeñado"),
            ("disponible_venta", "Disponible para venta"),
            ("bloqueado", "Bloqueado"),
            ("en_reparacion", "En reparación"),
        ],
        default="en_evaluacion",
    )
    observations = TextAreaField("Observaciones", validators=[Optional(), Length(max=4000)])
    photo_general = FileField(
        "Foto general", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])]
    )
    photo_front = FileField(
        "Foto frontal", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])]
    )
    photo_back = FileField(
        "Foto trasera", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])]
    )
    photo_serial = FileField(
        "Foto número de serie",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])],
    )
    photo_imei = FileField(
        "Foto IMEI", validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"])]
    )
    authorize_duplicate = BooleanField("Autorizar serie/IMEI/chasis/placa duplicados")
    duplicate_reason = TextAreaField("Motivo de autorización de duplicado", validators=[Optional()])
    submit = SubmitField("Guardar artículo")


class ItemSearchForm(FlaskForm):
    q = StringField("Buscar", validators=[Optional(), Length(max=120)])
    status = SelectField("Estado", choices=[("", "Todos")], default="")
    category_id = SelectField("Categoría", coerce=int, choices=[], default=0)
    submit = SubmitField("Buscar")