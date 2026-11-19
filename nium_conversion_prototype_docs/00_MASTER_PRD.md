# 00 — Master Product Requirements Document
**Version:** 0.1 | **Status:** Draft implementation baseline

## 1. Product
A conversion workflow inside the Nium multi-currency business wallet. A marketplace user converts between enabled fiat and stablecoin balances, reviews a quote, confirms it and sees updated balances and transaction history.

## 2. User/problem
Primary user: treasury/finance operator at a marketplace/platform managing cross-border seller, supplier and contractor payouts. They need fiat and stablecoin liquidity in one wallet and a simple way to convert when required.

## 3. Prototype goals
Demonstrate currency/asset/network-specific accounts, configured pairs, quote/fee calculation, quote expiry, transaction persistence, atomic balance updates, idempotency, uncertain-response recovery and customer-facing results.

## 4. In scope
- Synthetic customer/accounts and seeded balances.
- USD, INR, USDC-Solana, USDC-Base, USDT-Solana.
- Config-driven enabled pairs, seeded from config: USDC-Solana↔USD and USDC-Solana↔INR (4 directed pairs). USDC-Base and USDT-Solana accounts exist but have no enabled pairs.
- 0.5% conversion fee.
- Deterministic mock pricing adapter.
- Quote generation, 30-second expiry, confirmation and transaction retrieval.
- Balances in `accounts` split into available, reserved and pending.
- Source reservation before execution: an atomic check-and-reserve (available → reserved) in one conditional DB update.
- One `conversion_transactions` row per conversion with both sides and before/after balance snapshots.
- Normal, expired-quote and ambiguous-timeout scenarios.
- Automated tests for balance correctness, idempotency and atomicity.

## 5. Out of scope
Live BitGo/market pricing, blockchain movement, deposits/withdrawals, gas, treasury rebalancing, mint/redeem, KYC/sanctions, production authentication, scheduled conversion, full accounting GL, runtime AI.

## 6. Main journey
1. Load wallet balances.
2. Select source account, destination account and gross source amount.
3. Validate pair, amount and available balance.
4. Request quote.
5. Display rate, fee, net source, destination amount and expiry.
6. User confirms.
7. Backend revalidates quote and idempotency, then atomically checks and reserves the source (available −G, reserved +G; destination pending +D) and records the transaction as RESERVED.
8. Backend settles atomically (source reserved −G; destination pending −D, available +D) and marks the transaction COMPLETED. On failure it releases the reservation and marks the transaction FAILED.
9. UI shows result, updated balances and transaction detail.
10. On uncertain response, query the original transaction/idempotency key; never blindly submit a new conversion.

## 7. Core rules
- Account identity is customer + asset/currency + network. Fiat has no network.
- USDC-Solana and USDC-Base are separate accounts.
- `accounts` owns available, reserved and pending balances; frontend cannot write balances.
- The balance check and the reservation are one conditional UPDATE (`WHERE available_balance >= G`), so concurrent confirms (e.g. a double-click) can never both pass when the balance covers only one.
- `conversion_transactions` is the conversion/audit record. No separate ledger-entry table.
- In each phase (reserve, settle, release), the account updates, the transaction write and the idempotency write commit or roll back together.
- Same idempotency key + same request returns original result; same key + different payload returns conflict.
- Expired quotes cannot execute.
- Timeout is not proof of failure.
- Only configured pairs are available.
- Customer conversion does not trigger on-chain transfer or an immediate BitGo trade.

## 8. Pricing convention
Prototype assumption: fee = 0.5% of gross source amount, denominated/deducted in source currency. `net_source = gross_source - fee`; `destination_amount = net_source × quote_rate`, rounded to destination precision. Display gross, fee, net and destination separately. No extra FX markup or internal book-transfer fee. Keep the convention configurable.

## 9. Required scenarios
**Normal:** valid pair, sufficient balance, live simulated quote; confirm once; both balances and one transaction update.
**Exception:** quote expires before confirmation; reject with `QUOTE_EXPIRED`; no balance change.
**Ambiguous:** backend commits, response is lost/times out; client queries original idempotency key and receives original result; no second conversion.

## 10. Acceptance criteria
- Valid pair selection and quote.
- Reject unsupported pair, same account, non-positive/overprecision amount and insufficient balance.
- Quote shows quote ID, rate, fee, gross/net source, destination amount and expiry.
- Expired quote cannot execute.
- Successful conversion atomically updates both balances and stores one transaction with before/after balances.
- Idempotent retry returns original result; mismatched payload conflicts.
- Timeout recovery does not duplicate conversion.
- Tests prove invariants and rollback.

## 11. Success demo
Start with seeded balances, perform conversion, inspect updated balances and stored transaction, then demonstrate expired and ambiguous scenarios with test evidence.
