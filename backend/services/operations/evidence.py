"""Authoritative settlement evidence for one conversion.

Settlement is a single atomic DB transaction that (a) debits the source reservation, (b) credits the
destination, (c) writes the completed conversion record (status, settled_at, after-snapshots) and
(d) finalises the idempotency record. So the conversion record's settlement marker is present if and
only if the debit and credit committed. Recovery and reviewers classify the outcome from this evidence,
never from the fact that a request timed out.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy.orm import Session

from backend.domain.money import format_minor
from backend.repositories.accounts import AccountRepository
from backend.repositories.records import IdempotencyRepository, TransactionRepository

COMMITTED = "COMMITTED"
NOT_COMMITTED = "NOT_COMMITTED"
ALREADY_RELEASED = "ALREADY_RELEASED"
INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class SettlementEvidence:
    conversion_record_found: bool
    transaction_status: str | None
    settlement_marker_found: bool
    source_debit_found: bool
    destination_credit_found: bool
    reservation_released: bool
    reservation_still_held: bool
    idempotency_record_found: bool
    idempotency_state: str | None
    source_balances: dict | None
    destination_balances: dict | None
    conclusion: str
    explanation: str

    def to_dict(self) -> dict:
        return asdict(self)


def _fmt(snapshot, precision: int) -> dict:
    return {"available": format_minor(snapshot.available, precision),
            "reserved": format_minor(snapshot.reserved, precision),
            "pending": format_minor(snapshot.pending, precision)}


def inspect_settlement(s: Session, transaction_id: str) -> SettlementEvidence:
    txn = TransactionRepository(s).get(transaction_id)
    if txn is None:
        return SettlementEvidence(False, None, False, False, False, False, False, False, None, None, None,
                                  INCONCLUSIVE, "No conversion record exists for this ID.")
    idem = IdempotencyRepository(s).get(txn.customer_id, txn.idempotency_key)
    accounts = AccountRepository(s)
    src = accounts.snapshot(txn.source_account_id)
    dst = accounts.snapshot(txn.destination_account_id)

    marker = txn.settled_at is not None
    debit = marker and txn.src_available_after is not None and txn.src_reserved_after is not None
    credit = marker and txn.dst_available_after is not None
    released = txn.released_at is not None
    held = src.reserved >= txn.gross_source_minor and dst.pending >= txn.destination_minor
    idem_found = idem is not None
    idem_state = idem.state if idem else None

    if marker and debit and credit and not released and txn.status in ("COMPLETED", "REVIEW_REQUIRED"):
        conclusion, why = COMMITTED, "Settlement marker, source debit and destination credit are recorded together."
    elif released and txn.status == "FAILED":
        conclusion, why = ALREADY_RELEASED, "The reservation was already released; the conversion is final (FAILED)."
    elif (not marker and not released and held and idem_found and idem_state in ("IN_PROGRESS", "REVIEW_REQUIRED")
          and txn.status in ("RESERVED", "REVIEW_REQUIRED")):
        conclusion, why = NOT_COMMITTED, ("No settlement marker; the original reservation and pending credit are still held, "
                                          "so the settlement transaction rolled back.")
    else:
        conclusion, why = INCONCLUSIVE, "Records are missing or inconsistent with both a committed and a rolled-back settlement."

    return SettlementEvidence(
        conversion_record_found=True, transaction_status=txn.status, settlement_marker_found=marker,
        source_debit_found=debit, destination_credit_found=credit, reservation_released=released,
        reservation_still_held=held, idempotency_record_found=idem_found, idempotency_state=idem_state,
        source_balances=_fmt(src, txn.source_precision), destination_balances=_fmt(dst, txn.destination_precision),
        conclusion=conclusion, explanation=why,
    )
