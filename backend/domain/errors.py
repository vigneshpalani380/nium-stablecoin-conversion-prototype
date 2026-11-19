"""Domain errors mapped to the API error envelope. Messages are customer-facing and actionable."""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        http_status: int,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.retryable = retryable
        self.details = details or {}


class SimulatedFailure(Exception):
    """Demo/test fault injected inside a DB transaction to prove rollback."""


class SimulatedCommitUncertain(Exception):
    """Demo/test fault: the DB connection was lost during the settlement COMMIT; no acknowledgement received."""


class SimulatedConnectionLost(Exception):
    """Demo/test fault: an automated-recovery lookup could not reach the settlement records."""


class SimulatedTimeout(Exception):
    """Demo/test fault: the conversion committed but the response is 'lost'."""

    def __init__(self, transaction_id: str, idempotency_key: str) -> None:
        super().__init__("Simulated response timeout after commit")
        self.transaction_id = transaction_id
        self.idempotency_key = idempotency_key


def invalid_amount() -> AppError:
    return AppError("INVALID_AMOUNT", "Enter an amount greater than zero using digits and an optional decimal point.", 400)


def precision_exceeded(precision: int) -> AppError:
    return AppError("PRECISION_EXCEEDED", f"This asset supports at most {precision} decimal places.", 400)


def amount_too_small() -> AppError:
    return AppError("AMOUNT_TOO_SMALL", "The amount is too small to convert after the fee. Enter a larger amount.", 400)


def same_account() -> AppError:
    return AppError("SAME_ACCOUNT", "Choose different source and destination accounts.", 400)


def unsupported_pair(source: str, destination: str) -> AppError:
    return AppError("UNSUPPORTED_PAIR", f"Conversion from {source} to {destination} is not enabled.", 400)


def missing_idempotency_key() -> AppError:
    return AppError("MISSING_IDEMPOTENCY_KEY", "An Idempotency-Key header is required to confirm a conversion.", 400)


def invalid_idempotency_key() -> AppError:
    return AppError(
        "INVALID_IDEMPOTENCY_KEY",
        "Idempotency-Key must be 8-128 characters of letters, digits, '-', '_', ':' or '.'.",
        400,
    )


def account_not_found(account_id: str) -> AppError:
    return AppError("ACCOUNT_NOT_FOUND", f"Account {account_id} was not found.", 404)


def quote_not_found(quote_id: str) -> AppError:
    return AppError("QUOTE_NOT_FOUND", f"Quote {quote_id} was not found.", 404)


def transaction_not_found() -> AppError:
    return AppError(
        "TRANSACTION_NOT_FOUND",
        "No conversion was found for this reference. If you just submitted it, nothing was recorded; "
        "you can safely retry with the same reference.",
        404,
    )


def account_inactive() -> AppError:
    return AppError("ACCOUNT_INACTIVE", "One of the selected accounts is not active.", 409)


def insufficient_balance(available: str, currency: str) -> AppError:
    return AppError(
        "INSUFFICIENT_BALANCE",
        f"Insufficient available balance. Available: {available} {currency}.",
        409,
        details={"available": available, "currency": currency},
    )


def quote_expired() -> AppError:
    return AppError("QUOTE_EXPIRED", "This quote has expired. Request a new quote.", 409, retryable=True)


def quote_already_used() -> AppError:
    return AppError(
        "QUOTE_ALREADY_USED",
        "This quote has already been used for a conversion. Check Activity before requesting a new quote.",
        409,
    )


def quote_cancelled() -> AppError:
    return AppError("QUOTE_CANCELLED", "This quote was cancelled. Request a new quote.", 409, retryable=True)


def idempotency_conflict() -> AppError:
    return AppError(
        "IDEMPOTENCY_CONFLICT",
        "This reference was already used for a different conversion request.",
        409,
    )


def conversion_under_review(transaction_id: str | None) -> AppError:
    return AppError(
        "CONVERSION_UNDER_REVIEW",
        "This conversion is under review. Your funds remain reserved; you do not need to submit it again.",
        409,
        retryable=True,
        details={"transaction_id": transaction_id},
    )


def review_case_not_found(case_id: str) -> AppError:
    return AppError("REVIEW_CASE_NOT_FOUND", f"Review case {case_id} was not found.", 404)


def notification_not_found(notification_id: str) -> AppError:
    return AppError("NOTIFICATION_NOT_FOUND", f"Notification {notification_id} was not found.", 404)


def review_case_closed(case_id: str, status: str) -> AppError:
    return AppError("REVIEW_CASE_CLOSED", f"Review case {case_id} is already {status}.", 409)


def resolution_not_supported(action: str, conclusion: str) -> AppError:
    return AppError(
        "RESOLUTION_NOT_SUPPORTED_BY_EVIDENCE",
        f"{action} is not supported by the authoritative records (current conclusion: {conclusion}). "
        "Keep the case unresolved or escalate.",
        409,
        details={"evidence_conclusion": conclusion},
    )


def ops_unauthorised() -> AppError:
    return AppError("OPS_UNAUTHORISED", "Internal operations endpoint: a valid X-Ops-Token header is required.", 401)


def conversion_in_progress(transaction_id: str | None) -> AppError:
    return AppError(
        "CONVERSION_IN_PROGRESS",
        "This conversion is already being processed. Checking its status is safe; do not resubmit.",
        409,
        retryable=True,
        details={"transaction_id": transaction_id},
    )
