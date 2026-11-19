from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import JSONResponse

from backend.api.deps import get_container, request_id
from backend.container import Container

router = APIRouter(prefix="/api/v1", tags=["conversions"])


@router.post("/conversion/quotes/{quote_id}/confirm")
def confirm_quote(
    quote_id: str,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    c: Container = Depends(get_container),
) -> JSONResponse:
    """Quote values are read from the persisted quote; nothing financial is accepted from the client."""
    outcome = c.conversions().confirm(c.settings.customer_id, quote_id, idempotency_key, request_id(request))
    headers = {"Idempotent-Replayed": "true"} if outcome.replayed else {}
    return JSONResponse(outcome.body, status_code=outcome.status_code, headers=headers)
