# Nium Stablecoin Wallet — Internal Conversion Prototype
Documentation pack v0.1.

## Read order
`00_MASTER_PRD.md` → `01_PRODUCT_SCOPE.md` → `02_BACKEND_SPEC.md` → `03_DATA_MODEL.md` → `04_API_SPEC.md` → `05_UX_SPEC.md` → `06_BRAND_SPEC.md` → `07_TESTING_AND_VERIFICATION.md` → `08_BUILD_AND_AGENT_GUIDE.md` → `AGENT_MATRIX.md`.

## Architecture decisions
- `accounts` stores available, reserved and pending balances per customer + asset/currency + network. Confirmation reserves the source first with one atomic check-and-reserve update.
- `conversion_transactions` is the single conversion/audit record for this prototype. No separate `ledger_entries` table.
- Each conversion record stores both source and destination amounts, fees, rate, before/after balances, status and idempotency key.
- Updating both account balances and inserting the conversion record must be one atomic database transaction.
- This is a simplified operational ledger model, not a full accounting journal/general ledger.

## Assumptions
- 0.5% fee per conversion, denominated in source currency and deducted from gross source amount for this prototype.
- Prototype accounts: USD, INR, USDC-Solana, USDC-Base, USDT-Solana.
- Enabled pairs are configuration-driven and seeded: USDC-Solana↔USD and USDC-Solana↔INR.
- 30-second simulated quote validity.
- Deterministic mock prices, clearly labelled simulated.
- No live BitGo, blockchain, bank or paid API integrations.
- Internal customer conversion does not cause an on-chain transfer or an immediate BitGo trade; treasury rebalancing is out of scope.
