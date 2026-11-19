# 01 — Product Scope

## User
Marketplace treasury/finance operator using the Nium business wallet.

## Prototype accounts
USD, INR, USDC-Solana, USDC-Base, USDT-Solana. Each asset/network combination is a distinct account; fiat accounts have no network.

## Initial configured pairs
USDC-Solana→USD; USD→USDC-Solana; USDC-Solana→INR; INR→USDC-Solana. Defined in backend config and seeded into a `conversion_pairs` table; changing pairs is a config/seed change, not a code change. USDC-Base and USDT-Solana accounts are seeded but have no enabled pairs. These are prototype configurations, not a claim that any pair is approved for production. (Revised by product owner, 2026-11-19.)

## Inputs
Source account, destination account, gross source amount; customer context is seeded; confirmation requires a client-generated idempotency key.

## Quote output
Quote ID, source/destination, gross amount, fee rate/amount/currency, net source, exchange rate, destination amount, created/expiry timestamps and status.

## Confirmation output
Transaction ID/status, source/destination assets and networks, gross/fee/net/destination amounts, rate, previous/resulting balances for both accounts, timestamps and reference.

## Balance behaviour
Each account has `available_balance` (spendable), `reserved_balance` (held for in-flight outgoing conversions) and `pending_balance` (incoming, not yet spendable). (Revised by product owner, 2026-11-19: reservation replaces the earlier no-reservation model.)

| Phase | Source | Destination | Txn status |
|---|---|---|---|
| Reserve | available −G, reserved +G | pending +D | RESERVED |
| Settle | reserved −G | pending −D, available +D | COMPLETED |
| Release (failure) | reserved −G, available +G | pending −D | FAILED |

The reserve step is a single conditional UPDATE that checks `available_balance >= G` and moves the funds, so check and reserve are atomic. Zero rows updated means INSUFFICIENT_BALANCE. Each phase is one DB transaction. Fee is recorded in the transaction; no fee-revenue account is modelled. Backend alone updates balances. Stuck RESERVED transactions are released by a reconcile step (demo endpoint and app startup).

## Statuses
Quote: OPEN, CONFIRMED, EXPIRED, CANCELLED.
Transaction: RESERVED, COMPLETED, FAILED, REVIEW_REQUIRED (customer label "Under review").

## Uncertain settlement outcome (added 2026-11-19)
If confirmation is lost during the settlement COMMIT, the outcome is uncertain, not failed. Automated recovery inspects the authoritative records using the original conversion ID and idempotency key: committed → COMPLETED; rolled back → release the reservation exactly once (FAILED); cannot establish → REVIEW_REQUIRED. At that point automation stops (no retry, no new key, no release, no speculative credit), funds stay reserved, the customer sees Under review, and one internal review case plus one simulated email to Nium Operations is created. Human review is an internal process, not part of the customer app; see `docs/operations_review_procedure.md`. Only known pre-commit failures release the reservation directly.

## Errors
Unsupported pair, same account, invalid amount, precision error, insufficient balance, expired quote, quote already used, idempotency conflict, conversion in progress (duplicate confirm while the first is in flight), ambiguous response, internal failure with rollback/release.

## Exclusions
No deposit/withdrawal, on-chain movement, screening, custody operations, partner reconciliation or treasury rebalance.
