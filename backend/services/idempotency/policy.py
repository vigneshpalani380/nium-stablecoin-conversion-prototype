"""Idempotency rules for conversion confirmation.

- Key is required and scoped to the customer (unique customer + key in the database).
- The fingerprint binds the key to the request (customer + quote).
- Same key + same fingerprint: replay the stored result (or report IN_PROGRESS).
- Same key + different fingerprint: IDEMPOTENCY_CONFLICT.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from backend.domain import errors
from backend.models.entities import IdempotencyRecord

_KEY_RE = re.compile(r"^[A-Za-z0-9_\-:.]{8,128}$")


@dataclass(frozen=True)
class ConfirmOutcome:
    status_code: int
    body: dict[str, Any]
    replayed: bool = False


def validate_key(key: str | None) -> str:
    if key is None or key.strip() == "":
        raise errors.missing_idempotency_key()
    key = key.strip()
    if not _KEY_RE.match(key):
        raise errors.invalid_idempotency_key()
    return key


def request_fingerprint(customer_id: str, quote_id: str) -> str:
    return hashlib.sha256(f"confirm|{customer_id}|{quote_id}".encode()).hexdigest()


def resolve_existing(record: IdempotencyRecord, fingerprint: str) -> ConfirmOutcome:
    """Decide what a repeated request with a known key gets. Raises for conflict / in-progress."""
    if record.request_fingerprint != fingerprint:
        raise errors.idempotency_conflict()
    if record.state == "REVIEW_REQUIRED":
        raise errors.conversion_under_review(record.transaction_id)
    if record.state == "IN_PROGRESS" or record.response_json is None:
        raise errors.conversion_in_progress(record.transaction_id)
    return ConfirmOutcome(status_code=record.response_status or 200, body=json.loads(record.response_json), replayed=True)
