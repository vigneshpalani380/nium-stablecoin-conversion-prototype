# Internal Operations: Unresolved Conversion Outcome

**Audience:** Nium Operations reviewers. This is an internal process and is not part of the customer application.

## When a case is opened

A conversion reaches `REVIEW_REQUIRED` only when **all** of the following are true:

1. The source funds were reserved (available → reserved; the destination amount is held as pending).
2. Settlement was attempted. Settlement is one atomic DB transaction: debit the source, credit the destination, write the completed conversion record, and finalise the idempotency record.
3. The application lost confirmation during the settlement `COMMIT`, so the outcome is **uncertain**. An uncertain outcome is not a failure.
4. **Automated recovery** read the authoritative records using the original conversion ID and idempotency key, and could not establish the outcome. This happens when the lookups keep failing, or when the records match neither a committed nor a rolled-back settlement.

If recovery *can* establish the outcome, no case is opened:
- Committed: the conversion is confirmed as Completed.
- Not committed: the reservation is released once, and the conversion is marked Failed.

## What automation does at the boundary

The system stops financial execution. It does **not**:
- retry settlement,
- create a new idempotency key or a new conversion,
- release the reservation because of the timeout,
- credit the destination speculatively.

It does, in one DB transaction:
- mark the conversion `REVIEW_REQUIRED`,
- open one review case (`RVW-…`),
- queue one simulated email (`NTF-…`) to **OPERATIONS** over **EMAIL**, priority **HIGH**,
- write audit events.

Repeat attempts never create a second case or notification: the database enforces this with unique constraints.

The customer sees **Under review**, with the funds shown as reserved and the destination credit shown as not yet confirmed. The customer never sees case IDs, notes, logs or the notification.

## The notification (simulated email)

**Subject:** "Action Required – Conversion Outcome Unresolved". The notification has six sections:

| Section | Contents |
|---|---|
| A. Case | Review case ID, customer and accounts, conversion ID, idempotency key, time the review was triggered |
| B. Transaction | Source asset and amount, expected destination amount, rate, fee, creation time, last known status |
| C. Financial position | Source available/reserved and destination available/pending after reservation, balances before reservation; the after-settlement position is marked unknown |
| D. Evidence | Settlement attempt time, database error, whether the record, debit and credit were found, idempotency lookup result, each recovery attempt with timestamp and result, last system response, why automation stopped |
| E. What happened | Plain-language explanation |
| F. Required actions | The procedure below |

**No email is sent.** The notification is stored in `internal_notifications`, written to the backend log (`ops.notification.simulated_email`), and readable through the internal API. A sample is in `docs/evidence/sample_ops_notification.txt`.

## Internal API

The internal API lives under `/internal/v1/...`. Every request needs the header `X-Ops-Token: demo-ops-token` (a demo credential; override it with `WALLET_OPS_TOKEN`). In Swagger (http://localhost:8000/docs) these endpoints are grouped under **internal-operations (not customer-facing)**.

| Step | Endpoint |
|---|---|
| Outbox | `GET /internal/v1/notifications` |
| Read the email | `GET /internal/v1/notifications/{notification_id}` (subject, body, structured payload) |
| Case, evidence and audit trail | `GET /internal/v1/review-cases/{case_id}` |
| Inspect authoritative records | `GET /internal/v1/review-cases/{case_id}/inspection` (read-only; returns the evidence and the action it supports) |
| Record the decision | `POST /internal/v1/review-cases/{case_id}/resolution` with `{"action", "reviewer", "note"}` |
| State transitions | `GET /internal/v1/conversions/{conversion_id}/events` |

## Investigation and resolution procedure

1. **Inspect** the authoritative transaction and account records (the inspection endpoint).
2. **Establish atomicity:** check whether the settlement marker, the source debit and the destination credit are all present together, or all absent with the reservation and pending credit still intact.
3. **Option 1 — `CONFIRM_COMMITTED`.** Allowed only when the evidence shows the settlement committed.
   - The conversion becomes Completed and the customer status updates.
   - No money moves; the settlement already happened.
4. **Option 2 — `CONFIRM_NOT_COMMITTED`.** Allowed only when the evidence shows the settlement rolled back.
   - The reservation is released **exactly once**, using the same guarded release that automation uses.
   - The conversion becomes Failed.
5. **Option 3 — `ESCALATE`.** Use this when the evidence is inconclusive.
   - Funds stay reserved and the evidence is preserved.
   - The escalation reason is recorded, balances do not change, and the customer still sees Under review.
   - Hand the case to the engineering/data operations owner.

The backend **refuses** a decision that contradicts the evidence (`409 RESOLUTION_NOT_SUPPORTED_BY_EVIDENCE`). It also refuses any action on an already-resolved case (`409 REVIEW_CASE_CLOSED`).

**Never:**
- initiate a new conversion,
- generate a new idempotency key,
- release funds based solely on the original timeout.

## Audit

The following are kept after resolution:
- the case (reason, evidence, escalation reason, reviewer, note, resolution time and outcome),
- the notification,
- the full event trail: `REQUESTED → VALIDATED → RESERVED → SETTLEMENT_ATTEMPTED → OUTCOME_UNCERTAIN → AUTOMATED_RECOVERY_ATTEMPT ×3 → HUMAN_REVIEW_REQUIRED → NOTIFICATION_QUEUED → REVIEW_ESCALATED / REVIEW_RESOLVED_*`.
