"""Account persistence. All balance changes are single conditional UPDATE statements.

The WHERE clause carries the guard (e.g. `available_minor >= amount`), so the check and the
change happen atomically in the database. rowcount == 0 means the guard failed and nothing changed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.models.entities import Account


@dataclass(frozen=True)
class BalanceSnapshot:
    available: int
    reserved: int
    pending: int


class AccountRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def list_for_customer(self, customer_id: str) -> list[Account]:
        stmt = select(Account).where(Account.customer_id == customer_id).order_by(Account.sort_order, Account.id)
        return list(self.s.scalars(stmt))

    def get_for_customer(self, account_id: str, customer_id: str) -> Account | None:
        return self.s.scalar(select(Account).where(Account.id == account_id, Account.customer_id == customer_id))

    def snapshot(self, account_id: str) -> BalanceSnapshot:
        row = self.s.execute(
            select(Account.available_minor, Account.reserved_minor, Account.pending_minor).where(Account.id == account_id)
        ).one()
        return BalanceSnapshot(*row)

    def _guarded_update(self, account_id: str, guards: list, values: dict, now: datetime) -> bool:
        stmt = (
            update(Account)
            .where(Account.id == account_id, *guards)
            .values(**values, version=Account.version + 1, updated_at=now)
            .execution_options(synchronize_session=False)
        )
        return self.s.execute(stmt).rowcount == 1

    # --- conversion lifecycle -------------------------------------------------------------
    def try_reserve(self, account_id: str, amount: int, now: datetime) -> bool:
        """Atomic check-and-reserve: available -> reserved only if available >= amount."""
        return self._guarded_update(
            account_id,
            [Account.available_minor >= amount, Account.status == "ACTIVE"],
            {
                "available_minor": Account.available_minor - amount,
                "reserved_minor": Account.reserved_minor + amount,
            },
            now,
        )

    def add_pending(self, account_id: str, amount: int, now: datetime) -> bool:
        return self._guarded_update(
            account_id,
            [Account.status == "ACTIVE"],
            {"pending_minor": Account.pending_minor + amount},
            now,
        )

    def settle_source(self, account_id: str, amount: int, now: datetime) -> bool:
        return self._guarded_update(
            account_id,
            [Account.reserved_minor >= amount],
            {"reserved_minor": Account.reserved_minor - amount},
            now,
        )

    def settle_destination(self, account_id: str, amount: int, now: datetime) -> bool:
        return self._guarded_update(
            account_id,
            [Account.pending_minor >= amount],
            {
                "pending_minor": Account.pending_minor - amount,
                "available_minor": Account.available_minor + amount,
            },
            now,
        )

    def release_source(self, account_id: str, amount: int, now: datetime) -> bool:
        return self._guarded_update(
            account_id,
            [Account.reserved_minor >= amount],
            {
                "reserved_minor": Account.reserved_minor - amount,
                "available_minor": Account.available_minor + amount,
            },
            now,
        )

    def release_destination(self, account_id: str, amount: int, now: datetime) -> bool:
        return self._guarded_update(
            account_id,
            [Account.pending_minor >= amount],
            {"pending_minor": Account.pending_minor - amount},
            now,
        )
