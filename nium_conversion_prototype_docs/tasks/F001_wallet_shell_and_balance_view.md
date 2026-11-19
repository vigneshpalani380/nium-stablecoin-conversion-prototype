# F001 — Wallet Shell and Balance View

**Owner:** Frontend Agent  
**Status:** DONE  
**Depends on:** B003  
**Read:** 00_MASTER_PRD.md, 01_PRODUCT_SCOPE.md, 05_UX_SPEC.md, 06_BRAND_SPEC.md

## Objective
Build wallet shell and account balance cards.

## Scope
Load accounts from API; display fiat/stablecoin and explicit network labels; responsive layout.

## Acceptance criteria
- All seeded accounts visible; networks distinguished; no hard-coded balance mutation.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`frontend/src/app/**`, `frontend/src/components/accounts/**`, `frontend/src/styles/**`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
