# B006 — Idempotency and Uncertain Outcome Recovery

**Owner:** Backend Agent  
**Status:** DONE  
**Depends on:** B005  
**Read:** 02_BACKEND_SPEC.md, 04_API_SPEC.md, 07_TESTING_AND_VERIFICATION.md

## Objective
Prevent duplicate conversions and support status recovery.

## Scope
Require Idempotency-Key; `idempotency_records` (unique customer+key) inserted in the reservation transaction; store request fingerprint/state/result; same payload replays (or 409 CONVERSION_IN_PROGRESS while in flight); different payload conflicts; timeout-after-commit simulation; double-click concurrency.

## Acceptance criteria
- Retry returns original result; payload mismatch 409; ambiguous response resolves without second movement.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`backend/services/idempotency/**`, `backend/api/conversions/**`, `backend/models/**`, `tests/idempotency/**`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
