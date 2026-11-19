# B005 — Conversion Confirmation and Atomic Update

**Owner:** Backend Agent  
**Status:** DONE  
**Depends on:** B004  
**Read:** 00_MASTER_PRD.md, 02_BACKEND_SPEC.md, 03_DATA_MODEL.md

## Objective
Execute quote as reserve → settle (or release) with atomic account updates plus conversion record.

## Scope
Revalidate quote/expiry; consume quote with a conditional OPEN→CONFIRMED update; atomic check-and-reserve in one conditional UPDATE (available −G, reserved +G; destination pending +D); settle (reserved −G; pending −D, available +D); release on failure; capture before/after snapshots; each phase one DB transaction.

## Acceptance criteria
- Each phase commits atomically; concurrent confirms cannot overdraw; injected failure before commit rolls back; failure before settle releases the reservation.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`backend/services/conversions/**`, `backend/repositories/**`, `tests/conversions/**`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
