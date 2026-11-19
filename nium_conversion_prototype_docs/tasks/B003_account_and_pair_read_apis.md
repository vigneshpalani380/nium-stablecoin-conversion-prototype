# B003 — Account and Pair Read APIs

**Owner:** Backend Agent  
**Status:** DONE  
**Depends on:** B002  
**Read:** 02_BACKEND_SPEC.md, 04_API_SPEC.md, 05_UX_SPEC.md

## Objective
Expose current balances and enabled pairs.

## Scope
Implement GET accounts and GET conversion config; no balance mutation endpoint.

## Acceptance criteria
- UI can load balances and pairs; unsupported pairs absent; network identity tested.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`backend/api/accounts/**`, `backend/api/config/**`, `backend/schemas/**`, `tests/api/**`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
