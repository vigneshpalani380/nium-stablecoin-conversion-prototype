# B001 — Configuration and Seed Data

**Owner:** Backend Agent  
**Status:** DONE  
**Depends on:** P001  
**Read:** 00_MASTER_PRD.md, 01_PRODUCT_SCOPE.md, 02_BACKEND_SPEC.md, 03_DATA_MODEL.md

## Objective
Implement currencies/assets/networks, enabled pairs, fees, precision, quote TTL and deterministic demo balances.

## Scope
Configure USD, INR, USDC-Solana, USDC-Base, USDT-Solana (with precision); enabled pairs USDC-Solana↔USD and USDC-Solana↔INR defined in config and seeded into `conversion_pairs`; 0.5% fee; 30s TTL; mock rates. Seed one demo marketplace with available balances (reserved/pending = 0).

## Acceptance criteria
- Pairs are data-driven; network-specific accounts distinct; seed repeatable; no live pricing.
- Money uses Decimal/string representation; no floating-point arithmetic.
- No live funds, paid integrations or production credentials.
- No unrelated files or behaviour changed.

## Allowed files
`backend/config/**`, `backend/seed/**`, `tests/config/**`

## Out of scope
- Changing master product decisions.
- Adding a separate `ledger_entries` table.
- Live BitGo/blockchain integration.
- Production deployment.

## Verification
Run relevant tests and report exact commands/results, files changed, deviations and unresolved issues before marking DONE.
