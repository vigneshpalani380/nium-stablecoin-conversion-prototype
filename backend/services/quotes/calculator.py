"""Pure quote arithmetic (prototype convention, see 00_MASTER_PRD §8).

fee = gross × fee_rate, rounded to source precision (fee in source currency)
net = gross − fee
destination = net × rate, rounded to destination precision
Rounding: ROUND_HALF_UP.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext

from backend.domain.money import ROUNDING, quantum


@dataclass(frozen=True)
class QuoteCalculation:
    gross_source: Decimal
    fee: Decimal
    net_source: Decimal
    rate: Decimal
    destination: Decimal


def calculate_quote(
    gross_source: Decimal, fee_rate: Decimal, rate: Decimal, source_precision: int, destination_precision: int
) -> QuoteCalculation:
    with localcontext() as ctx:
        ctx.prec = 50
        fee = (gross_source * fee_rate).quantize(quantum(source_precision), rounding=ROUNDING)
        net = gross_source - fee
        destination = (net * rate).quantize(quantum(destination_precision), rounding=ROUNDING)
    return QuoteCalculation(gross_source=gross_source, fee=fee, net_source=net, rate=rate, destination=destination)
