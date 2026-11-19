# Demo Runbook

A repeatable script for showing the conversion prototype in about 10 minutes.

## 1. Setup (once)

```sh
python -m venv .venv                                   # Python 3.12
.venv/Scripts/python -m pip install -r requirements-dev.txt
cd frontend && npm install && cd ..
```

## 2. Start

Open two terminals from the repo root:

```sh
.venv/Scripts/python -m uvicorn backend.main:create_app --factory --port 8000
```

```sh
cd frontend && npm run dev
```

Open http://localhost:5173. API docs are at http://localhost:8000/docs.

The SQLite database is `./wallet.db`. It is seeded automatically on first start. To start over, either open **Convert → Demo controls → Reset demo data**, or run `curl -X POST localhost:8000/api/v1/demo/reset`.

**Seed balances:** USD 25,000.00 · INR 2,000,000.00 · USDC-Solana 5,000 · USDC-Base 1,000 · USDT-Solana 1,000.

**Enabled pairs (config):** USDC-Solana ↔ USD and USDC-Solana ↔ INR.

## 3. Script

### A. Balances and accounts (1 min)

- Open the **Balances** tab. Every card shows its network: "Solana network", "Base network", or "Fiat — no network".
- Point out that USDC-Solana and USDC-Base are separate accounts.

### B. Normal conversion, T1 (2 min)

1. In **Convert**, set From **USD**, To **USDC-Solana**, Amount **10000.00**, then click **Get quote**.
   - The To list only offers enabled pairs. USD → USDC-Base never appears.
2. Review the quote: gross 10,000.00, fee 0.5% = 50.00 USD, net 9,950.00, rate labelled **Simulated demo rate**, you receive 9,950.00 USDC, and a 30s countdown.
3. Click **Confirm conversion**. Try double-clicking: the button locks, and the backend would deduplicate the request anyway.
4. The result shows the reference and a before/after table: USD 25,000 → 15,000 and USDC-Solana 5,000 → 14,950.
5. The **Activity** tab shows one row. Click it to see the rate, quote ID, idempotency key and the full balance snapshots.

### C. Reserve → settle made visible (1 min)

1. In Demo controls, tick **Pause 5s after reserving**.
2. Convert **INR 100000.00 → USDC-Solana**, then switch to **Balances** while it runs:
   - INR shows *Reserved: 100,000.00 (outgoing)*.
   - USDC-Solana shows *Pending: 1,195.194995 (incoming)*.
3. After about 5s it settles: reserved and pending go back to 0, and the available balances update.
4. Untick the pause.

### D. Expired quote, T2 (1 min)

1. Get a quote, then click **Expire this quote (demo)**, or wait 30s.
2. Confirm is replaced by **Get new quote**. If you confirm through the API, it returns `409 QUOTE_EXPIRED`.
3. No balances change and no transaction is created.

### E. Ambiguous response, T3 (2 min)

1. In Demo controls, tick **Lose the response after the conversion commits**.
2. Convert USDC-Solana → USD 100.
3. The server commits and then returns `504`. The UI shows **"Checking conversion status…"** and queries `/transactions/by-idempotency-key/{original key}`.
4. The result shows the original conversion, noting *"nothing was submitted twice"*. Activity has exactly one new row.

### F. Failure with release (1 min)

1. Tick **Fail during settlement** and convert.
2. The UI shows *Conversion failed — funds released*.
3. Balances are unchanged, and Activity shows the transaction as `FAILED` with `SETTLEMENT_FAILED`.

### H. Assignment scenarios: Normal, Exception, Ambiguous → human review (4 min)

All three use **USD 10,000 → USDC-Solana**. Click **Reset demo data** before each one.

**Scenario A — Normal.** Run the conversion with no demo controls set.
- The result is Completed: USD 15,000 / USDC 14,950.
- The ops outbox stays empty: `GET /internal/v1/notifications`.

**Scenario B — Definitive exception.** Tick **Fail during settlement**, then convert.
- The result is *Conversion failed — funds released*. The reservation is released once and balances are back to the start.
- No ops notification is created.

**Scenario C — Ambiguous outcome (simulated DB connection loss during COMMIT).**
1. In Demo controls, set *Simulated uncertain database commit* to **Scenario C — recovery cannot confirm → Under review + ops email**.
2. Convert. The customer sees **Status: Under review**, with the required message, the conversion ID, the amounts, "Source reserved" and "Destination credit … not yet confirmed". No resubmit button is offered.
3. **Balances** tab: USD shows *Reserved 10,000*, and USDC-Solana shows *Pending 9,950* (not available).
4. **Ops side (internal, not in the customer app).** Open http://localhost:8000/docs and use the **internal-operations** endpoints with the header `X-Ops-Token: demo-ops-token`:
   - `GET /internal/v1/notifications` returns `{"notification_id": "NTF-…", "event": "CONVERSION_REVIEW_REQUIRED", "channel": "EMAIL", "recipient_group": "OPERATIONS", "status": "QUEUED", "simulated": true}`
   - `GET /internal/v1/notifications/{id}` returns the full simulated email with sections A–F. A sample is in `docs/evidence/sample_ops_notification.txt`.
   - `GET /internal/v1/review-cases/{case_id}` returns the evidence and the audit trail: REQUESTED → … → OUTCOME_UNCERTAIN → 3× AUTOMATED_RECOVERY_ATTEMPT → HUMAN_REVIEW_REQUIRED → NOTIFICATION_QUEUED.
   - `GET /internal/v1/review-cases/{case_id}/inspection` returns `NOT_COMMITTED`, with the supported action `CONFIRM_NOT_COMMITTED`.
   - Optional: `POST …/resolution` with `{"action":"CONFIRM_COMMITTED", ...}` is **refused** because it contradicts the evidence.
   - `POST …/resolution` with `{"action":"CONFIRM_NOT_COMMITTED","reviewer":"ops.demo","note":"No settlement marker; reservation intact"}` releases the reservation once.
5. Back in the customer app, click **Refresh status**. The conversion now shows *failed — funds released*, and balances return to the start.

**Variants to show automation working without a human:**
- *Settled, ack lost*: recovery confirms Completed.
- *Rolled back, ack lost*: recovery releases the funds.

Neither variant creates a case or notification.

From the command line instead (Git Bash):

```sh
curl -s -X PUT localhost:8000/api/v1/demo/faults -H 'Content-Type: application/json'   -d '{"uncertain_commit":"ROLLED_BACK","recovery_lookup_fails":true}'
curl -s localhost:8000/internal/v1/notifications -H 'X-Ops-Token: demo-ops-token'
```

The full internal procedure is in [operations_review_procedure.md](operations_review_procedure.md).

### G. Double-click and concurrency proof (1 min)

Run the automated evidence in a terminal:

```sh
.venv/Scripts/python -m pytest tests/idempotency -v
```

- **T4a:** two or ten concurrent confirms with the same key produce one transaction.
- **T4b:** different keys on the same quote are rejected with `QUOTE_ALREADY_USED`.
- **T4c:** two quotes worth 60% of the balance each, confirmed simultaneously. One succeeds and one gets `INSUFFICIENT_BALANCE`, because check-and-reserve is a single conditional `UPDATE … WHERE available_minor >= :amount`.

## 4. Live-change exercise (config-driven pairs)

**Enable USDT-Solana → USD:**

1. Add `PairSpec(("USDT", "SOLANA"), ("USD", None), "1.0000")` to `PAIRS` in `backend/config/settings.py`.
2. Restart the backend. `sync_pairs` updates `conversion_pairs` on startup.
3. Reload the UI: USDT-Solana now appears as a source, with no UI code change.

**Change the fee:** edit `fee_rate` in `Settings`. Fee changes need product-owner approval under `08_BUILD_AND_AGENT_GUIDE.md`.

Revert both changes after the demo.

## 5. Full test evidence

```sh
.venv/Scripts/python -m pytest                       # 103 backend tests incl. live-server E2E
E2E_EVIDENCE_DIR=docs/evidence .venv/Scripts/python -m pytest tests/e2e   # regenerate evidence
cd frontend && npm test && npm run build && npx eslint .
```

- Evidence: `docs/evidence/e2e_scenarios.md`
- AI correction record: `docs/correction_record.md`
