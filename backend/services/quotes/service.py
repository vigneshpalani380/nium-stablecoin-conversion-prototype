"""Quote service: validates the request and persists a priced quote. Never moves balances."""
from __future__ import annotations

from datetime import timedelta

from backend.adapters.pricing.mock import PricingAdapter
from backend.config.settings import Settings
from backend.db.database import Database
from backend.domain import errors
from backend.domain.money import format_minor, parse_amount, to_minor
from backend.domain.support import display_name, log_event, new_id
from backend.models.entities import ConversionQuote
from backend.repositories.accounts import AccountRepository
from backend.repositories.records import PairRepository, QuoteRepository
from backend.services.quotes.calculator import calculate_quote


class QuoteService:
    def __init__(self, db: Database, clock, settings: Settings, pricing: PricingAdapter) -> None:
        self.db = db
        self.clock = clock
        self.settings = settings
        self.pricing = pricing

    def create(self, customer_id: str, source_account_id: str, destination_account_id: str, gross_raw: object) -> ConversionQuote:
        if source_account_id == destination_account_id:
            raise errors.same_account()
        with self.db.transaction() as s:
            accounts = AccountRepository(s)
            src = accounts.get_for_customer(source_account_id, customer_id)
            if src is None:
                raise errors.account_not_found(source_account_id)
            dst = accounts.get_for_customer(destination_account_id, customer_id)
            if dst is None:
                raise errors.account_not_found(destination_account_id)
            if src.status != "ACTIVE" or dst.status != "ACTIVE":
                raise errors.account_inactive()
            if PairRepository(s).find_enabled(src.asset_code, src.network_key, dst.asset_code, dst.network_key) is None:
                raise errors.unsupported_pair(
                    display_name(src.asset_code, src.network), display_name(dst.asset_code, dst.network)
                )

            gross = parse_amount(gross_raw, src.precision)
            rate = self.pricing.get_rate(s, src, dst)
            calc = calculate_quote(gross, self.settings.fee_rate, rate.rate, src.precision, dst.precision)
            if calc.destination <= 0:
                raise errors.amount_too_small()

            gross_minor = to_minor(gross, src.precision)
            available = accounts.snapshot(src.id).available
            if available < gross_minor:
                raise errors.insufficient_balance(format_minor(available, src.precision), display_name(src.asset_code, src.network))

            now = self.clock.now()
            quote = ConversionQuote(
                id=new_id("q"),
                customer_id=customer_id,
                source_account_id=src.id,
                destination_account_id=dst.id,
                source_precision=src.precision,
                destination_precision=dst.precision,
                gross_source_minor=gross_minor,
                fee_rate=str(self.settings.fee_rate),
                fee_minor=to_minor(calc.fee, src.precision),
                fee_currency=src.asset_code,
                net_source_minor=to_minor(calc.net_source, src.precision),
                exchange_rate=str(rate.rate),
                destination_minor=to_minor(calc.destination, dst.precision),
                rate_source=rate.source,
                created_at=now,
                expires_at=now + timedelta(seconds=self.settings.quote_ttl_seconds),
                status="OPEN",
            )
            QuoteRepository(s).add(quote)
        log_event("quote.created", customer=customer_id, quote=quote.id, source=src.id, destination=dst.id)
        return quote

    def get(self, customer_id: str, quote_id: str) -> ConversionQuote:
        with self.db.transaction() as s:
            quote = QuoteRepository(s).get_for_customer(quote_id, customer_id)
        if quote is None:
            raise errors.quote_not_found(quote_id)
        return quote

    def cancel(self, customer_id: str, quote_id: str) -> ConversionQuote:
        with self.db.transaction() as s:
            repo = QuoteRepository(s)
            quote = repo.get_for_customer(quote_id, customer_id)
            if quote is None:
                raise errors.quote_not_found(quote_id)
            if quote.status == "CONFIRMED":
                raise errors.quote_already_used()
            repo.cancel(quote_id)  # no-op if already expired/cancelled
        quote = self.get(customer_id, quote_id)
        log_event("quote.cancelled", customer=customer_id, quote=quote_id, status=quote.status)
        return quote
