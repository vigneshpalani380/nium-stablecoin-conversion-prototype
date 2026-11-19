# D001 — Visual Tokens and Component Styling

**Owner:** Design/Frontend Agent  
**Status:** DONE  
**Depends on:** P001  
**Read:** 05_UX_SPEC.md, 06_BRAND_SPEC.md

## Objective
Implement restrained business-fintech visual system.

## Scope
Add colour/type/spacing/status/form/card/table tokens; no invented official logo.

## Acceptance criteria
- Consistent styling, accessible focus and text status labels.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`frontend/src/styles/**`, `frontend/src/components/ui/**`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
