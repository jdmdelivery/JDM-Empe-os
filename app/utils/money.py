"""Utilidades monetarias con Decimal (nunca float)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

TWOPLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def to_decimal(value: Any, default: Decimal = ZERO) -> Decimal:
    if value is None or value == "":
        return default
    if isinstance(value, Decimal):
        return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    try:
        return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return default


def money_add(*values: Any) -> Decimal:
    total = ZERO
    for value in values:
        total += to_decimal(value)
    return total.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def money_sub(a: Any, b: Any) -> Decimal:
    return (to_decimal(a) - to_decimal(b)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def percent_of(amount: Any, percent: Any) -> Decimal:
    """Calcula (amount * percent) / 100 con Decimal."""
    result = (to_decimal(amount) * to_decimal(percent)) / Decimal("100")
    return result.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def format_money(amount: Any, symbol: str = "RD$") -> str:
    value = to_decimal(amount)
    sign = "-" if value < 0 else ""
    absolute = abs(value)
    formatted = f"{absolute:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sign}{symbol}{formatted}"