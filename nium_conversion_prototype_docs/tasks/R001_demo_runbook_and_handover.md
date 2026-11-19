# R001 — Demo Runbook and Handover

**Owner:** Documentation/Product Agent  
**Status:** DONE  
**Depends on:** Q002, Q003  
**Read:** 00_MASTER_PRD.md, 01_PRODUCT_SCOPE.md, 02_BACKEND_SPEC.md, 04_API_SPEC.md, 07_TESTING_AND_VERIFICATION.md

## Objective
Prepare repeatable run and interview demo.

## Scope
Document setup, seed, run commands, normal/expired/ambiguous demo, live-change exercise and limitations.

## Acceptance criteria
- Clean checkout can run and reproduce scenarios without paid integrations.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`README.md`, `docs/demo_runbook.md`, `docs/known_limitations.md`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
