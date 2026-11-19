from fastapi import APIRouter, Depends, Query

from backend.api.deps import get_container
from backend.container import Container

router = APIRouter(prefix="/api/v1", tags=["transactions"])


@router.get("/conversion/transactions")
def list_transactions(limit: int = Query(default=50, ge=1, le=200), c: Container = Depends(get_container)) -> dict:
    return {"transactions": c.transactions().list_recent(c.settings.customer_id, limit)}


@router.get("/conversion/transactions/by-idempotency-key/{key}")
def get_by_idempotency_key(key: str, c: Container = Depends(get_container)) -> dict:
    """Uncertain-outcome recovery: look up the original conversion by the client's original key."""
    return c.transactions().get_by_idempotency_key(c.settings.customer_id, key)


@router.get("/conversion/transactions/{transaction_id}")
def get_transaction(transaction_id: str, c: Container = Depends(get_container)) -> dict:
    return c.transactions().get(c.settings.customer_id, transaction_id)
