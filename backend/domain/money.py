"""Exact money handling. Decimal in code, integer minor units in the database. Never float."""
from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal

from backend.domain import errors

ROUNDING = ROUND_HALF_UP

# Digits with an optional fractional part. No sign, exponent or thousands separators.
# Max 12 integer digits keeps minor units well inside a signed 64-bit integer.
_AMOUNT_RE = re.compile(r"^\d{1,12}(\.\d+)?$")


def quantum(precision: int) -> Decimal:
    return Decimal(1).scaleb(-precision)


def parse_amount(raw: object, precision: int) -> Decimal:
    """Parse a user-supplied decimal string; reject non-positive, malformed and over-precise values."""
    if not isinstance(raw, str):
        raise errors.invalid_amount()
    text = raw.strip()
    if not _AMOUNT_RE.match(text):
        raise errors.invalid_amount()
    value = Decimal(text)
    if value <= 0:
        raise errors.invalid_amount()
    q = quantum(precision)
    if value != value.quantize(q):
        raise errors.precision_exceeded(precision)
    return value.quantize(q)


def to_minor(value: Decimal, precision: int) -> int:
    scaled = value.scaleb(precision)
    if scaled != scaled.to_integral_value():
        raise ValueError(f"{value} has more than {precision} decimal places")
    return int(scaled)


def from_minor(minor: int, precision: int) -> Decimal:
    return Decimal(minor).scaleb(-precision).quantize(quantum(precision))


def format_minor(minor: int | None, precision: int) -> str | None:
    if minor is None:
        return None
    return format(from_minor(minor, precision), "f")
