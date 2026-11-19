# 05 — UX Specification

## Experience
A clear business-wallet conversion journey. User must understand source, destination, fee, rate, amount received and completion status.

## Main screen
Header `Wallet`; navigation `Balances | Convert | Activity`.
Show USD, INR, USDC-Solana, USDC-Base and USDT-Solana balances. Network labels always visible.

## Form
Source account, destination account filtered by enabled pair, gross source amount, available balance and Get quote. Block same account, unsupported pair, non-positive amount and unsupported precision. Reset quote when inputs change.

## Quote review
Show gross source, fee rate/amount/currency, net source, rate, destination amount, expiry countdown, Confirm and Cancel. Label rate `Simulated demo rate`. Never imply live market pricing.

## Confirm/result
Disable button while request is in flight. Reuse same idempotency key on retry. On success show transaction reference and before/after balances; refresh balances from API.

## Ambiguous response
On timeout retain original idempotency key, show `Checking conversion status…`, query original transaction. If completed, show original result. If unresolved, explain status is not confirmed and provide reference. Never invite blind resubmission.

## Activity
Recent conversions: date/time, from/to amounts and assets, fee, status, transaction ID. Detail shows rate, quote and before/after balances.

## Errors
Actionable messages for expired quote, insufficient balance, unsupported pair, idempotency conflict and uncertain outcome.

## Accessibility/responsive
Keyboard accessible; visible labels/focus; status not colour-only; responsive desktop/tablet and usable at 360px mobile width.
