"""Read-side queries for conversion transactions (history, detail, uncertain-outcome recovery).

Returns customer-facing data only; internal review cases and notifications are never included.
"""
from __future__ import annotations

from backend.db.database import Database
from backend.domain import errors
from backend.repositories.operations import EventRepository
from backend.repositories.records import TransactionRepository
from backend.schemas.serializers import transaction_out


class TransactionQueryService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get(self, customer_id: str, transaction_id: str) -> dict:
        with self.db.transaction() as s:
            txn = TransactionRepository(s).get_for_customer(transaction_id, customer_id)
            if txn is None:
                raise errors.transaction_not_found()
            return transaction_out(txn, EventRepository(s).last_at(txn.id))

    def get_by_idempotency_key(self, customer_id: str, key: str) -> dict:
        with self.db.transaction() as s:
            txn = TransactionRepository(s).get_by_key(customer_id, key)
            if txn is None:
                raise errors.transaction_not_found()
            return transaction_out(txn, EventRepository(s).last_at(txn.id))

    def list_recent(self, customer_id: str, limit: int = 50) -> list[dict]:
        with self.db.transaction() as s:
            events = EventRepository(s)
            return [transaction_out(t, events.last_at(t.id)) for t in TransactionRepository(s).list_recent(customer_id, limit)]
