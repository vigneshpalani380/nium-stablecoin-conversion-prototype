"""INTERNAL Nium Operations API — not used by the customer application.

Simulates the operations side of the human-review boundary: the (simulated) email outbox, review
cases with their evidence and audit history, read-only inspection of authoritative records, and
recording a reviewer's resolution. Protected by a demo X-Ops-Token header.
"""
from typing import Literal

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, ConfigDict, Field

from backend.api.deps import get_container
from backend.container import Container
from backend.domain import errors


def require_ops(x_ops_token: str | None = Header(default=None, alias="X-Ops-Token"),
                c: Container = Depends(get_container)) -> None:
    if x_ops_token != c.settings.ops_token:
        raise errors.ops_unauthorised()


router = APIRouter(prefix="/internal/v1", tags=["internal-operations (not customer-facing)"],
                   dependencies=[Depends(require_ops)])


class Resolution(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["CONFIRM_COMMITTED", "CONFIRM_NOT_COMMITTED", "ESCALATE"]
    reviewer: str = Field(min_length=2, max_length=64)
    note: str = Field(min_length=3, max_length=1000)


@router.get("/notifications", summary="Simulated email outbox for Nium Operations")
def list_notifications(c: Container = Depends(get_container)) -> dict:
    return {"notifications": c.reviews().list_notifications()}


@router.get("/notifications/{notification_id}", summary="Full simulated email (subject, body, structured payload)")
def get_notification(notification_id: str, c: Container = Depends(get_container)) -> dict:
    return c.reviews().get_notification(notification_id)


@router.get("/review-cases")
def list_review_cases(c: Container = Depends(get_container)) -> dict:
    return {"review_cases": c.reviews().list_cases()}


@router.get("/review-cases/{case_id}", summary="Case, evidence, notifications and audit history")
def get_review_case(case_id: str, c: Container = Depends(get_container)) -> dict:
    return c.reviews().get_case(case_id)


@router.get("/review-cases/{case_id}/inspection", summary="Read-only inspection of the authoritative records")
def inspect_review_case(case_id: str, c: Container = Depends(get_container)) -> dict:
    return c.reviews().inspect(case_id)


@router.post("/review-cases/{case_id}/resolution", summary="Record the reviewer's decision (validated against evidence)")
def resolve_review_case(case_id: str, body: Resolution, c: Container = Depends(get_container)) -> dict:
    return c.reviews().resolve(case_id, body.action, body.reviewer, body.note)


@router.get("/conversions/{transaction_id}/events", summary="Internal audit trail of state transitions")
def conversion_events(transaction_id: str, c: Container = Depends(get_container)) -> dict:
    return {"conversion_id": transaction_id, "events": c.reviews().conversion_events(transaction_id)}
