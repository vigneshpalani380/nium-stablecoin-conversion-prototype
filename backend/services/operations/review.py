"""Internal operations review: inspect evidence and record a reviewer's resolution.

This is NOT part of the customer application. A reviewer's decision is validated against the
authoritative records; it can never release funds or confirm completion on the timeout alone.
"""
from __future__ import annotations

import json
from typing import Any

from backend.db.database import Database
from backend.domain import errors
from backend.domain.support import iso, log_event
from backend.models.entities import InternalNotification, ReviewCase
from backend.repositories.operations import EventRepository, ReviewRepository
from backend.repositories.records import TransactionRepository
from backend.services.conversions.service import ConversionService
from backend.services.operations import evidence as ev

ACTIONS = ("CONFIRM_COMMITTED", "CONFIRM_NOT_COMMITTED", "ESCALATE")
OPEN_STATES = ("OPEN", "ESCALATED")


def case_out(c: ReviewCase) -> dict[str, Any]:
    return {
        "review_case_id": c.id, "conversion_id": c.transaction_id, "customer_id": c.customer_id, "status": c.status,
        "reason": c.reason, "evidence": json.loads(c.evidence_json), "escalation_reason": c.escalation_reason,
        "resolved_by": c.resolved_by, "resolution_note": c.resolution_note, "created_at": iso(c.created_at),
        "updated_at": iso(c.updated_at), "resolved_at": iso(c.resolved_at),
    }


def notification_out(n: InternalNotification, full: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {
        "notification_id": n.id, "conversion_id": n.transaction_id, "review_case_id": n.review_case_id,
        "event": n.event, "channel": n.channel, "recipient_group": n.recipient_group, "priority": n.priority,
        "subject": n.subject, "status": n.status, "simulated": True, "created_at": iso(n.created_at),
    }
    if full:
        out["body"] = n.body
        out["payload"] = json.loads(n.payload_json)
    return out


class ReviewService:
    def __init__(self, db: Database, clock, conversions: ConversionService) -> None:
        self.db = db
        self.clock = clock
        self.conversions = conversions

    def list_cases(self) -> list[dict]:
        with self.db.transaction() as s:
            return [case_out(c) for c in ReviewRepository(s).list_all()]

    def get_case(self, case_id: str) -> dict:
        with self.db.transaction() as s:
            repo = ReviewRepository(s)
            case = repo.get(case_id)
            if case is None:
                raise errors.review_case_not_found(case_id)
            out = case_out(case)
            out["notifications"] = [notification_out(n) for n in repo.notifications(case.transaction_id)]
            out["audit_history"] = self._events(s, case.transaction_id)
            return out

    def inspect(self, case_id: str) -> dict:
        """Read-only inspection of the authoritative records (reviewer step 1-2)."""
        with self.db.transaction() as s:
            case = ReviewRepository(s).get(case_id)
            if case is None:
                raise errors.review_case_not_found(case_id)
            evidence = ev.inspect_settlement(s, case.transaction_id)
        recommended = {ev.COMMITTED: "CONFIRM_COMMITTED", ev.NOT_COMMITTED: "CONFIRM_NOT_COMMITTED"}.get(
            evidence.conclusion, "ESCALATE")
        return {"review_case_id": case_id, "conversion_id": case.transaction_id, "evidence": evidence.to_dict(),
                "supported_action": recommended}

    def resolve(self, case_id: str, action: str, reviewer: str, note: str) -> dict:
        if action not in ACTIONS:
            raise errors.AppError("INVALID_ACTION", f"action must be one of {', '.join(ACTIONS)}.", 400)
        with self.db.transaction() as s:
            case = ReviewRepository(s).get(case_id)
            if case is None:
                raise errors.review_case_not_found(case_id)
            if case.status not in OPEN_STATES:
                raise errors.review_case_closed(case_id, case.status)
            evidence = ev.inspect_settlement(s, case.transaction_id)
            txn_id = case.transaction_id

        if action == "ESCALATE":
            # Keep funds reserved, change no balances, keep the customer status as Under review.
            with self.db.transaction() as s:
                case = ReviewRepository(s).get(case_id)
                now = self.clock.now()
                case.status = "ESCALATED"
                case.escalation_reason = note
                case.updated_at = now
                EventRepository(s).add(txn_id, "REVIEW_ESCALATED", now, actor=reviewer,
                                       detail={"reason": note, "evidence_conclusion": evidence.conclusion})
        elif action == "CONFIRM_COMMITTED":
            if evidence.conclusion != ev.COMMITTED:
                raise errors.resolution_not_supported(action, evidence.conclusion)
            self.conversions.finalise_committed(txn_id, reviewer, "REVIEW_RESOLVED_COMMITTED")
            self._close(case_id, "RESOLVED_COMMITTED", reviewer, note)
        else:  # CONFIRM_NOT_COMMITTED
            if evidence.conclusion != ev.NOT_COMMITTED:
                raise errors.resolution_not_supported(action, evidence.conclusion)
            self.conversions._release(  # noqa: SLF001 - same exactly-once release used by automation
                txn_id, "SETTLEMENT_NOT_COMMITTED",
                "The conversion could not be completed. Your reserved funds were released.", None,
                allowed_statuses=("REVIEW_REQUIRED",), event="REVIEW_RESOLVED_NOT_COMMITTED", actor=reviewer)
            self._close(case_id, "RESOLVED_NOT_COMMITTED", reviewer, note)

        log_event("ops.review_case_action", review_case=case_id, action=action, reviewer=reviewer)
        result = self.get_case(case_id)
        with self.db.transaction() as s:
            result["customer_visible_status"] = TransactionRepository(s).get(txn_id).status
        return result

    def _close(self, case_id: str, status: str, reviewer: str, note: str) -> None:
        with self.db.transaction() as s:
            case = ReviewRepository(s).get(case_id)
            now = self.clock.now()
            case.status, case.resolved_by, case.resolution_note = status, reviewer, note
            case.resolved_at = case.updated_at = now

    def list_notifications(self) -> list[dict]:
        with self.db.transaction() as s:
            return [notification_out(n) for n in ReviewRepository(s).notifications()]

    def get_notification(self, notification_id: str) -> dict:
        with self.db.transaction() as s:
            n = ReviewRepository(s).notification(notification_id)
            if n is None:
                raise errors.notification_not_found(notification_id)
            return notification_out(n, full=True)

    def conversion_events(self, transaction_id: str) -> list[dict]:
        with self.db.transaction() as s:
            return self._events(s, transaction_id)

    @staticmethod
    def _events(s, transaction_id: str) -> list[dict]:
        return [{"event": e.event, "actor": e.actor, "at": iso(e.created_at),
                 "detail": json.loads(e.detail_json) if e.detail_json else None}
                for e in EventRepository(s).list_for(transaction_id)]
