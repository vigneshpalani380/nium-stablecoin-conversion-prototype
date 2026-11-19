# Q003 — AI Correction Record

**Owner:** QA/Product Agent  
**Status:** DONE  
**Depends on:** Q001, Q002  
**Read:** 07_TESTING_AND_VERIFICATION.md, 08_BUILD_AND_AGENT_GUIDE.md

## Objective
Record one actual AI-generated mistake and its correction.

## Scope
Capture actual generated mistake, failing evidence, correction and passing verification. Do not fabricate.

## Acceptance criteria
- Record has mistake, risk, correction, failing test and passing test.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`docs/correction_record.md`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
