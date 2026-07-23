"""Cálculos financieros con Decimal (nunca float)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Sequence

from app.utils.money import ZERO, money_add, money_sub, percent_of, to_decimal


DEFAULT_PAYMENT_ORDER = ("mora", "cargos", "interes", "capital")


@dataclass
class InterestBreakdown:
    capital: Decimal
    percent: Decimal
    interest_type: str
    interest: Decimal
    fees: Decimal
    late_fee: Decimal
    discounts: Decimal
    total: Decimal
    grace_days: int
    due_date: date | None


@dataclass
class AllocationResult:
    applied: dict[str, Decimal]
    remaining_payment: Decimal
    new_balances: dict[str, Decimal]


def calculate_interest(
    capital: Any,
    percent: Any,
    *,
    interest_type: str = "simple_mensual",
    periods: int = 1,
    fixed_fee: Any = 0,
) -> Decimal:
    capital_d = to_decimal(capital)
    percent_d = to_decimal(percent)
    periods = max(int(periods or 1), 1)
    fee = to_decimal(fixed_fee)

    if interest_type == "cargo_fijo":
        return fee
    if interest_type == "porcentaje_mas_cargo":
        return money_add(percent_of(capital_d, percent_d) * periods, fee)
    if interest_type == "compuesto":
        # Desactivado por defecto en UI; implementación conservadora.
        amount = capital_d
        rate = percent_d / Decimal("100")
        for _ in range(periods):
            amount = (amount * (Decimal("1") + rate)).quantize(Decimal("0.01"))
        return money_sub(amount, capital_d)
    # simple / fijo / diario / semanal / quincenal / mensual / periodo
    return money_add(percent_of(capital_d, percent_d) * periods, fee)


def calculate_late_fee(
    capital: Any,
    *,
    late_percent: Any = 0,
    late_fixed: Any = 0,
    days_late: int = 0,
    mode: str = "mensual",
) -> Decimal:
    if days_late <= 0:
        return ZERO
    capital_d = to_decimal(capital)
    late_percent_d = to_decimal(late_percent)
    late_fixed_d = to_decimal(late_fixed)
    if mode == "diario":
        return money_add(percent_of(capital_d, late_percent_d) * days_late, late_fixed_d)
    if mode == "semanal":
        weeks = max((days_late + 6) // 7, 1)
        return money_add(percent_of(capital_d, late_percent_d) * weeks, late_fixed_d)
    # mensual / periodo
    return money_add(percent_of(capital_d, late_percent_d), late_fixed_d)


def build_breakdown(
    *,
    capital: Any,
    percent: Any,
    interest_type: str = "simple_mensual",
    periods: int = 1,
    fixed_fee: Any = 0,
    late_fee: Any = 0,
    other_fees: Any = 0,
    discounts: Any = 0,
    grace_days: int = 0,
    start_date: date | None = None,
    duration_days: int = 30,
) -> InterestBreakdown:
    interest = calculate_interest(
        capital, percent, interest_type=interest_type, periods=periods, fixed_fee=0
    )
    fees = money_add(fixed_fee, other_fees)
    late = to_decimal(late_fee)
    disc = to_decimal(discounts)
    total = money_sub(money_add(capital, interest, fees, late), disc)
    due = None
    if start_date is not None:
        due = start_date + timedelta(days=int(duration_days or 30))
    return InterestBreakdown(
        capital=to_decimal(capital),
        percent=to_decimal(percent),
        interest_type=interest_type,
        interest=interest,
        fees=fees,
        late_fee=late,
        discounts=disc,
        total=total,
        grace_days=int(grace_days or 0),
        due_date=due,
    )


def allocate_payment(
    amount: Any,
    balances: dict[str, Any],
    order: Sequence[str] | None = None,
) -> AllocationResult:
    """Aplica pago en orden configurable: mora → cargos → interés → capital."""
    remaining = to_decimal(amount)
    applied: dict[str, Decimal] = {}
    new_balances: dict[str, Decimal] = {
        key: to_decimal(value) for key, value in balances.items()
    }
    for key in order or DEFAULT_PAYMENT_ORDER:
        balance = to_decimal(new_balances.get(key, ZERO))
        if remaining <= ZERO or balance <= ZERO:
            applied[key] = ZERO
            continue
        use = min(remaining, balance)
        applied[key] = use
        new_balances[key] = money_sub(balance, use)
        remaining = money_sub(remaining, use)
    return AllocationResult(applied=applied, remaining_payment=remaining, new_balances=new_balances)


def days_between(start: date | datetime, end: date | datetime) -> int:
    s = start.date() if isinstance(start, datetime) else start
    e = end.date() if isinstance(end, datetime) else end
    return (e - s).days


def role_percent_limit(role_code: str | None) -> Decimal | None:
    """None = sin límite (superadmin o llamada sin contexto de usuario)."""
    if not role_code:
        return None
    limits = {
        "cashier": Decimal("12.00"),
        "admin": Decimal("25.00"),
        "auditor": Decimal("0.00"),
        "superadmin": None,
    }
    return limits.get(role_code, Decimal("12.00"))
