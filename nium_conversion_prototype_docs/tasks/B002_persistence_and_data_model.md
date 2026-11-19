# B002 — Persistence and Data Model

**Owner:** Backend Agent  
**Status:** DONE  
**Depends on:** B001  
**Read:** 00_MASTER_PRD.md, 02_BACKEND_SPEC.md, 03_DATA_MODEL.md

## Objective
Create accounts, conversion_pairs, conversion_quotes, conversion_transactions and idempotency_records models/migrations.

## Scope
Implement available/reserved/pending balances as integer minor units with non-negative CHECKs, and one conversion/audit record with both sides and before/after snapshots. No ledger_entries.

## Acceptance criteria
- Unique quote/idempotency constraints; decimal precision preserved; schema matches spec.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`backend/models/**`, `backend/db/**`, `backend/migrations/**`, `tests/models/**`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
