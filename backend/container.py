"""Wires settings, database, clock, pricing adapter and demo faults into services."""
from __future__ import annotations

from dataclasses import dataclass, field

from backend.adapters.pricing.mock import MockPricingAdapter, PricingAdapter
from backend.config.settings import Settings
from backend.db.database import Database
from backend.domain.support import DemoFaults
from backend.services.conversions.service import ConversionService
from backend.services.operations.review import ReviewService
from backend.services.quotes.service import QuoteService
from backend.services.transactions.service import TransactionQueryService


@dataclass
class Container:
    settings: Settings
    db: Database
    clock: object
    pricing: PricingAdapter = field(default_factory=MockPricingAdapter)
    faults: DemoFaults = field(default_factory=DemoFaults)

    def quotes(self) -> QuoteService:
        return QuoteService(self.db, self.clock, self.settings, self.pricing)

    def conversions(self) -> ConversionService:
        return ConversionService(self.db, self.clock, self.faults)

    def transactions(self) -> TransactionQueryService:
        return TransactionQueryService(self.db)

    def reviews(self) -> ReviewService:
        return ReviewService(self.db, self.clock, self.conversions())
