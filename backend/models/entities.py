"""Persistence model. Money columns are INTEGER minor units scaled by the asset precision.

There is deliberately no `ledger_entries` table: one `conversion_transactions` row captures
both sides of a conversion and before/after balance snapshots.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(64), index=True)
    asset_code: Mapped[str] = mapped_column(String(16))
    asset_type: Mapped[str] = mapped_column(String(16))
    network: Mapped[str | None] = mapped_column(String(32), nullable=True)
    network_key: Mapped[str] = mapped_column(String(32))
    precision: Mapped[int] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    available_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    reserved_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    pending_minor: Mapped[int] = mapped_column(BigInteger, default=0)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    version: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    __table_args__ = (
        UniqueConstraint("customer_id", "asset_code", "network_key", name="uq_account_identity"),
        CheckConstraint("available_minor >= 0", name="ck_available_nonneg"),
        CheckConstraint("reserved_minor >= 0", name="ck_reserved_nonneg"),
        CheckConstraint("pending_minor >= 0", name="ck_pending_nonneg"),
    )


class ConversionPair(Base):
    __tablename__ = "conversion_pairs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_asset_code: Mapped[str] = mapped_column(String(16))
    source_network_key: Mapped[str] = mapped_column(String(32))
    destination_asset_code: Mapped[str] = mapped_column(String(16))
    destination_network_key: Mapped[str] = mapped_column(String(32))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    simulated_rate: Mapped[str] = mapped_column(String(40))

    __table_args__ = (
        UniqueConstraint(
            "source_asset_code", "source_network_key", "destination_asset_code", "destination_network_key",
            name="uq_pair",
        ),
    )


class ConversionQuote(Base):
    __tablename__ = "conversion_quotes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(64), index=True)
    source_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    destination_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    source_precision: Mapped[int] = mapped_column(Integer)
    destination_precision: Mapped[int] = mapped_column(Integer)
    gross_source_minor: Mapped[int] = mapped_column(BigInteger)
    fee_rate: Mapped[str] = mapped_column(String(20))
    fee_minor: Mapped[int] = mapped_column(BigInteger)
    fee_currency: Mapped[str] = mapped_column(String(16))
    net_source_minor: Mapped[int] = mapped_column(BigInteger)
    exchange_rate: Mapped[str] = mapped_column(String(40))
    destination_minor: Mapped[int] = mapped_column(BigInteger)
    rate_source: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime]
    expires_at: Mapped[datetime]
    status: Mapped[str] = mapped_column(String(16))  # OPEN | CONFIRMED | EXPIRED | CANCELLED

    __table_args__ = (
        CheckConstraint("gross_source_minor > 0", name="ck_quote_gross_pos"),
        CheckConstraint("destination_minor > 0", name="ck_quote_dest_pos"),
    )


class ConversionTransaction(Base):
    __tablename__ = "conversion_transactions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(64), index=True)
    quote_id: Mapped[str] = mapped_column(ForeignKey("conversion_quotes.id"), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    source_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    destination_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"))
    source_asset_code: Mapped[str] = mapped_column(String(16))
    source_network: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_precision: Mapped[int] = mapped_column(Integer)
    destination_asset_code: Mapped[str] = mapped_column(String(16))
    destination_network: Mapped[str | None] = mapped_column(String(32), nullable=True)
    destination_precision: Mapped[int] = mapped_column(Integer)
    gross_source_minor: Mapped[int] = mapped_column(BigInteger)
    fee_rate: Mapped[str] = mapped_column(String(20))
    fee_minor: Mapped[int] = mapped_column(BigInteger)
    fee_currency: Mapped[str] = mapped_column(String(16))
    net_source_minor: Mapped[int] = mapped_column(BigInteger)
    exchange_rate: Mapped[str] = mapped_column(String(40))
    rate_source: Mapped[str] = mapped_column(String(20))
    destination_minor: Mapped[int] = mapped_column(BigInteger)
    # Snapshots: "before" = immediately before reservation; "after" = after settle or release.
    src_available_before: Mapped[int] = mapped_column(BigInteger)
    src_reserved_before: Mapped[int] = mapped_column(BigInteger)
    src_pending_before: Mapped[int] = mapped_column(BigInteger)
    dst_available_before: Mapped[int] = mapped_column(BigInteger)
    dst_reserved_before: Mapped[int] = mapped_column(BigInteger)
    dst_pending_before: Mapped[int] = mapped_column(BigInteger)
    src_available_after: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    src_reserved_after: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    src_pending_after: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    dst_available_after: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    dst_reserved_after: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    dst_pending_after: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(20))  # RESERVED | COMPLETED | FAILED | REVIEW_REQUIRED
    failure_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime]
    reserved_at: Mapped[datetime]
    settled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (UniqueConstraint("customer_id", "idempotency_key", name="uq_txn_idempotency"),)


class ConversionEvent(Base):
    """Internal audit trail of state transitions (REQUESTED, RESERVED, SETTLEMENT_ATTEMPTED,
    OUTCOME_UNCERTAIN, RECOVERY_ATTEMPT, REVIEW_REQUIRED, ...). Never exposed to customers."""

    __tablename__ = "conversion_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[str] = mapped_column(String(64), index=True)
    event: Mapped[str] = mapped_column(String(48))
    actor: Mapped[str] = mapped_column(String(64))  # SYSTEM or reviewer identity
    detail_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]


class ReviewCase(Base):
    """Internal operations case for a conversion whose outcome automation could not establish."""

    __tablename__ = "review_cases"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("conversion_transactions.id"), unique=True)
    customer_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))  # OPEN | ESCALATED | RESOLVED_COMMITTED | RESOLVED_NOT_COMMITTED
    reason: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[str] = mapped_column(Text)
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)


class InternalNotification(Base):
    """Simulated internal email to Nium Operations. No real email is sent."""

    __tablename__ = "internal_notifications"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    review_case_id: Mapped[str] = mapped_column(ForeignKey("review_cases.id"))
    transaction_id: Mapped[str] = mapped_column(String(64))
    event: Mapped[str] = mapped_column(String(48))
    channel: Mapped[str] = mapped_column(String(16))
    recipient_group: Mapped[str] = mapped_column(String(32))
    priority: Mapped[str] = mapped_column(String(16))
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16))  # QUEUED (simulated; never actually sent)
    created_at: Mapped[datetime]

    __table_args__ = (UniqueConstraint("transaction_id", "event", name="uq_notification_per_event"),)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(String(64))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(16))  # IN_PROGRESS | COMPLETED | FAILED
    transaction_id: Mapped[str | None] = mapped_column(ForeignKey("conversion_transactions.id"), nullable=True)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    __table_args__ = (UniqueConstraint("customer_id", "idempotency_key", name="uq_idempotency_key"),)
