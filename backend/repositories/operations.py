"""Persistence for internal operations data: audit events, review cases, simulated notifications."""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.models.entities import (
    ConversionEvent,
    ConversionTransaction,
    IdempotencyRecord,
    InternalNotification,
    ReviewCase,
)


class EventRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def add(self, transaction_id: str, event: str, now: datetime, actor: str = "SYSTEM", detail: dict | None = None) -> None:
        self.s.add(ConversionEvent(transaction_id=transaction_id, event=event, actor=actor,
                                   detail_json=json.dumps(detail, default=str) if detail else None, created_at=now))

    def list_for(self, transaction_id: str) -> list[ConversionEvent]:
        return list(self.s.scalars(select(ConversionEvent).where(ConversionEvent.transaction_id == transaction_id)
                                   .order_by(ConversionEvent.id)))

    def last_at(self, transaction_id: str) -> datetime | None:
        return self.s.scalar(select(func.max(ConversionEvent.created_at)).where(ConversionEvent.transaction_id == transaction_id))


class ReviewRepository:
    def __init__(self, session: Session) -> None:
        self.s = session

    def get(self, case_id: str) -> ReviewCase | None:
        return self.s.get(ReviewCase, case_id)

    def get_for_transaction(self, transaction_id: str) -> ReviewCase | None:
        return self.s.scalar(select(ReviewCase).where(ReviewCase.transaction_id == transaction_id))

    def list_all(self) -> list[ReviewCase]:
        return list(self.s.scalars(select(ReviewCase).order_by(ReviewCase.created_at.desc())))

    def add(self, case: ReviewCase) -> None:
        self.s.add(case)

    def notifications(self, transaction_id: str | None = None) -> list[InternalNotification]:
        stmt = select(InternalNotification).order_by(InternalNotification.created_at.desc())
        if transaction_id:
            stmt = stmt.where(InternalNotification.transaction_id == transaction_id)
        return list(self.s.scalars(stmt))

    def notification(self, notification_id: str) -> InternalNotification | None:
        return self.s.get(InternalNotification, notification_id)

    def add_notification(self, n: InternalNotification) -> None:
        self.s.add(n)

    # Blind, guarded writes used on escalation (they do not depend on reading settlement evidence).
    def mark_transaction_review_required(self, transaction_id: str) -> bool:
        stmt = (update(ConversionTransaction)
                .where(ConversionTransaction.id == transaction_id,
                       ConversionTransaction.status.in_(("RESERVED", "COMPLETED")))
                .values(status="REVIEW_REQUIRED").execution_options(synchronize_session=False))
        return self.s.execute(stmt).rowcount == 1

    def mark_idempotency_review_required(self, customer_id: str, key: str, now: datetime) -> bool:
        stmt = (update(IdempotencyRecord)
                .where(IdempotencyRecord.customer_id == customer_id, IdempotencyRecord.idempotency_key == key)
                .values(state="REVIEW_REQUIRED", updated_at=now).execution_options(synchronize_session=False))
        return self.s.execute(stmt).rowcount == 1
