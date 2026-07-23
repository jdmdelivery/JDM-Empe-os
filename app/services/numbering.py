"""Numeración de códigos de negocio."""

from __future__ import annotations

from datetime import datetime

from app.utils.datetime_utils import local_now


def _year() -> int:
    return local_now().year


def next_code(prefix: str, last_code: str | None) -> str:
    year = _year()
    seq = 1
    expected_prefix = f"{prefix}-{year}-"
    if last_code and last_code.startswith(expected_prefix):
        try:
            seq = int(last_code.split("-")[-1]) + 1
        except ValueError:
            seq = 1
    return f"{expected_prefix}{seq:06d}"


def next_customer_code(last_code: str | None) -> str:
    return next_code("CLI", last_code)


def next_deliverer_code(last_code: str | None) -> str:
    return next_code("ENT", last_code)


def next_item_code(last_code: str | None) -> str:
    return next_code("ART", last_code)