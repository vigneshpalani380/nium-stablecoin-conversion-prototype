"""Demo/test-only controls. Mounted only when WALLET_DEMO_MODE is true."""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from backend.api.deps import get_container
from backend.container import Container
from backend.domain import errors
from backend.repositories.records import QuoteRepository
from backend.seed.seed import reset_demo_data

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


class FaultsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pause_after_reserve_seconds: float | None = Field(default=None, ge=0, le=60)
    fail_mid_reserve: bool | None = None
    fail_mid_settle: bool | None = None
    timeout_after_commit: bool | None = None
    # Simulated uncertain settlement COMMIT (one-shot). The value is what really happened in the DB.
    uncertain_commit: Literal["OFF", "COMMITTED", "ROLLED_BACK"] | None = None
    # With uncertain_commit: automated-recovery lookups also fail -> HUMAN_REVIEW_REQUIRED.
    recovery_lookup_fails: bool | None = None


@router.get("/faults")
def get_faults(c: Container = Depends(get_container)) -> dict:
    return c.faults.snapshot()


@router.put("/faults")
def set_faults(body: FaultsUpdate, c: Container = Depends(get_container)) -> dict:
    c.faults.update(**body.model_dump())
    return c.faults.snapshot()


@router.post("/quotes/{quote_id}/expire")
def expire_quote(quote_id: str, c: Container = Depends(get_container)) -> dict:
    with c.db.transaction() as s:
        repo = QuoteRepository(s)
        if repo.get_for_customer(quote_id, c.settings.customer_id) is None:
            raise errors.quote_not_found(quote_id)
        changed = repo.force_expire(quote_id, c.clock.now())
    return {"quote_id": quote_id, "expired": changed}


@router.post("/reconcile")
def reconcile(older_than_seconds: float = Query(default=0, ge=0), c: Container = Depends(get_container)) -> dict:
    return {"released_transaction_ids": c.conversions().reconcile(older_than_seconds)}


@router.post("/reset")
def reset(c: Container = Depends(get_container)) -> dict:
    c.faults.reset()
    reset_demo_data(c.db, c.settings, c.clock)
    return {"reset": True}
