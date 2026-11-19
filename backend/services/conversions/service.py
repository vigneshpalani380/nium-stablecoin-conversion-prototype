"""Conversion execution: reserve -> settle, with safe handling of definitive and uncertain failures.

Phase 1 (one DB transaction): idempotency lookup, consume quote (OPEN -> CONFIRMED), atomic
check-and-reserve on the source (available -> reserved), destination pending += D, insert the
transaction (RESERVED) and the idempotency record (IN_PROGRESS).

Phase 2 (one DB transaction): source reserved -= G, destination pending -= D / available += D,
transaction COMPLETED, idempotency COMPLETED with the stored response.

Failure handling after the reservation:
- Definitive failure before commit (known, nothing committed) -> release the reservation (FAILED).
- Uncertain outcome (connection lost during COMMIT, any unexpected error) -> NEVER assume failure.
  Automated recovery inspects the authoritative records using the original conversion ID and
  idempotency key:
    COMMITTED      -> confirm COMPLETED
    NOT_COMMITTED  -> release the reservation exactly once (FAILED)
    cannot tell    -> stop automation, keep funds reserved, mark REVIEW_REQUIRED, open an internal
                      review case and queue a (simulated) email to Nium Operations.
  Recovery never re-runs settlement, never creates a new idempotency key, never credits speculatively.

Every state transition is written to the internal `conversion_events` audit trail.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import timedelta

from sqlalchemy.exc import IntegrityError

from backend.db.database import Database
from backend.domain import errors
from backend.domain.money import format_minor
from backend.domain.support import DemoFaults, display_name, iso, log_event, new_id
from backend.models.entities import (
    ConversionQuote,
    ConversionTransaction,
    IdempotencyRecord,
    InternalNotification,
    ReviewCase,
)
from backend.repositories.accounts import AccountRepository
from backend.repositories.operations import EventRepository, ReviewRepository
from backend.repositories.records import IdempotencyRepository, QuoteRepository, TransactionRepository
from backend.schemas.serializers import error_body, transaction_out
from backend.services.idempotency.policy import ConfirmOutcome, request_fingerprint, resolve_existing, validate_key
from backend.services.operations import evidence as ev
from backend.services.operations.notifications import EVENT as REVIEW_EVENT
from backend.services.operations.notifications import build_review_notification

RECOVERY_ATTEMPTS = 3
DB_COMMIT_LOST = ("Simulated: database connection lost during settlement COMMIT; "
                  "no commit acknowledgement received")


class _SettlementSkipped(Exception):
    """The transaction was already finalised elsewhere (e.g. reconcile); return what is stored."""


class ConversionService:
    def __init__(self, db: Database, clock, faults: DemoFaults) -> None:
        self.db = db
        self.clock = clock
        self.faults = faults

    # ------------------------------------------------------------------ public API
    def confirm(self, customer_id: str, quote_id: str, idempotency_key: str | None, request_id: str | None = None) -> ConfirmOutcome:
        key = validate_key(idempotency_key)
        fingerprint = request_fingerprint(customer_id, quote_id)

        try:
            with self.db.transaction() as s:
                existing = IdempotencyRepository(s).get(customer_id, key)
                if existing is not None:
                    outcome = resolve_existing(existing, fingerprint)
                    log_event("conversion.replayed", customer=customer_id, key=key, transaction=existing.transaction_id)
                    return outcome
                txn_id = self._reserve(s, customer_id, quote_id, key, fingerprint)
        except errors.AppError as exc:
            if exc.code == "QUOTE_EXPIRED":
                self._mark_quote_expired(quote_id)
            log_event("conversion.rejected", customer=customer_id, quote=quote_id, key=key, code=exc.code)
            raise
        except IntegrityError:
            # A concurrent request with the same key/quote won the race. Re-read and replay.
            with self.db.transaction() as s:
                existing = IdempotencyRepository(s).get(customer_id, key)
                if existing is not None:
                    return resolve_existing(existing, fingerprint)
            raise errors.quote_already_used()

        log_event("conversion.reserved", customer=customer_id, quote=quote_id, key=key, transaction=txn_id,
                  fingerprint=fingerprint[:12], request_id=request_id)

        pause = self.faults.pause_after_reserve_seconds
        if pause > 0:
            time.sleep(pause)

        outcome = self._execute_settlement(txn_id, request_id)
        if outcome.status_code == 200 and not outcome.replayed:
            log_event("conversion.completed", customer=customer_id, transaction=txn_id, key=key)
            if self.faults.take("timeout_after_commit"):
                raise errors.SimulatedTimeout(txn_id, key)
        return outcome

    def reconcile(self, older_than_seconds: float) -> list[str]:
        """Release RESERVED transactions older than the threshold (crash recovery).

        Safe because settlement is atomic: a transaction still RESERVED in the database did not settle.
        REVIEW_REQUIRED transactions are never touched by automation.
        """
        cutoff = self.clock.now() - timedelta(seconds=older_than_seconds)
        with self.db.transaction() as s:
            stuck = TransactionRepository(s).list_reserved_before(cutoff)
        released = []
        for txn_id in stuck:
            self._release(txn_id, "RECONCILED_RELEASE",
                          "The conversion did not complete and the reserved funds were released.", None)
            released.append(txn_id)
        if released:
            log_event("conversion.reconciled", released=released)
        return released

    # ------------------------------------------------------------------ settlement
    def _execute_settlement(self, txn_id: str, request_id: str | None) -> ConfirmOutcome:
        fault = self.faults.take_uncertain_commit()
        attempted_at = self.clock.now()
        self._event(txn_id, "SETTLEMENT_ATTEMPTED")
        try:
            with self.db.transaction() as s:
                outcome = self._settle(s, txn_id)
                if fault and fault[0] == "ROLLED_BACK":
                    raise errors.SimulatedCommitUncertain(DB_COMMIT_LOST)  # raised inside -> rolled back
            if fault and fault[0] == "COMMITTED":
                raise errors.SimulatedCommitUncertain(DB_COMMIT_LOST)  # raised after commit
            return outcome
        except _SettlementSkipped:
            return self._stored_outcome(txn_id)
        except errors.SimulatedFailure as exc:
            # Definitive: a known failure raised before COMMIT, so nothing was committed.
            log_event("conversion.settle_failed", transaction=txn_id, error=str(exc))
            return self._release(txn_id, "SETTLEMENT_FAILED",
                                 "The conversion could not be completed. Your reserved funds were released.",
                                 request_id)
        except Exception as exc:  # noqa: BLE001 - outcome unknown: never assume failure or success
            db_error = str(exc) if isinstance(exc, errors.SimulatedCommitUncertain) else f"{type(exc).__name__}: {exc}"
            log_event("conversion.outcome_uncertain", transaction=txn_id, error=db_error)
            return self._recover_uncertain(txn_id, attempted_at, db_error, bool(fault and fault[1]), request_id)

    def _recover_uncertain(self, txn_id: str, attempted_at, db_error: str, lookup_fails: bool,
                           request_id: str | None) -> ConfirmOutcome:
        self._event(txn_id, "OUTCOME_UNCERTAIN", detail={"database_error": db_error})
        attempts: list[dict] = []
        evidence: ev.SettlementEvidence | None = None
        for n in range(1, RECOVERY_ATTEMPTS + 1):
            at = self.clock.now()
            try:
                if lookup_fails:
                    raise errors.SimulatedConnectionLost(
                        "Simulated: connection to settlement records unavailable during recovery lookup")
                with self.db.transaction() as s:
                    evidence = ev.inspect_settlement(s, txn_id)
            except Exception as exc:  # noqa: BLE001 - lookup failure is evidence of nothing
                attempts.append({"attempt": n, "at": iso(at), "result": "LOOKUP_FAILED", "error": str(exc)})
                self._event(txn_id, "AUTOMATED_RECOVERY_ATTEMPT", detail=attempts[-1])
                continue
            attempts.append({"attempt": n, "at": iso(at), "result": evidence.conclusion})
            self._event(txn_id, "AUTOMATED_RECOVERY_ATTEMPT", detail={**attempts[-1], "evidence": evidence.to_dict()})
            if evidence.conclusion == ev.COMMITTED:
                return self.finalise_committed(txn_id, "SYSTEM", "RECOVERY_CONFIRMED_COMMITTED")
            if evidence.conclusion == ev.NOT_COMMITTED:
                return self._release(txn_id, "SETTLEMENT_NOT_COMMITTED",
                                     "The conversion could not be completed. Your reserved funds were released.",
                                     request_id, event="RECOVERY_CONFIRMED_NOT_COMMITTED")
            if evidence.conclusion == ev.ALREADY_RELEASED:
                return self._stored_outcome(txn_id)
            break  # INCONCLUSIVE: retrying the same read will not help

        if evidence is None:
            probe = {"conversion_record_found": "UNKNOWN (lookup failed)",
                     "source_debit_found": "UNKNOWN (lookup failed)",
                     "destination_credit_found": "UNKNOWN (lookup failed)",
                     "idempotency_lookup_result": f"FAILED after {len(attempts)} attempts: {attempts[-1]['error']}"}
            reason = (f"All {len(attempts)} automated recovery lookups failed; the settlement records could not be "
                      "read, so neither a committed nor a rolled-back settlement can be established.")
        else:
            probe = {"conversion_record_found": evidence.conversion_record_found,
                     "source_debit_found": evidence.source_debit_found,
                     "destination_credit_found": evidence.destination_credit_found,
                     "idempotency_lookup_result": f"found={evidence.idempotency_record_found} state={evidence.idempotency_state}"}
            reason = f"Inconsistent evidence after recovery: {evidence.explanation}"
        return self.escalate(txn_id, attempted_at, db_error, attempts, probe, reason)

    # ------------------------------------------------------------------ escalation (automation stops here)
    def escalate(self, txn_id: str, attempted_at, db_error: str, attempts: list[dict], probe: dict,
                 reason: str) -> ConfirmOutcome:
        """Open ONE review case and ONE simulated notification. Changes no balances. Idempotent."""
        now = self.clock.now()
        created = None
        with self.db.transaction() as s:
            reviews = ReviewRepository(s)
            existing = reviews.get_for_transaction(txn_id)
            txn = TransactionRepository(s).get(txn_id)
            if existing is None:
                reviews.mark_transaction_review_required(txn_id)
                reviews.mark_idempotency_review_required(txn.customer_id, txn.idempotency_key, now)
                case_id = f"RVW-{uuid.uuid4().hex[:8].upper()}"
                subject, body, payload = build_review_notification(
                    txn, case_id, now, attempted_at, db_error, attempts, probe, reason)
                reviews.add(ReviewCase(
                    id=case_id, transaction_id=txn_id, customer_id=txn.customer_id, status="OPEN", reason=reason,
                    evidence_json=json.dumps({"database_error": db_error, "settlement_attempted_at": iso(attempted_at),
                                              "probe": probe, "automated_recovery_attempts": attempts}),
                    created_at=now, updated_at=now))
                s.flush()
                notification = InternalNotification(
                    id=f"NTF-{uuid.uuid4().hex[:8].upper()}", review_case_id=case_id, transaction_id=txn_id,
                    event=REVIEW_EVENT, channel="EMAIL", recipient_group="OPERATIONS", priority="HIGH",
                    subject=subject, body=body, payload_json=json.dumps(payload), status="QUEUED", created_at=now)
                reviews.add_notification(notification)
                events = EventRepository(s)
                events.add(txn_id, "HUMAN_REVIEW_REQUIRED", now, detail={"review_case_id": case_id, "reason": reason})
                events.add(txn_id, "NOTIFICATION_QUEUED", now,
                           detail={"notification_id": notification.id, "channel": "EMAIL",
                                   "recipient_group": "OPERATIONS", "simulated": True})
                created = (case_id, notification.id, body)
            s.flush()
            s.refresh(txn)
            body_out = transaction_out(txn, last_updated_at=now)
        if created:
            log_event("ops.review_case_opened", transaction=txn_id, review_case=created[0], reason=reason)
            log_event("ops.notification.simulated_email", notification=created[1], transaction=txn_id,
                      recipient_group="OPERATIONS", channel="EMAIL", status="QUEUED", note="SIMULATED - not sent")
            log_event("ops.notification.body", notification=created[1], body=created[2])
        return ConfirmOutcome(status_code=202, body=body_out)

    # ------------------------------------------------------------------ phases
    def _reserve(self, s, customer_id: str, quote_id: str, key: str, fingerprint: str) -> str:
        quotes = QuoteRepository(s)
        accounts = AccountRepository(s)
        now = self.clock.now()

        quote = quotes.get_for_customer(quote_id, customer_id)
        if quote is None:
            raise errors.quote_not_found(quote_id)
        self._assert_quote_usable(quote, now)
        if not quotes.try_consume(quote.id, now):
            raise errors.quote_already_used()

        src_before = accounts.snapshot(quote.source_account_id)
        dst_before = accounts.snapshot(quote.destination_account_id)

        # Atomic check-and-reserve: one conditional UPDATE.
        if not accounts.try_reserve(quote.source_account_id, quote.gross_source_minor, now):
            src = accounts.get_for_customer(quote.source_account_id, customer_id)
            raise errors.insufficient_balance(
                format_minor(src_before.available, quote.source_precision),
                display_name(src.asset_code, src.network) if src else quote.fee_currency,
            )
        if not accounts.add_pending(quote.destination_account_id, quote.destination_minor, now):
            raise errors.account_inactive()

        if self.faults.take("fail_mid_reserve"):
            raise errors.SimulatedFailure("Injected failure before reserve commit")

        src = accounts.get_for_customer(quote.source_account_id, customer_id)
        dst = accounts.get_for_customer(quote.destination_account_id, customer_id)
        txn = ConversionTransaction(
            id=new_id("txn"),
            customer_id=customer_id,
            quote_id=quote.id,
            idempotency_key=key,
            request_fingerprint=fingerprint,
            source_account_id=src.id,
            destination_account_id=dst.id,
            source_asset_code=src.asset_code,
            source_network=src.network,
            source_precision=quote.source_precision,
            destination_asset_code=dst.asset_code,
            destination_network=dst.network,
            destination_precision=quote.destination_precision,
            gross_source_minor=quote.gross_source_minor,
            fee_rate=quote.fee_rate,
            fee_minor=quote.fee_minor,
            fee_currency=quote.fee_currency,
            net_source_minor=quote.net_source_minor,
            exchange_rate=quote.exchange_rate,
            rate_source=quote.rate_source,
            destination_minor=quote.destination_minor,
            src_available_before=src_before.available,
            src_reserved_before=src_before.reserved,
            src_pending_before=src_before.pending,
            dst_available_before=dst_before.available,
            dst_reserved_before=dst_before.reserved,
            dst_pending_before=dst_before.pending,
            status="RESERVED",
            created_at=now,
            reserved_at=now,
        )
        TransactionRepository(s).add(txn)
        s.flush()
        IdempotencyRepository(s).add(
            IdempotencyRecord(
                customer_id=customer_id,
                idempotency_key=key,
                request_fingerprint=fingerprint,
                state="IN_PROGRESS",
                transaction_id=txn.id,
                created_at=now,
                updated_at=now,
            )
        )
        events = EventRepository(s)
        events.add(txn.id, "REQUESTED", now, detail={"quote_id": quote.id, "idempotency_key": key})
        events.add(txn.id, "VALIDATED", now)
        events.add(txn.id, "RESERVED", now)
        s.flush()
        return txn.id

    def _settle(self, s, txn_id: str) -> ConfirmOutcome:
        txns = TransactionRepository(s)
        accounts = AccountRepository(s)
        now = self.clock.now()
        txn = txns.get(txn_id)
        if txn is None or txn.status != "RESERVED":
            raise _SettlementSkipped(txn_id)

        if not accounts.settle_source(txn.source_account_id, txn.gross_source_minor, now):
            raise RuntimeError("source reserved balance below reservation")
        if self.faults.take("fail_mid_settle"):
            raise errors.SimulatedFailure("Injected failure mid-settlement")
        if not accounts.settle_destination(txn.destination_account_id, txn.destination_minor, now):
            raise RuntimeError("destination pending balance below expected credit")

        self._write_after(txn, accounts)
        txn.status = "COMPLETED"
        txn.settled_at = now
        s.flush()
        body = transaction_out(txn)
        self._finish_idempotency(s, txn, "COMPLETED", 200, body, now)
        EventRepository(s).add(txn_id, "COMPLETED", now)
        return ConfirmOutcome(status_code=200, body=body)

    def finalise_committed(self, txn_id: str, actor: str, event: str) -> ConfirmOutcome:
        """Record an authoritatively-committed settlement as COMPLETED. Moves no balances."""
        with self.db.transaction() as s:
            now = self.clock.now()
            txn = TransactionRepository(s).get(txn_id)
            if txn.status == "REVIEW_REQUIRED":
                txn.status = "COMPLETED"
            s.flush()
            body = transaction_out(txn, last_updated_at=now)
            self._finish_idempotency(s, txn, "COMPLETED", 200, body, now)
            EventRepository(s).add(txn_id, event, now, actor=actor)
        log_event("conversion.recovered_committed", transaction=txn_id, actor=actor)
        return ConfirmOutcome(status_code=200, body=body)

    def _release(self, txn_id: str, failure_code: str, message: str, request_id: str | None,
                 allowed_statuses: tuple[str, ...] = ("RESERVED",), event: str = "RESERVATION_RELEASED",
                 actor: str = "SYSTEM") -> ConfirmOutcome:
        """Release the reservation exactly once (guarded by status + balance guards)."""
        with self.db.transaction() as s:
            txns = TransactionRepository(s)
            accounts = AccountRepository(s)
            now = self.clock.now()
            txn = txns.get(txn_id)
            if txn is None:
                raise RuntimeError(f"transaction {txn_id} missing")
            record = IdempotencyRepository(s).get(txn.customer_id, txn.idempotency_key)
            if txn.status not in allowed_statuses:
                # Already finalised: return what was stored; never release twice.
                if record is not None and record.response_json is not None:
                    return ConfirmOutcome(record.response_status or 200, json.loads(record.response_json), replayed=True)
                return ConfirmOutcome(200, transaction_out(txn))

            if not accounts.release_source(txn.source_account_id, txn.gross_source_minor, now):
                raise RuntimeError("cannot release source reservation")
            if not accounts.release_destination(txn.destination_account_id, txn.destination_minor, now):
                raise RuntimeError("cannot release destination pending")
            self._write_after(txn, accounts)
            txn.status = "FAILED"
            txn.failure_code = failure_code
            txn.failure_message = message
            txn.released_at = now
            s.flush()
            body = error_body(
                "CONVERSION_FAILED", message, False, request_id,
                {"transaction_id": txn.id, "status": "FAILED", "failure_code": failure_code},
            )
            self._finish_idempotency(s, txn, "FAILED", 500, body, now)
            EventRepository(s).add(txn_id, event, now, actor=actor, detail={"failure_code": failure_code})
        log_event("conversion.released", transaction=txn_id, failure_code=failure_code, actor=actor)
        return ConfirmOutcome(status_code=500, body=body)

    # ------------------------------------------------------------------ helpers
    def _stored_outcome(self, txn_id: str) -> ConfirmOutcome:
        with self.db.transaction() as s:
            txn = TransactionRepository(s).get(txn_id)
            record = IdempotencyRepository(s).get(txn.customer_id, txn.idempotency_key)
            if record is not None and record.response_json is not None and record.state in ("COMPLETED", "FAILED"):
                return ConfirmOutcome(record.response_status or 200, json.loads(record.response_json), replayed=True)
            return ConfirmOutcome(202 if txn.status == "REVIEW_REQUIRED" else 200, transaction_out(txn))

    def _event(self, txn_id: str, event: str, actor: str = "SYSTEM", detail: dict | None = None) -> None:
        """Best-effort audit write in its own transaction (never blocks the financial flow)."""
        try:
            with self.db.transaction() as s:
                EventRepository(s).add(txn_id, event, self.clock.now(), actor=actor, detail=detail)
        except Exception:  # noqa: BLE001
            log_event("audit.write_failed", transaction=txn_id, audit_event=event)

    @staticmethod
    def _assert_quote_usable(quote: ConversionQuote, now) -> None:
        if quote.status == "CONFIRMED":
            raise errors.quote_already_used()
        if quote.status == "CANCELLED":
            raise errors.quote_cancelled()
        if quote.status == "EXPIRED" or now >= quote.expires_at:
            raise errors.quote_expired()

    @staticmethod
    def _write_after(txn: ConversionTransaction, accounts: AccountRepository) -> None:
        src = accounts.snapshot(txn.source_account_id)
        dst = accounts.snapshot(txn.destination_account_id)
        txn.src_available_after, txn.src_reserved_after, txn.src_pending_after = src.available, src.reserved, src.pending
        txn.dst_available_after, txn.dst_reserved_after, txn.dst_pending_after = dst.available, dst.reserved, dst.pending

    @staticmethod
    def _finish_idempotency(s, txn: ConversionTransaction, state: str, status: int, body: dict, now) -> None:
        record = IdempotencyRepository(s).get(txn.customer_id, txn.idempotency_key)
        if record is None:
            raise RuntimeError("idempotency record missing for reserved transaction")
        record.state = state
        record.response_status = status
        record.response_json = json.dumps(body)
        record.updated_at = now

    def _mark_quote_expired(self, quote_id: str) -> None:
        try:
            with self.db.transaction() as s:
                QuoteRepository(s).mark_expired(quote_id)
        except Exception:  # noqa: BLE001 - best effort status bookkeeping only
            pass
