# Q001 — Backend Financial Invariant Tests

**Owner:** QA Agent  
**Status:** DONE  
**Depends on:** B005, B006  
**Read:** 02_BACKEND_SPEC.md, 03_DATA_MODEL.md, 07_TESTING_AND_VERIFICATION.md

## Objective
Verify financial correctness, atomicity and idempotency.

## Scope
Test normal, insufficient balance, expired quote, unsupported pair, retries, key mismatch, concurrency and rollback.

## Acceptance criteria
- Tests prove one conversion, no negative balance, correct deltas and no partial updates.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`tests/**`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
