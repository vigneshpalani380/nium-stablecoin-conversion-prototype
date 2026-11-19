# B004 — Quote Engine

**Owner:** Backend Agent  
**Status:** DONE  
**Depends on:** B003  
**Read:** 00_MASTER_PRD.md, 01_PRODUCT_SCOPE.md, 02_BACKEND_SPEC.md, 03_DATA_MODEL.md, 04_API_SPEC.md

## Objective
Implement deterministic quote, fee, precision and expiry.

## Scope
Validate pair/amount; calculate source fee, net source and destination; persist quote; never change balances.

## Acceptance criteria
- Quote complete; Decimal used; invalid/insufficient inputs rejected; no balance movement.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`backend/services/quotes/**`, `backend/adapters/pricing/**`, `backend/api/quotes/**`, `tests/quotes/**`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
