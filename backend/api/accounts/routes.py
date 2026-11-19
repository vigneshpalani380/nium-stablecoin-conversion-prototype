"""Read-only account balances. There is intentionally no endpoint that writes balances."""
from fastapi import APIRouter, Depends

from backend.api.deps import get_container
from backend.container import Container
from backend.repositories.accounts import AccountRepository
from backend.schemas.serializers import account_out

router = APIRouter(prefix="/api/v1", tags=["accounts"])


@router.get("/accounts")
def list_accounts(c: Container = Depends(get_container)) -> dict:
    with c.db.transaction() as s:
        accounts = AccountRepository(s).list_for_customer(c.settings.customer_id)
    return {"customer_id": c.settings.customer_id, "accounts": [account_out(a) for a in accounts]}
