# 02 — Backend Specification

## Architecture
FastAPI with routers (HTTP only), Pydantic schemas, services (domain rules), repositories (persistence), central config and deterministic mock pricing adapter. Controllers contain no domain logic.

## Services
- Account: fetch accounts/balances; never accept client balance updates.
- Pair/config: enabled pairs, fee, precision, quote TTL.
- Quote: validate pair/amount, calculate fee/net/destination, persist expiry; never mutate balances.
- Conversion: validate quote, idempotency and balance; atomically update two accounts and insert conversion transaction.
- Transaction query: fetch by transaction ID or idempotency key.

## Atomic confirmation
Within one DB transaction: validate quote and balance; capture previous balances; calculate new balances; update both accounts; insert conversion record; persist idempotency response; commit. Any failure rolls back all changes. Use transaction boundaries/locking or version checks appropriate to chosen DB.

## Idempotency
Required `Idempotency-Key` on confirmation. Store customer, key, request fingerprint, transaction ID and result. Unique customer+key. Same key/same payload returns original result. Same key/different payload returns 409. On timeout, client queries original key; do not create a new key.

## Money
Use Decimal end-to-end; never binary float. Store decimal strings or fixed decimal columns. Configure precision by asset. Use explicit rounding (ROUND_HALF_UP for prototype unless changed). Quote rate precision retained; destination amount rounded to destination precision.

## Pricing
Deterministic seeded mock rates, marked SIMULATED. Quote TTL 30 seconds configurable. Pricing adapter isolated from conversion logic.

## HTTP errors
400 invalid amount/pair/same account; 404 missing account/quote/transaction; 409 insufficient balance/expired quote/idempotency conflict; 422 schema validation; 500 unexpected failure with rollback.

## Logging
Structured request ID, customer, quote, transaction, idempotency fingerprint, state transition and error code. No secrets.

## Runtime AI
None required. All pricing, financial calculations and ledger/balance changes are deterministic.
