from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from backend.api.deps import get_container
from backend.container import Container
from backend.repositories.accounts import AccountRepository
from backend.schemas.serializers import quote_out

router = APIRouter(prefix="/api/v1", tags=["quotes"])


class QuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_account_id: str
    destination_account_id: str
    gross_source_amount: str  # decimal string; JSON numbers are rejected to avoid float input


def _render(c: Container, quote) -> dict:  # type: ignore[no-untyped-def]
    with c.db.transaction() as s:
        repo = AccountRepository(s)
        src = repo.get_for_customer(quote.source_account_id, c.settings.customer_id)
        dst = repo.get_for_customer(quote.destination_account_id, c.settings.customer_id)
    return quote_out(quote, src, dst, c.clock.now())


@router.post("/conversion/quotes", status_code=201)
def create_quote(body: QuoteRequest, c: Container = Depends(get_container)) -> dict:
    quote = c.quotes().create(c.settings.customer_id, body.source_account_id, body.destination_account_id,
                              body.gross_source_amount)
    return _render(c, quote)


@router.get("/conversion/quotes/{quote_id}")
def get_quote(quote_id: str, c: Container = Depends(get_container)) -> dict:
    return _render(c, c.quotes().get(c.settings.customer_id, quote_id))


@router.post("/conversion/quotes/{quote_id}/cancel")
def cancel_quote(quote_id: str, c: Container = Depends(get_container)) -> dict:
    return _render(c, c.quotes().cancel(c.settings.customer_id, quote_id))
