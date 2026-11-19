# B007 — Transaction History and Detail API

**Owner:** Backend Agent  
**Status:** DONE  
**Depends on:** B006  
**Read:** 02_BACKEND_SPEC.md, 03_DATA_MODEL.md, 04_API_SPEC.md, 05_UX_SPEC.md

## Objective
Expose conversion history and detail.

## Scope
Return persisted amounts, rate, fee, status, asset/network and before/after balances.

## Acceptance criteria
- History and detail reflect stored transactions, no fabricated frontend data.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`backend/api/transactions/**`, `backend/services/transactions/**`, `backend/schemas/**`, `tests/transactions/**`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
