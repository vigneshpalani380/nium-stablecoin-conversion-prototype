# F002 — Conversion Form and Pair Selection

**Owner:** Frontend Agent  
**Status:** DONE  
**Depends on:** F001, B003  
**Read:** 01_PRODUCT_SCOPE.md, 04_API_SPEC.md, 05_UX_SPEC.md, 06_BRAND_SPEC.md

## Objective
Build source/destination selectors and amount input.

## Scope
Load enabled pairs; filter destinations; validate amount/precision; display available source balance; call quote API.

## Acceptance criteria
- Unsupported pairs blocked; same account blocked; backend authoritative.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`frontend/src/features/conversion/form/**`, `frontend/src/api/**`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
