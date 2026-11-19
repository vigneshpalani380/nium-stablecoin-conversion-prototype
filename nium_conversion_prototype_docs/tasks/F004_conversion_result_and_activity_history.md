# F004 — Conversion Result and Activity History

**Owner:** Frontend Agent  
**Status:** DONE  
**Depends on:** F003, B007  
**Read:** 03_DATA_MODEL.md, 04_API_SPEC.md, 05_UX_SPEC.md

## Objective
Show result, balances and transaction history.

## Scope
Refresh balances from API; display transaction ID, before/after balances, fee/rate/status; activity list.

## Acceptance criteria
- Completed conversion appears once; displayed balances match API.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`frontend/src/features/activity/**`, `frontend/src/features/conversion/result/**`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
