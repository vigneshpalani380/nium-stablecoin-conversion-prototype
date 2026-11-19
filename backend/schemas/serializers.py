"""ORM -> API representations. Money is always serialised as decimal strings."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.domain.money import format_minor
from backend.domain.support import display_name, iso
from backend.models.entities import Account, ConversionQuote, ConversionTransaction


def account_out(a: Account) -> dict[str, Any]:
    return {
        "id": a.id,
        "asset_code": a.asset_code,
        "asset_type": a.asset_type,
        "network": a.network,
        "display_name": display_name(a.asset_code, a.network),
        "precision": a.precision,
        "available_balance": format_minor(a.available_minor, a.precision),
        "reserved_balance": format_minor(a.reserved_minor, a.precision),
        "pending_balance": format_minor(a.pending_minor, a.precision),
        "status": a.status,
    }


def effective_quote_status(q: ConversionQuote, now: datetime) -> str:
    if q.status == "OPEN" and now >= q.expires_at:
        return "EXPIRED"
    return q.status


def quote_out(q: ConversionQuote, src: Account, dst: Account, now: datetime) -> dict[str, Any]:
    sp, dp = q.source_precision, q.destination_precision
    return {
        "quote_id": q.id,
        "status": effective_quote_status(q, now),
        "rate_source": q.rate_source,
        "source": {"account_id": src.id, "asset_code": src.asset_code, "network": src.network,
                   "display_name": display_name(src.asset_code, src.network)},
        "destination": {"account_id": dst.id, "asset_code": dst.asset_code, "network": dst.network,
                        "display_name": display_name(dst.asset_code, dst.network)},
        "gross_source_amount": format_minor(q.gross_source_minor, sp),
        "fee_rate": q.fee_rate,
        "fee_amount": format_minor(q.fee_minor, sp),
        "fee_currency": q.fee_currency,
        "net_source_amount": format_minor(q.net_source_minor, sp),
        "exchange_rate": q.exchange_rate,
        "destination_amount": format_minor(q.destination_minor, dp),
        "created_at": iso(q.created_at),
        "expires_at": iso(q.expires_at),
        "seconds_remaining": max(0, int((q.expires_at - now).total_seconds())),
    }


def _balances(t: ConversionTransaction, side: str, precision: int) -> dict[str, Any]:
    def snap(when: str) -> dict[str, Any] | None:
        vals = [getattr(t, f"{side}_{k}_{when}") for k in ("available", "reserved", "pending")]
        if any(v is None for v in vals):
            return None
        return {k: format_minor(v, precision) for k, v in zip(("available", "reserved", "pending"), vals)}

    return {"before": snap("before"), "after": snap("after")}


def transaction_out(t: ConversionTransaction, last_updated_at: datetime | None = None) -> dict[str, Any]:
    """Customer-facing representation. Contains no internal review/notification data."""
    sp, dp = t.source_precision, t.destination_precision
    balances = {"source": _balances(t, "src", sp), "destination": _balances(t, "dst", dp)}
    if t.status == "REVIEW_REQUIRED":
        # Outcome not authoritatively confirmed: never show post-settlement figures to the customer.
        balances["source"]["after"] = None
        balances["destination"]["after"] = None
    if last_updated_at is None:
        last_updated_at = max(d for d in (t.created_at, t.reserved_at, t.settled_at, t.released_at) if d is not None)
    return {
        "transaction_id": t.id,
        "reference": t.id,
        "status": t.status,
        "quote_id": t.quote_id,
        "idempotency_key": t.idempotency_key,
        "source": {"account_id": t.source_account_id, "asset_code": t.source_asset_code, "network": t.source_network,
                   "display_name": display_name(t.source_asset_code, t.source_network)},
        "destination": {"account_id": t.destination_account_id, "asset_code": t.destination_asset_code,
                        "network": t.destination_network,
                        "display_name": display_name(t.destination_asset_code, t.destination_network)},
        "gross_source_amount": format_minor(t.gross_source_minor, sp),
        "fee_rate": t.fee_rate,
        "fee_amount": format_minor(t.fee_minor, sp),
        "fee_currency": t.fee_currency,
        "net_source_amount": format_minor(t.net_source_minor, sp),
        "exchange_rate": t.exchange_rate,
        "rate_source": t.rate_source,
        "destination_amount": format_minor(t.destination_minor, dp),
        "balances": balances,
        "failure_code": t.failure_code,
        "failure_message": t.failure_message,
        "created_at": iso(t.created_at),
        "reserved_at": iso(t.reserved_at),
        "settled_at": iso(t.settled_at),
        "released_at": iso(t.released_at),
        "last_updated_at": iso(last_updated_at),
    }


def error_body(code: str, message: str, retryable: bool, request_id: str | None, details: dict | None = None) -> dict:
    body: dict[str, Any] = {"code": code, "message": message, "retryable": retryable, "request_id": request_id}
    if details:
        body["details"] = details
    return {"error": body}
