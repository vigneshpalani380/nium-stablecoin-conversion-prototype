# Known Limitations

This is an interview prototype, not production software.

## Scope (intentional)

- **No real money movement.** There is no blockchain, BitGo, bank or market-data integration. Rates are deterministic and labelled `SIMULATED`.
- **No authentication.** A single seeded demo customer is used, with no KYC, sanctions screening or limits.
- **No accounting ledger.** `conversion_transactions` is the only audit record (product decision). Production would need immutable debit/credit postings, reversals and period controls.
- **No fee revenue account.** The fee is recorded on each transaction but not credited anywhere.
- **No treasury rebalancing, deposits or withdrawals.**

## Technical

- **SQLite.** All transactions use `BEGIN IMMEDIATE`, so writers are serialised, and reads are serialised too. This is correct, but throughput is limited. Production would use Postgres, row-level guards (the conditional `UPDATE` pattern carries over unchanged), and `SELECT … FOR UPDATE` where needed.
- **Schema setup.** The schema is created with `metadata.create_all`; there are no migrations (Alembic not added, to avoid unnecessary dependencies). Changing a model requires deleting `wallet.db`.
- **Two-phase in one request.** Reserve and settle are separate DB transactions inside the same HTTP request. A crash between them leaves a `RESERVED` transaction, which is released on startup or by `POST /api/v1/demo/reconcile`. Production would run reconciliation as a scheduled job with alerting.
- **Stuck reservations are released, not settled.** Reconcile treats every stuck reservation as failed. That is safe, but a real system might retry the settle step instead.
- **Idempotency fingerprint.** The fingerprint covers customer + quote, because the confirm body is empty. Keys never expire.
- **Demo fault injection lives in process memory.** It is not shared across multiple server processes. It is enabled only when `WALLET_DEMO_MODE=true` (the default for local runs). Set it to `false` to remove the `/demo` routes.
- **Quote expiry uses server time.** The countdown uses `seconds_remaining` from the server, so client clock skew doesn't matter, but network latency can make the displayed countdown a little generous.

## Ambiguous-outcome simulation
- The uncertain COMMIT and the failing recovery lookups are simulated deterministically (demo faults); there is no real database outage. In the human-review scenario, only the recovery *probe* is made to fail. The escalation record and notification are written to the same SQLite database. Production would write them through a durable outbox or alerting channel that does not depend on the failing database.
- The internal ops API uses a static demo token (`X-Ops-Token`). There is no real identity, authorisation or four-eyes approval.
- No email is sent. Notifications are stored with status `QUEUED` and logged.
- Customers are not actually notified when a case is resolved. Their status updates when they refresh.

## Testing

- **No automated browser-driven E2E.** There is no Playwright or Cypress test of the real UI. UI behaviour is covered by Vitest/Testing Library component tests with a fake API. API behaviour is covered end-to-end against a live server (`tests/e2e`). Manual UI checks follow `docs/demo_runbook.md`.
- **Concurrency tests run against SQLite on one machine.**
