"""Pricing adapter boundary. The prototype ships only a deterministic, clearly SIMULATED adapter.

A live adapter (e.g. a liquidity-provider quote API) would implement the same `get_rate`
signature; conversion logic never knows where a rate came from beyond `rate_source`.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from sqlalchemy.orm import Session

from backend.config.settings import RATE_SOURCE
from backend.domain import errors
from backend.domain.support import display_name
from backend.models.entities import Account
from backend.repositories.records import PairRepository


@dataclass(frozen=True)
class RateQuote:
    rate: Decimal  # destination units per 1 source unit
    source: str


class PricingAdapter(Protocol):
    def get_rate(self, session: Session, source: Account, destination: Account) -> RateQuote: ...


class MockPricingAdapter:
    """Returns the deterministic rate seeded into `conversion_pairs`. Never calls a live market."""

    def get_rate(self, session: Session, source: Account, destination: Account) -> RateQuote:
        pair = PairRepository(session).find_enabled(
            source.asset_code, source.network_key, destination.asset_code, destination.network_key
        )
        if pair is None:
            raise errors.unsupported_pair(
                display_name(source.asset_code, source.network), display_name(destination.asset_code, destination.network)
            )
        return RateQuote(rate=Decimal(pair.simulated_rate), source=RATE_SOURCE)
