"""Builds the SIMULATED internal email to Nium Operations for an unresolved conversion outcome.

No email is sent. The notification is stored (internal_notifications), logged, and inspectable via
the internal operations API.
"""
from __future__ import annotations

from typing import Any

from backend.domain.money import format_minor
from backend.domain.support import display_name, iso
from backend.models.entities import ConversionTransaction

SUBJECT = "Action Required – Conversion Outcome Unresolved"
EVENT = "CONVERSION_REVIEW_REQUIRED"

REVIEWER_ACTIONS = [
    "Inspect the authoritative database transaction and account records "
    "(GET /internal/v1/review-cases/{case_id}/inspection).",
    "Establish whether the source debit, destination credit and completed conversion record committed atomically.",
    "If settlement committed, confirm the completed outcome (action CONFIRM_COMMITTED).",
    "If settlement did not commit, establish that it was rolled back and authorise the one-time reservation "
    "release (action CONFIRM_NOT_COMMITTED).",
    "If evidence remains inconclusive, escalate to the engineering/data operations owner and keep the "
    "transaction unresolved (action ESCALATE).",
]

PROHIBITED = ("Never initiate a new conversion, generate a new idempotency key, or release funds based "
              "solely on the original timeout.")


def build_review_notification(
    txn: ConversionTransaction,
    case_id: str,
    triggered_at,
    settlement_attempted_at,
    db_error: str,
    attempts: list[dict],
    probe: dict,
    reason: str,
) -> tuple[str, str, dict[str, Any]]:
    sp, dp = txn.source_precision, txn.destination_precision
    src_name = display_name(txn.source_asset_code, txn.source_network)
    dst_name = display_name(txn.destination_asset_code, txn.destination_network)
    gross = format_minor(txn.gross_source_minor, sp)
    dest = format_minor(txn.destination_minor, dp)

    # Position immediately after the reservation (from the reservation snapshot the application holds).
    position = {
        "basis": "Last known position after reservation (settlement outcome unconfirmed)",
        "source_available": format_minor(txn.src_available_before - txn.gross_source_minor, sp),
        "source_reserved": format_minor(txn.src_reserved_before + txn.gross_source_minor, sp),
        "destination_available": format_minor(txn.dst_available_before, dp),
        "destination_pending": format_minor(txn.dst_pending_before + txn.destination_minor, dp),
        "before_reservation": {
            "source": {"available": format_minor(txn.src_available_before, sp),
                       "reserved": format_minor(txn.src_reserved_before, sp),
                       "pending": format_minor(txn.src_pending_before, sp)},
            "destination": {"available": format_minor(txn.dst_available_before, dp),
                            "reserved": format_minor(txn.dst_reserved_before, dp),
                            "pending": format_minor(txn.dst_pending_before, dp)},
        },
        "after_settlement": "Unknown — this is what the reviewer must establish.",
    }
    explanation = (
        f"The conversion request was submitted and {txn.source_asset_code} {gross} was reserved. "
        "The application lost its database connection during the settlement commit and did not receive "
        "confirmation. Automated recovery using the original conversion ID and idempotency key could not "
        "establish whether settlement committed. The funds remain reserved. No further conversion or "
        "automatic reservation release will be attempted."
    )
    payload: dict[str, Any] = {
        "simulated": True,
        "delivery_note": "SIMULATED EMAIL — stored and logged only; no email was sent.",
        "header": {
            "subject": SUBJECT, "priority": "HIGH", "review_case_id": case_id,
            "customer_id": txn.customer_id, "source_account_id": txn.source_account_id,
            "destination_account_id": txn.destination_account_id,
            "conversion_id": txn.id, "idempotency_key": txn.idempotency_key, "review_triggered_at": iso(triggered_at),
        },
        "transaction": {
            "source": f"{src_name} {gross}", "destination_expected": f"{dst_name} {dest}",
            "conversion_rate": f"1 {txn.source_asset_code} = {txn.exchange_rate} {txn.destination_asset_code} ({txn.rate_source})",
            "conversion_fee": f"{format_minor(txn.fee_minor, sp)} {txn.fee_currency} ({txn.fee_rate})",
            "quote_id": txn.quote_id, "original_transaction_timestamp": iso(txn.created_at),
            "last_known_status": "RESERVED — settlement attempted, outcome unknown",
        },
        "financial_position": position,
        "evidence": {
            "settlement_attempted_at": iso(settlement_attempted_at),
            "database_error": db_error,
            "conversion_record_found": probe.get("conversion_record_found", "UNKNOWN"),
            "source_debit_found": probe.get("source_debit_found", "UNKNOWN"),
            "destination_credit_found": probe.get("destination_credit_found", "UNKNOWN"),
            "idempotency_lookup_result": probe.get("idempotency_lookup_result", "UNKNOWN"),
            "automated_recovery_attempts": attempts,
            "last_known_system_response": "No commit acknowledgement received from the database.",
            "why_automation_stopped": reason,
        },
        "explanation": explanation,
        "required_reviewer_actions": REVIEWER_ACTIONS,
        "prohibited": PROHIBITED,
    }
    return SUBJECT, render_email(payload), payload


def render_email(p: dict[str, Any]) -> str:
    h, t, f, e = p["header"], p["transaction"], p["financial_position"], p["evidence"]
    lines = [
        "[SIMULATED EMAIL — not sent]",
        "To: Nium Operations <operations@nium.example> (group: OPERATIONS)",
        f"Subject: {h['subject']}",
        f"Priority: {h['priority']}",
        "",
        "A. CASE",
        f"  Review case:      {h['review_case_id']}",
        f"  Customer:         {h['customer_id']}  (accounts {h['source_account_id']} → {h['destination_account_id']})",
        f"  Conversion ID:    {h['conversion_id']}",
        f"  Idempotency key:  {h['idempotency_key']}",
        f"  Review triggered: {h['review_triggered_at']}",
        "",
        "B. TRANSACTION",
        f"  Source:           {t['source']}",
        f"  Destination:      {t['destination_expected']} (expected)",
        f"  Rate:             {t['conversion_rate']}",
        f"  Fee:              {t['conversion_fee']}",
        f"  Created:          {t['original_transaction_timestamp']}",
        f"  Last known state: {t['last_known_status']}",
        "",
        f"C. FINANCIAL POSITION — {f['basis']}",
        f"  Source available:        {f['source_available']}",
        f"  Source reserved:         {f['source_reserved']}",
        f"  Destination available:   {f['destination_available']}",
        f"  Destination pending:     {f['destination_pending']}",
        f"  After settlement:        {f['after_settlement']}",
        "",
        "D. EVIDENCE",
        f"  Settlement attempted:    {e['settlement_attempted_at']}",
        f"  Database error:          {e['database_error']}",
        f"  Conversion record found: {e['conversion_record_found']}",
        f"  Source debit found:      {e['source_debit_found']}",
        f"  Destination credit found:{' '}{e['destination_credit_found']}",
        f"  Idempotency lookup:      {e['idempotency_lookup_result']}",
        "  Recovery attempts:",
        *[f"    #{a['attempt']} {a['at']} → {a['result']}{(' (' + a['error'] + ')') if a.get('error') else ''}"
          for a in e["automated_recovery_attempts"]],
        f"  Last system response:    {e['last_known_system_response']}",
        f"  Why automation stopped:  {e['why_automation_stopped']}",
        "",
        "E. WHAT HAPPENED",
        f"  {p['explanation']}",
        "",
        "F. REQUIRED ACTIONS",
        *[f"  {i}. {a}" for i, a in enumerate(p["required_reviewer_actions"], 1)],
        f"  {p['prohibited']}",
    ]
    return "\n".join(lines)
