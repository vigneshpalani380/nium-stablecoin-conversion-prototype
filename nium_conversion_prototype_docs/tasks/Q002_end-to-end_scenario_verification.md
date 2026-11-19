# Q002 — End-to-End Scenario Verification

**Owner:** QA Agent  
**Status:** DONE  
**Depends on:** F004, F005, Q001  
**Read:** 00_MASTER_PRD.md, 05_UX_SPEC.md, 07_TESTING_AND_VERIFICATION.md

## Objective
Verify three customer journeys end to end.

## Scope
Run UI/API normal, expired and ambiguous scenarios; capture actual evidence.

## Acceptance criteria
- All scenarios pass with recorded outputs and before/after balances.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`tests/e2e/**`, `docs/evidence/**`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
