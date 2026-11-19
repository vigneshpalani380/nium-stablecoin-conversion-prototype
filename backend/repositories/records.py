"""Repositories for pairs, quotes, conversion transactions and idempotency records."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.models.entities import ConversionPair, ConversionQuote, ConversionTransaction, IdempotencyRecord


class PairRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def list_enabled(self) -> list[ConversionPair]:
        return list(self.s.scalars(select(ConversionPair).where(ConversionPair.enabled.is_(True)).order_by(ConversionPair.id)))

    def find_enabled(self, src_asset: str, src_net: str, dst_asset: str, dst_net: str) -> ConversionPair | None:
        return self.s.scalar(
            select(ConversionPair).where(
                ConversionPair.source_asset_code == src_asset,
                ConversionPair.source_network_key == src_net,
                ConversionPair.destination_asset_code == dst_asset,
                ConversionPair.destination_network_key == dst_net,
                ConversionPair.enabled.is_(True),
            )
        )


class QuoteRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def add(self, quote: ConversionQuote) -> None:
        self.s.add(quote)

    def get_for_customer(self, quote_id: str, customer_id: str) -> ConversionQuote | None:
        return self.s.scalar(
            select(ConversionQuote).where(ConversionQuote.id == quote_id, ConversionQuote.customer_id == customer_id)
        )

    def _transition(self, quote_id: str, guards: list, values: dict) -> bool:
        stmt = (
            update(ConversionQuote)
            .where(ConversionQuote.id == quote_id, *guards)
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        return self.s.execute(stmt).rowcount == 1

    def try_consume(self, quote_id: str, now: datetime) -> bool:
        """OPEN -> CONFIRMED only if still open and unexpired. Guarantees a quote is used once."""
        return self._transition(
            quote_id,
            [ConversionQuote.status == "OPEN", ConversionQuote.expires_at > now],
            {"status": "CONFIRMED"},
        )

    def mark_expired(self, quote_id: str) -> bool:
        return self._transition(quote_id, [ConversionQuote.status == "OPEN"], {"status": "EXPIRED"})

    def cancel(self, quote_id: str) -> bool:
        return self._transition(quote_id, [ConversionQuote.status == "OPEN"], {"status": "CANCELLED"})

    def force_expire(self, quote_id: str, now: datetime) -> bool:
        """Demo-only: move expiry into the past."""
        return self._transition(
            quote_id, [ConversionQuote.status == "OPEN"], {"expires_at": now - timedelta(seconds=1)}
        )


class TransactionRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def add(self, txn: ConversionTransaction) -> None:
        self.s.add(txn)

    def get(self, transaction_id: str) -> ConversionTransaction | None:
        return self.s.get(ConversionTransaction, transaction_id)

    def get_for_customer(self, transaction_id: str, customer_id: str) -> ConversionTransaction | None:
        return self.s.scalar(
            select(ConversionTransaction).where(
                ConversionTransaction.id == transaction_id, ConversionTransaction.customer_id == customer_id
            )
        )

    def get_by_key(self, customer_id: str, key: str) -> ConversionTransaction | None:
        return self.s.scalar(
            select(ConversionTransaction).where(
                ConversionTransaction.customer_id == customer_id, ConversionTransaction.idempotency_key == key
            )
        )

    def list_recent(self, customer_id: str, limit: int = 50) -> list[ConversionTransaction]:
        stmt = (
            select(ConversionTransaction)
            .where(ConversionTransaction.customer_id == customer_id)
            .order_by(ConversionTransaction.created_at.desc(), ConversionTransaction.id.desc())
            .limit(limit)
        )
        return list(self.s.scalars(stmt))

    def list_reserved_before(self, cutoff: datetime) -> list[str]:
        stmt = select(ConversionTransaction.id).where(
            ConversionTransaction.status == "RESERVED", ConversionTransaction.reserved_at <= cutoff
        )
        return list(self.s.scalars(stmt))

    def count(self) -> int:
        return self.s.scalar(select(func.count()).select_from(ConversionTransaction)) or 0


class IdempotencyRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def get(self, customer_id: str, key: str) -> IdempotencyRecord | None:
        return self.s.scalar(
            select(IdempotencyRecord).where(
                IdempotencyRecord.customer_id == customer_id, IdempotencyRecord.idempotency_key == key
            )
        )

    def add(self, record: IdempotencyRecord) -> None:
        self.s.add(record)
