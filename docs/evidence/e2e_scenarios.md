# End-to-end scenario evidence

Generated 2026-11-19T10:23:41+00:00 by `tests/e2e/test_scenarios_e2e.py` against a live uvicorn process over HTTP (fresh SQLite DB, seeded balances).


## T1 Normal conversion (USD → USDC-Solana 10,000)

- **quote**: `{"quote_id": "q-a552a92ad1f048b7", "gross_source_amount": "10000.00", "fee_amount": "50.00", "net_source_amount": "9950.00", "exchange_rate": "1.0000", "destination_amount": "9950.000000", "rate_source": "SIMULATED"}`
- **balances_before**: `{"acct-usd": {"available": "25000.00", "reserved": "0.00", "pending": "0.00"}, "acct-usdc-sol": {"available": "5000.000000", "reserved": "0.000000", "pending": "0.000000"}}`
- **balances_after**: `{"acct-usd": {"available": "15000.00", "reserved": "0.00", "pending": "0.00"}, "acct-usdc-sol": {"available": "14950.000000", "reserved": "0.000000", "pending": "0.000000"}}`
- **transaction_status**: `"COMPLETED"`
- **transaction_rows**: `1`

## T2 Expired quote

- **http_status**: `409`
- **error**: `{"code": "QUOTE_EXPIRED", "message": "This quote has expired. Request a new quote.", "retryable": true, "request_id": "req-6811600238e6"}`
- **balances_unchanged**: `true`
- **transaction_rows**: `0`

## T3 Ambiguous response (timeout after commit)

- **first_response**: `{"status": 504, "code": "RESPONSE_TIMEOUT"}`
- **recovery_lookup**: `{"status": 200, "transaction_status": "COMPLETED", "transaction_id": "txn-e959a7e24bae48d3"}`
- **same_key_retry**: `{"status": 200, "replayed": "true", "transaction_id": "txn-e959a7e24bae48d3"}`
- **usd_available_after**: `"15000.00"`
- **transaction_rows**: `1`

## T4 Double-click / concurrent confirms

- **same_key_5_parallel_status_codes**: `[200, 200, 200, 200, 200]`
- **distinct_transactions_created**: `1`
- **two_quotes_60pct_each_status_codes**: `[200, 409]`
- **loser_error**: `"INSUFFICIENT_BALANCE"`
- **usd_after**: `{"available": "6000.00", "reserved": "0.00", "pending": "0.00"}`

## T5 Failure during settlement (reservation released)

- **http_status**: `500`
- **failure_code**: `"SETTLEMENT_FAILED"`
- **transaction_status**: `"FAILED"`
- **balances_restored**: `true`

## Reserve → settle visibility (INR → USDC-Solana 100,000)

- **mid_flight**: `{"acct-inr": {"available": "1900000.00", "reserved": "100000.00", "pending": "0.00"}, "acct-usdc-sol": {"available": "5000.000000", "reserved": "0.000000", "pending": "1195.194995"}}`
- **after_settle**: `{"acct-inr": {"available": "1900000.00", "reserved": "0.00", "pending": "0.00"}, "acct-usdc-sol": {"available": "6195.194995", "reserved": "0.000000", "pending": "0.000000"}}`

## Scenario C — ambiguous commit → human review (simulated DB connection loss)

- **customer_response**: `{"http_status": 202, "status": "REVIEW_REQUIRED", "conversion_id": "txn-7eb2def998054ac9", "after_balances_shown_to_customer": null}`
- **balances_while_under_review**: `{"acct-usd": {"available": "15000.00", "reserved": "10000.00", "pending": "0.00"}, "acct-usdc-sol": {"available": "5000.000000", "reserved": "0.000000", "pending": "9950.000000"}}`
- **same_key_retry**: `{"http_status": 409, "code": "CONVERSION_UNDER_REVIEW"}`
- **notification_response**: `{"notification_id": "NTF-D2D0B20E", "conversion_id": "txn-7eb2def998054ac9", "review_case_id": "RVW-FEA0B4AE", "event": "CONVERSION_REVIEW_REQUIRED", "channel": "EMAIL", "recipient_group": "OPERATIONS", "priority": "HIGH", "subject": "Action Required \u2013 Conversion Outcome Unresolved", "status": "QUEUED", "simulated": true, "created_at": "2026-11-19T10:23:40.999Z"}`
- **notification_evidence_section**: `{"settlement_attempted_at": "2026-11-19T10:23:40.984Z", "database_error": "Simulated: database connection lost during settlement COMMIT; no commit acknowledgement received", "conversion_record_found": "UNKNOWN (lookup failed)", "source_debit_found": "UNKNOWN (lookup failed)", "destination_credit_found": "UNKNOWN (lookup failed)", "idempotency_lookup_result": "FAILED after 3 attempts: Simulated: connection to settlement records unavailable during recovery lookup", "automated_recovery_attempts": [{"attempt": 1, "at": "2026-11-19T10:23:40.992Z", "result": "LOOKUP_FAILED", "error": "Simulated: connection to settlement records unavailable during recovery lookup"}, {"attempt": 2, "at": "2026-11-19T10:23:40.995Z", "result": "LOOKUP_FAILED", "error": "Simulated: connection to settlement records unavailable during recovery lookup"}, {"attempt": 3, "at": "2026-11-19T10:23:40.997Z", "result": "LOOKUP_FAILED", "error": "Simulated: connection to settlement records unavailable during recovery lookup"}], "last_known_system_response": "No commit acknowledgement received from the database.", "why_automation_stopped": "All 3 automated recovery lookups failed; the settlement records could not be read, so neither a committed nor a rolled-back settlement can be established."}`
- **reviewer_inspection_conclusion**: `"NOT_COMMITTED"`
- **resolution**: `{"action": "CONFIRM_NOT_COMMITTED", "case_status": "RESOLVED_NOT_COMMITTED", "customer_final_status": "FAILED"}`
- **balances_after_resolution_equal_start**: `true`
