"""Generación de PDF y códigos QR."""

from __future__ import annotations

import io
from pathlib import Path

import qrcode
from flask import current_app
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.utils.money import format_money


def generate_qr_png(data: str, filename: str | None = None) -> Path:
    root = Path(current_app.config["UPLOAD_FOLDER"]) / "qr"
    root.mkdir(parents=True, exist_ok=True)
    name = filename or "qr.png"
    path = root / name
    img = qrcode.make(data)
    img.save(path)
    return path


def build_pawn_contract_pdf(contract, business_name: str = "JDM Empeños") -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 20 * mm

    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, y, business_name)
    y -= 8 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, f"Contrato de empeño {contract.contract_number}")
    y -= 10 * mm
    c.setFont("Helvetica", 10)
    lines = [
        f"Cliente: {contract.customer.full_name if contract.customer else ''}",
        f"Cédula: {contract.customer.national_id if contract.customer else ''}",
        f"Quien entrega: {contract.deliverer.full_name if contract.deliverer else ''}",
        f"Artículo: {contract.item.code if contract.item else ''} "
        f"{getattr(contract.item, 'brand', '') or ''} {getattr(contract.item, 'model', '') or ''}",
        f"Serie: {getattr(contract.item, 'serial_number', None) or '—'}",
        f"IMEI: {getattr(contract.item, 'imei', None) or '—'}",
        f"Capital: {format_money(contract.capital)}",
        f"Porcentaje: {contract.percent}% ({contract.interest_type})",
        f"Interés: {format_money(contract.interest_amount)}",
        f"Cargos: {format_money(contract.fees_amount)}",
        f"Total: {format_money(contract.total_due)}",
        f"Inicio: {contract.start_date}",
        f"Vencimiento: {contract.due_date}",
        f"Días de gracia: {contract.grace_days}",
    ]
    for line in lines:
        c.drawString(20 * mm, y, line)
        y -= 6 * mm

    y -= 8 * mm
    c.drawString(20 * mm, y, "Firma del cliente / quien entrega: ______________________")
    y -= 8 * mm
    c.drawString(20 * mm, y, "Firma del empleado: ______________________")
    y -= 12 * mm
    c.setFont("Helvetica", 8)
    c.drawString(
        20 * mm,
        y,
        "Este contrato conserva el porcentaje y reglas originales (snapshot). Moneda: RD$.",
    )
    c.showPage()
    c.save()
    return buffer.getvalue()


def build_receipt_pdf(title: str, lines: list[str], business_name: str = "JDM Empeños") -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(80 * mm, 200 * mm))
    y = 190 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(5 * mm, y, business_name)
    y -= 6 * mm
    c.setFont("Helvetica-Bold", 9)
    c.drawString(5 * mm, y, title)
    y -= 8 * mm
    c.setFont("Helvetica", 8)
    for line in lines:
        c.drawString(5 * mm, y, line[:42])
        y -= 5 * mm
        if y < 10 * mm:
            c.showPage()
            y = 190 * mm
    c.showPage()
    c.save()
    return buffer.getvalue()


def build_ticket_58mm_pdf(contract, business_name: str = "JDM Empeños") -> bytes:
    """Recibo térmico 58 mm de ancho."""
    width = 58 * mm
    height = 180 * mm
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(width, height))
    y = height - 6 * mm
    left = 3 * mm

    def line(text: str, *, bold: bool = False, size: int = 8):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(left, y, text[:34])
        y -= 4.2 * mm

    line(business_name, bold=True, size=9)
    line("RECIBO DE EMPEÑO", bold=True)
    line(f"#{contract.contract_number}", bold=True)
    line("-" * 28)
    cust = contract.customer
    item = contract.item
    line(f"Cliente: {cust.full_name if cust else '-'}")
    line(f"ID/Cedula: {cust.national_id if cust else '-'}")
    line(f"Tel: {cust.phone_primary if cust else '-'}")
    if item:
        cat = item.category.name if item.category else ""
        line(f"Tipo: {cat}")
        line(f"Art: {item.brand or ''} {item.model or ''}".strip() or item.code)
        line(f"Codigo: {item.code}")
    line("-" * 28)
    line(f"Capital: {format_money(contract.capital)}")
    line(f"Interes: {format_money(contract.interest_amount)} ({contract.percent}%)")
    line(f"Total: {format_money(contract.total_due)}", bold=True)
    line(f"Inicio: {contract.start_date}")
    line(f"Vence: {contract.due_date}")
    line("-" * 28)
    line("Gracias por su preferencia")
    c.showPage()
    c.save()
    return buffer.getvalue()