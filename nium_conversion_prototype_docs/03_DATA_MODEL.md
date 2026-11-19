# 03 — Data Model

## `accounts`
One row per customer + asset/currency + network.
Fields: id, customer_id, asset_code, asset_type (FIAT/STABLECOIN), network (nullable for fiat), precision, available_balance, reserved_balance, pending_balance, status, version, created_at, updated_at.
Unique identity: customer + asset_code + network (normalise null network for fiat).
Balances are stored as INTEGER minor units scaled by the asset's precision (fiat 2, stablecoins 6) and converted to/from Decimal in code. This keeps money exact and lets SQLite do the atomic conditional UPDATE in SQL. CHECK constraints keep every balance ≥ 0.

## `conversion_pairs`
Seeded from backend config. Fields: id, source_asset_code, source_network, destination_asset_code, destination_network, enabled, simulated_rate. Unique on source + destination.

## `idempotency_records`
Fields: id, customer_id, idempotency_key, request_fingerprint, state (IN_PROGRESS/COMPLETED/FAILED), transaction_id, response_json, created_at, updated_at. Unique: customer + idempotency_key. Inserted in the same DB transaction as the reservation.

## `conversion_quotes`
Fields: id, customer_id, source_account_id, destination_account_id, gross_source_amount, fee_rate, fee_amount, fee_currency, net_source_amount, exchange_rate, destination_amount, rate_source, created_at, expires_at, status.
Quotes do not move balances.

## `conversion_transactions`
The single conversion/audit record for this prototype; no `ledger_entries` table.
Fields: id, customer_id, quote_id, idempotency_key, request_fingerprint, source_account_id, destination_account_id, source_asset_code, source_network, destination_asset_code, destination_network, gross_source_amount, fee_rate, fee_amount, fee_currency, net_source_amount, exchange_rate, destination_amount, before/after snapshots of available, reserved and pending for both source and destination accounts, status (RESERVED/COMPLETED/FAILED/REVIEW_REQUIRED), failure_code, failure_message, created_at, reserved_at, settled_at, released_at.
Unique: quote_id; customer + idempotency_key; transaction ID primary key.

## Internal operations tables (not customer-facing)
- `conversion_events`: audit trail of state transitions (REQUESTED, VALIDATED, RESERVED, SETTLEMENT_ATTEMPTED, OUTCOME_UNCERTAIN, AUTOMATED_RECOVERY_ATTEMPT, HUMAN_REVIEW_REQUIRED, NOTIFICATION_QUEUED, REVIEW_*), with actor and detail.
- `review_cases`: one per unresolved conversion (unique transaction_id). Status OPEN/ESCALATED/RESOLVED_COMMITTED/RESOLVED_NOT_COMMITTED, reason, evidence, reviewer, note, timestamps.
- `internal_notifications`: simulated emails (channel EMAIL, recipient group OPERATIONS, priority, subject, body, structured payload, status QUEUED). Unique per transaction + event, so notification creation is idempotent.

## Why no separate ledger entries
One conversion moves value between exactly two accounts. A single transaction row captures both sides and balance snapshots. This avoids duplicate representation for the narrow prototype. It is not a complete accounting journal/general ledger; production accounting may require immutable debit/credit postings, reversals and accounting-period controls.

## Invariants
After settlement: source (available + reserved) = before − gross source amount; destination available = before + destination amount; reserved and pending return to their pre-conversion values.
After release: all four balances equal their pre-conversion values.
No balance is ever negative. Fee is included in gross source debit and stored as a transaction field. No separate fee-revenue account in this prototype.

## Example
USD available 25,000; USDC-Solana available 5,000; gross 10,000 USD; fee 50 USD; net source 9,950 USD; rate 1:1; destination 9,950 USDC.
After reserve: USD available 15,000, reserved 10,000; USDC-Solana available 5,000, pending 9,950.
After settle: USD available 15,000, reserved 0; USDC-Solana available 14,950, pending 0.
