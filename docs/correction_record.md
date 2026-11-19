# AI Correction Record

## 1. Non-atomic balance check and reservation (caught by human review)

**AI-generated build**

The initial implementation plan proposed checking the account's available balance and then performing a separate database update to reserve the conversion amount.

**Human correction**

I identified a concurrency risk: two simultaneous conversion requests could both pass the balance check using the same available balance, potentially allowing the account to reserve more funds than it held.

I required the balance check and reservation to happen atomically in the database.

**Changes made**

The implementation was changed to use a conditional SQL update:

`UPDATE accounts ... WHERE available_minor >= :amount`

The update moves funds from available to reserved only when sufficient funds remain. If no row is updated, the request returns `INSUFFICIENT_BALANCE` without changing the account balance.

**Verification**

Verified through backend balance and concurrent-confirmation tests. The E2E double-click scenario was also tested over HTTP. Repeated E2E runs passed, with evidence recorded in `docs/evidence/e2e_scenarios.md`.

---
