# 07 — Testing and Verification

## Required scenarios
T1 Normal: seed USD 25,000 and USDC-Solana 5,000; quote gross 10,000 USD; fee 50 USD; net 9,950; rate 1:1; confirm. Expect USD 15,000, USDC 14,950 and exactly one transaction.
T2 Expired quote: expire before confirm; expect QUOTE_EXPIRED, unchanged balances and no completed transaction.
T3 Ambiguous response: simulate timeout after DB commit; query original key; expect original completed transaction, balances changed once and one transaction row.

T4 Double-click (concurrent confirm): fire two confirms in parallel threads (a) with the same key, (b) with different keys on the same quote, (c) on two different quotes each worth 60% of available balance. Expect exactly one conversion in each case and no negative balance; the loser gets CONVERSION_IN_PROGRESS/replay, QUOTE_ALREADY_USED or INSUFFICIENT_BALANCE respectively.
T5 Reserve then failure: inject failure before settle; expect release, with available/reserved/pending back to the starting values and transaction FAILED.

T6 Uncertain commit: connection lost during settlement COMMIT. (a) Settlement committed and recovery reads the records → COMPLETED, no review. (b) Settlement rolled back and recovery reads the records → released exactly once (FAILED), no review. (c) Recovery cannot establish the outcome → REVIEW_REQUIRED, funds stay reserved, customer sees Under review, exactly one review case and one simulated ops email with the full evidence package, no customer exposure, and no balance change from notification or escalation. The reviewer resolution is validated against evidence.

## Additional tests
Insufficient balance; unsupported pair (e.g. USD→USDT-Solana, USDC-Base→INR); same account; zero/negative amount; excess precision; same key/same payload; same key/different payload; injected mid-transaction failure rollback; destination rounding; USDC network mismatch; reconcile releases stuck RESERVED.

## Invariants
No negative balance. One transaction per idempotency key/quote. Check-and-reserve is a single conditional update. Source (available + reserved) delta equals gross debit. Destination available delta equals credit after settle. Reserved/pending return to baseline after settle or release. Quote consumed once. No partial update. Frontend never writes balances.

## AI correction record
Record a real AI-generated mistake only after it occurs. Candidate: generated code retries timed-out confirmation with a new idempotency key. Correct by retaining/reusing key and querying status. Capture original mistake, failing test, correction and passing verification; do not fabricate.

## Final report
Commands run, test results, scenario outputs, before/after balances, duplicate retry evidence, rollback evidence and known limitations.
