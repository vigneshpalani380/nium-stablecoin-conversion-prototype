# 04 — API Specification
Base path `/api/v1`.

## `GET /accounts`
Returns seeded customer accounts and balances: id, asset_code, asset_type, network, available_balance, reserved_balance, pending_balance (decimal strings), precision, status.

## `GET /conversion/config`
Returns enabled pairs, fee rate, quote TTL and precision. No secrets.

## `POST /conversion/quotes`
Request:
```json
{"source_account_id":"acct-usd","destination_account_id":"acct-usdc-sol","gross_source_amount":"10000.00"}
```
Response includes quote_id, OPEN status, SIMULATED rate source, gross source, fee rate/amount/currency, net source, exchange rate, destination amount, created_at and expires_at.

## `POST /conversion/quotes/{quote_id}/confirm`
Required header `Idempotency-Key`. Quote values are read from persisted quote, never trusted from frontend. Flow: insert idempotency record + consume quote (OPEN→CONFIRMED, conditional) + atomic reserve, then settle. Success returns transaction ID/status, amounts, rate, fee, before/after balances and timestamps.
- Same key, same payload, finished → replay original result.
- Same key, same payload, still in flight → 409 `CONVERSION_IN_PROGRESS` with transaction reference; client polls by key.
- Same key, different payload → 409 `IDEMPOTENCY_CONFLICT`.
- Different key, quote already consumed → 409 `QUOTE_ALREADY_USED`.
- Available balance < gross → 409 `INSUFFICIENT_BALANCE`, no change.

## `GET /conversion/transactions`
Recent conversions for the demo customer, newest first.

## `GET /conversion/transactions/{transaction_id}`
Returns transaction status/details.

## `GET /conversion/transactions/by-idempotency-key/{key}`
Returns original result for uncertain-response recovery; scope to demo customer.

Confirm may also return `202` with status `REVIEW_REQUIRED` when the settlement outcome could not be established; a same-key retry then returns `409 CONVERSION_UNDER_REVIEW`. Customer endpoints never include internal review or notification data, and they hide post-settlement balances while a conversion is under review. Every transaction includes `last_updated_at`.

## Internal operations API (`/internal/v1`, header `X-Ops-Token`, not used by the customer app)
`GET /notifications`, `GET /notifications/{id}`, `GET /review-cases`, `GET /review-cases/{id}`, `GET /review-cases/{id}/inspection`, `POST /review-cases/{id}/resolution` (`CONFIRM_COMMITTED` | `CONFIRM_NOT_COMMITTED` | `ESCALATE`, validated against evidence), `GET /conversions/{id}/events`.

## Demo-only failure injection
Simulate quote expiry, response timeout after commit, failure before commit (rollback), pause after reserve (shows reserved/pending in the UI) and failure before settle (shows release). Uncertain settlement commit: `uncertain_commit` = `COMMITTED` | `ROLLED_BACK` (what really happened), optionally with `recovery_lookup_fails` (forces human review). Plus a reconcile endpoint that releases stuck RESERVED transactions. Disabled outside demo/test mode.

## Error response
```json
{"error":{"code":"QUOTE_EXPIRED","message":"This quote has expired. Request a new quote.","retryable":true,"request_id":"req-demo"}}
```
No stack traces/raw DB errors.
