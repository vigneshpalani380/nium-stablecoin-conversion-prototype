"""Shared test helpers. Amounts are compared as Decimal, never float."""
from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select

from backend.models.entities import ConversionTransaction, IdempotencyRecord

USD, INR = "acct-usd", "acct-inr"
USDC_SOL, USDC_BASE, USDT_SOL = "acct-usdc-sol", "acct-usdc-base", "acct-usdt-sol"


def balances(client) -> dict[str, dict[str, Decimal]]:
    resp = client.get("/api/v1/accounts")
    assert resp.status_code == 200
    return {
        a["id"]: {
            "available": Decimal(a["available_balance"]),
            "reserved": Decimal(a["reserved_balance"]),
            "pending": Decimal(a["pending_balance"]),
        }
        for a in resp.json()["accounts"]
    }


def make_quote(client, src: str, dst: str, amount: str):
    return client.post(
        "/api/v1/conversion/quotes",
        json={"source_account_id": src, "destination_account_id": dst, "gross_source_amount": amount},
    )


def quote_id(client, src: str, dst: str, amount: str) -> str:
    resp = make_quote(client, src, dst, amount)
    assert resp.status_code == 201, resp.text
    return resp.json()["quote_id"]


def new_key() -> str:
    return f"key-{uuid.uuid4().hex}"


def confirm(client, qid: str, key: str | None):
    headers = {"Idempotency-Key": key} if key is not None else {}
    return client.post(f"/api/v1/conversion/quotes/{qid}/confirm", headers=headers)


def txn_count(container) -> int:
    with container.db.transaction() as s:
        return s.scalar(select(func.count()).select_from(ConversionTransaction))


def idem_count(container) -> int:
    with container.db.transaction() as s:
        return s.scalar(select(func.count()).select_from(IdempotencyRecord))


def completed_count(container) -> int:
    with container.db.transaction() as s:
        return s.scalar(
            select(func.count()).select_from(ConversionTransaction).where(ConversionTransaction.status == "COMPLETED")
        )
