"""Formularios de empeños, pagos y renovaciones."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import BooleanField, DecimalField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Optional


class PawnContractForm(FlaskForm):
    customer_id = SelectField("Cliente", coerce=int, validators=[DataRequired()])
    same_as_customer = BooleanField("Quien entrega es el mismo cliente", default=True)
    deliverer_id = SelectField("Persona que entrega", coerce=int, validators=[Optional()])
    category_id = SelectField("Tipo de artículo", coerce=int, validators=[Optional()])
    item_brand = StringField("Marca / nombre", validators=[Optional()])
    item_model = StringField("Modelo / detalle", validators=[Optional()])
    item_weight = DecimalField("Peso (g)", places=2, validators=[Optional()])
    item_serial = StringField("Serial / IMEI (opcional)", validators=[Optional()])
    item_photo = FileField(
        "Foto del artículo",
        validators=[Optional(), FileAllowed(["jpg", "jpeg", "png", "webp"], "Solo imágenes")],
    )
    item_id = SelectField(
        "Usar artículo ya registrado (opcional)",
        coerce=int,
        validators=[Optional()],
    )
    capital = DecimalField("Monto prestado", places=2, validators=[DataRequired(), NumberRange(min=1)])
    percent = DecimalField("Porcentaje", places=2, validators=[DataRequired(), NumberRange(min=0)])
    interest_type = SelectField(
        "Tipo de interés",
        choices=[
            ("simple_mensual", "Interés simple mensual"),
            ("fijo", "Interés fijo"),
            ("diario", "Interés diario"),
            ("semanal", "Interés semanal"),
            ("quincenal", "Interés quincenal"),
            ("mensual", "Interés mensual"),
            ("periodo", "Interés por período"),
            ("cargo_fijo", "Cargo fijo"),
            ("porcentaje_mas_cargo", "Porcentaje + cargo fijo"),
            ("compuesto", "Interés compuesto (desactivado por defecto)"),
        ],
        default="simple_mensual",
    )
    duration_days = IntegerField("Duración (días)", default=30, validators=[DataRequired(), NumberRange(min=1)])
    grace_days = IntegerField("Días de gracia", default=3, validators=[DataRequired(), NumberRange(min=0)])
    fees_amount = DecimalField("Cargos", places=2, default=0, validators=[Optional()])
    late_percent = DecimalField("Mora %", places=2, default=0, validators=[Optional()])
    late_fixed = DecimalField("Mora fija", places=2, default=0, validators=[Optional()])
    late_mode = SelectField(
        "Modo mora",
        choices=[("mensual", "Mensual"), ("diario", "Diaria"), ("semanal", "Semanal")],
        default="mensual",
    )
    percent_manual = BooleanField("Porcentaje manual")
    percent_change_reason = TextAreaField("Motivo del porcentaje manual", validators=[Optional()])
    conditions = TextAreaField("Condiciones", validators=[Optional()])
    observations = TextAreaField("Observaciones", validators=[Optional()])
    declaration_accepted = BooleanField("Acepto declaración y términos")
    submit = SubmitField("Crear contrato")


class PaymentForm(FlaskForm):
    contract_id = SelectField("Contrato", coerce=int, validators=[DataRequired()])
    amount = DecimalField("Monto recibido", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    method = SelectField(
        "Método",
        choices=[
            ("efectivo", "Efectivo"),
            ("tarjeta", "Tarjeta"),
            ("transferencia", "Transferencia"),
            ("deposito", "Depósito"),
            ("cheque", "Cheque"),
            ("mixto", "Pago mixto"),
        ],
        default="efectivo",
    )
    payment_type = SelectField(
        "¿Qué desea pagar?",
        choices=[
            ("interes", "Solo interés"),
            ("abono", "Abonar a capital"),
            ("auto", "Automático (mora → cargos → interés → capital)"),
            ("mora", "Solo mora"),
            ("total", "Liquidar / pago total"),
        ],
        default="interes",
    )
    payer_name = StringField("Persona que paga", validators=[Optional()])
    notes = TextAreaField("Notas", validators=[Optional()])
    signature_data = TextAreaField("Firma del cliente", validators=[Optional()])
    idempotency_key = StringField("Clave de idempotencia", validators=[Optional()])
    submit = SubmitField("Registrar pago")


class RenewalForm(FlaskForm):
    contract_id = SelectField("Contrato", coerce=int, validators=[DataRequired()])
    amount = DecimalField("Monto a pagar", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    method = SelectField(
        "Método",
        choices=[("efectivo", "Efectivo"), ("transferencia", "Transferencia"), ("tarjeta", "Tarjeta")],
        default="efectivo",
    )
    submit = SubmitField("Renovar")


class AuthorizeExpiredForm(FlaskForm):
    reason = TextAreaField("Motivo de autorización", validators=[DataRequired()])
    submit = SubmitField("Autorizar para inventario")