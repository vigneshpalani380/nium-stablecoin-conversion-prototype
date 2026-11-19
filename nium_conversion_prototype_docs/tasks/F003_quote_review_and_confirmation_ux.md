# F003 — Quote Review and Confirmation UX

**Owner:** Frontend Agent  
**Status:** DONE  
**Depends on:** F002, B004, B006  
**Read:** 00_MASTER_PRD.md, 04_API_SPEC.md, 05_UX_SPEC.md

## Objective
Build quote review and safe confirmation.

## Scope
Show gross, fee, net source, rate, destination and expiry; confirm with one idempotency key; prevent double-click.

## Acceptance criteria
- Quote matches backend; expired quote refreshes; retry reuses key.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`frontend/src/features/conversion/quote/**`, `frontend/src/api/**`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
