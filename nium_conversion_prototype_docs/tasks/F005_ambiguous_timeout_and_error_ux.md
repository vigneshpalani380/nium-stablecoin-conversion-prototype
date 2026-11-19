# F005 — Ambiguous Timeout and Error UX

**Owner:** Frontend Agent  
**Status:** DONE  
**Depends on:** F003, B006  
**Read:** 02_BACKEND_SPEC.md, 04_API_SPEC.md, 05_UX_SPEC.md

## Objective
Handle quote expiry, insufficient balance, API errors and uncertain outcome.

## Scope
On timeout retain original key and query original transaction; never blindly resubmit.

## Acceptance criteria
- Ambiguous scenario returns original result or remains unresolved; no duplicate request.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`frontend/src/features/conversion/**`, `frontend/src/api/**`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
