"""Q002: end-to-end scenarios against a real uvicorn process over HTTP.

Set E2E_EVIDENCE_DIR=docs/evidence to write the captured evidence (JSON + Markdown).
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    port = _free_port()
    db = tmp_path_factory.mktemp("e2e") / "e2e.db"
    env = {**os.environ, "WALLET_DATABASE_URL": f"sqlite:///{db.as_posix()}", "WALLET_DEMO_MODE": "true"}
    # Server output goes to a file. An undrained PIPE fills up (small on Windows) and blocks the
    # server's log writes, which looks exactly like a server hang. See docs/correction_record.md.
    log_file = open(db.parent / "server.log", "w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:create_app", "--factory", "--port", str(port), "--log-level", "warning"],
        cwd=ROOT, env=env, stdout=log_file, stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            if httpx.get(f"{base}/health", timeout=0.5).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.1)
    else:
        proc.kill()
        raise RuntimeError("server did not start")
    yield base
    proc.terminate()
    proc.wait(timeout=10)
    log_file.close()


EVIDENCE: dict[str, dict] = {}


@pytest.fixture(scope="module", autouse=True)
def write_evidence():
    yield
    out = os.getenv("E2E_EVIDENCE_DIR")
    if not out or not EVIDENCE:
        return
    path = ROOT / out
    path.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (path / "e2e_scenarios.json").write_text(json.dumps({"generated_at": stamp, "scenarios": EVIDENCE}, indent=2), encoding="utf-8")
    lines = [f"# End-to-end scenario evidence\n", f"Generated {stamp} by `tests/e2e/test_scenarios_e2e.py` "
             "against a live uvicorn process over HTTP (fresh SQLite DB, seeded balances).\n"]
    for name, ev in EVIDENCE.items():
        lines.append(f"\n## {name}\n")
        for k, v in ev.items():
            lines.append(f"- **{k}**: `{json.dumps(v)}`")
    (path / "e2e_scenarios.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _balances(c):
    return {a["id"]: {k: a[f"{k}_balance"] for k in ("available", "reserved", "pending")}
            for a in c.get("/api/v1/accounts").json()["accounts"]}


def _quote(c, src, dst, amount):
    r = c.post("/api/v1/conversion/quotes", json={"source_account_id": src, "destination_account_id": dst,
                                                  "gross_source_amount": amount})
    assert r.status_code == 201, r.text
    return r.json()


def _confirm(c, qid, key):
    return c.post(f"/api/v1/conversion/quotes/{qid}/confirm", headers={"Idempotency-Key": key})


def _key():
    return f"e2e-{uuid.uuid4().hex}"


@pytest.fixture
def c(server):
    with httpx.Client(base_url=server, timeout=30) as client:
        client.post("/api/v1/demo/reset")
        yield client


def test_t1_normal(c):
    before = _balances(c)
    q = _quote(c, "acct-usd", "acct-usdc-sol", "10000.00")
    r = _confirm(c, q["quote_id"], _key())
    after = _balances(c)
    txns = c.get("/api/v1/conversion/transactions").json()["transactions"]
    assert r.status_code == 200 and r.json()["status"] == "COMPLETED"
    assert after["acct-usd"]["available"] == "15000.00"
    assert after["acct-usdc-sol"]["available"] == "14950.000000"
    assert len(txns) == 1
    EVIDENCE["T1 Normal conversion (USD → USDC-Solana 10,000)"] = {
        "quote": {k: q[k] for k in ("quote_id", "gross_source_amount", "fee_amount", "net_source_amount",
                                    "exchange_rate", "destination_amount", "rate_source")},
        "balances_before": {k: before[k] for k in ("acct-usd", "acct-usdc-sol")},
        "balances_after": {k: after[k] for k in ("acct-usd", "acct-usdc-sol")},
        "transaction_status": r.json()["status"], "transaction_rows": len(txns),
    }


def test_t2_expired_quote(c):
    before = _balances(c)
    q = _quote(c, "acct-usd", "acct-usdc-sol", "10000.00")
    c.post(f"/api/v1/demo/quotes/{q['quote_id']}/expire")
    r = _confirm(c, q["quote_id"], _key())
    after = _balances(c)
    txns = c.get("/api/v1/conversion/transactions").json()["transactions"]
    assert r.status_code == 409 and r.json()["error"]["code"] == "QUOTE_EXPIRED"
    assert after == before and txns == []
    EVIDENCE["T2 Expired quote"] = {"http_status": r.status_code, "error": r.json()["error"],
                                    "balances_unchanged": after == before, "transaction_rows": len(txns)}


def test_t3_ambiguous_timeout_after_commit(c):
    c.put("/api/v1/demo/faults", json={"timeout_after_commit": True})
    q = _quote(c, "acct-usd", "acct-usdc-sol", "10000.00")
    key = _key()
    lost = _confirm(c, q["quote_id"], key)
    recovered = c.get(f"/api/v1/conversion/transactions/by-idempotency-key/{key}")
    replay = _confirm(c, q["quote_id"], key)
    after = _balances(c)
    txns = c.get("/api/v1/conversion/transactions").json()["transactions"]
    assert lost.status_code == 504
    assert recovered.json()["status"] == "COMPLETED"
    assert replay.status_code == 200 and replay.headers.get("Idempotent-Replayed") == "true"
    assert replay.json()["transaction_id"] == recovered.json()["transaction_id"]
    assert after["acct-usd"]["available"] == "15000.00" and len(txns) == 1
    EVIDENCE["T3 Ambiguous response (timeout after commit)"] = {
        "first_response": {"status": lost.status_code, "code": lost.json()["error"]["code"]},
        "recovery_lookup": {"status": recovered.status_code, "transaction_status": recovered.json()["status"],
                            "transaction_id": recovered.json()["transaction_id"]},
        "same_key_retry": {"status": replay.status_code, "replayed": replay.headers.get("Idempotent-Replayed"),
                           "transaction_id": replay.json()["transaction_id"]},
        "usd_available_after": after["acct-usd"]["available"], "transaction_rows": len(txns),
    }


def test_t4_double_click_over_http(c, server):
    # (a) same key, 5 simultaneous requests; (b) two quotes worth 60% of balance each.
    q = _quote(c, "acct-usd", "acct-usdc-sol", "10000.00")
    key = _key()
    barrier = threading.Barrier(5)

    def click(_):
        with httpx.Client(base_url=server, timeout=30) as cc:
            barrier.wait()
            return _confirm(cc, q["quote_id"], key)

    with ThreadPoolExecutor(5) as pool:
        same_key = list(pool.map(click, range(5)))
    ids = {r.json().get("transaction_id") for r in same_key if r.status_code == 200}
    codes_a = sorted(r.status_code for r in same_key)
    assert len(ids) == 1 and set(codes_a) <= {200, 409}

    q1 = _quote(c, "acct-usd", "acct-usdc-sol", "9000.00")   # 15,000 left; each is 60%
    q2 = _quote(c, "acct-usd", "acct-usdc-sol", "9000.00")
    barrier2 = threading.Barrier(2)

    def click2(qid):
        with httpx.Client(base_url=server, timeout=30) as cc:
            barrier2.wait()
            return _confirm(cc, qid, _key())

    with ThreadPoolExecutor(2) as pool:
        two = list(pool.map(click2, [q1["quote_id"], q2["quote_id"]]))
    codes_b = sorted(r.status_code for r in two)
    assert codes_b == [200, 409]
    loser = next(r for r in two if r.status_code == 409).json()["error"]["code"]
    assert loser == "INSUFFICIENT_BALANCE"
    after = _balances(c)
    assert after["acct-usd"] == {"available": "6000.00", "reserved": "0.00", "pending": "0.00"}
    EVIDENCE["T4 Double-click / concurrent confirms"] = {
        "same_key_5_parallel_status_codes": codes_a, "distinct_transactions_created": len(ids),
        "two_quotes_60pct_each_status_codes": codes_b, "loser_error": loser,
        "usd_after": after["acct-usd"],
    }


def test_t5_failure_mid_settlement_releases(c):
    before = _balances(c)
    c.put("/api/v1/demo/faults", json={"fail_mid_settle": True})
    q = _quote(c, "acct-usdc-sol", "acct-inr", "100.000000")
    r = _confirm(c, q["quote_id"], _key())
    after = _balances(c)
    assert r.status_code == 500 and r.json()["error"]["code"] == "CONVERSION_FAILED"
    assert after == before
    tid = r.json()["error"]["details"]["transaction_id"]
    detail = c.get(f"/api/v1/conversion/transactions/{tid}").json()
    assert detail["status"] == "FAILED"
    EVIDENCE["T5 Failure during settlement (reservation released)"] = {
        "http_status": r.status_code, "failure_code": detail["failure_code"],
        "transaction_status": detail["status"], "balances_restored": after == before,
    }


def test_reserved_and_pending_visible_mid_flight(c, server):
    c.put("/api/v1/demo/faults", json={"pause_after_reserve_seconds": 2.0})
    q = _quote(c, "acct-inr", "acct-usdc-sol", "100000.00")
    result = {}
    t = threading.Thread(target=lambda: result.setdefault("r", _confirm(httpx.Client(base_url=server, timeout=30), q["quote_id"], _key())))
    t.start()
    # Poll (don't sleep a fixed time) until the reservation is visible; it lasts 2s.
    deadline = time.monotonic() + 1.5
    mid = _balances(c)
    while mid["acct-inr"]["reserved"] == "0.00" and time.monotonic() < deadline:
        time.sleep(0.05)
        mid = _balances(c)
    t.join()
    assert result["r"].status_code == 200
    c.put("/api/v1/demo/faults", json={"pause_after_reserve_seconds": 0})
    end = _balances(c)
    assert mid["acct-inr"]["reserved"] == "100000.00" and mid["acct-usdc-sol"]["pending"] == "1195.194995"
    assert end["acct-inr"]["reserved"] == "0.00" and end["acct-usdc-sol"]["available"] == "6195.194995"
    EVIDENCE["Reserve → settle visibility (INR → USDC-Solana 100,000)"] = {
        "mid_flight": {"acct-inr": mid["acct-inr"], "acct-usdc-sol": mid["acct-usdc-sol"]},
        "after_settle": {"acct-inr": end["acct-inr"], "acct-usdc-sol": end["acct-usdc-sol"]},
    }


OPS = {"X-Ops-Token": "demo-ops-token"}


def test_scenario_c_ambiguous_commit_human_review(c):
    """Scenario C over HTTP: uncertain COMMIT -> recovery fails -> Under review + simulated ops email."""
    before = _balances(c)
    c.put("/api/v1/demo/faults", json={"uncertain_commit": "ROLLED_BACK", "recovery_lookup_fails": True})
    q = _quote(c, "acct-usd", "acct-usdc-sol", "10000.00")
    key = _key()
    r = _confirm(c, q["quote_id"], key)
    customer = r.json()
    held = _balances(c)
    retry = _confirm(c, q["quote_id"], key)
    notifications = c.get("/internal/v1/notifications", headers=OPS).json()["notifications"]
    assert r.status_code == 202 and customer["status"] == "REVIEW_REQUIRED"
    assert held["acct-usd"] == {"available": "15000.00", "reserved": "10000.00", "pending": "0.00"}
    assert held["acct-usdc-sol"]["pending"] == "9950.000000" and held["acct-usdc-sol"]["available"] == "5000.000000"
    assert retry.status_code == 409 and retry.json()["error"]["code"] == "CONVERSION_UNDER_REVIEW"
    assert len(notifications) == 1
    assert "notification" not in r.text and "RVW-" not in r.text
    full = c.get(f"/internal/v1/notifications/{notifications[0]['notification_id']}", headers=OPS).json()
    case_id = full["review_case_id"]
    inspection = c.get(f"/internal/v1/review-cases/{case_id}/inspection", headers=OPS).json()
    resolution = c.post(f"/internal/v1/review-cases/{case_id}/resolution", headers=OPS,
                        json={"action": "CONFIRM_NOT_COMMITTED", "reviewer": "ops.demo",
                              "note": "No settlement marker; reservation and pending credit intact"}).json()
    final = c.get(f"/api/v1/conversion/transactions/by-idempotency-key/{key}").json()
    after = _balances(c)
    out = os.getenv("E2E_EVIDENCE_DIR")
    if out:
        (ROOT / out).mkdir(parents=True, exist_ok=True)
        (ROOT / out / "sample_ops_notification.txt").write_text(full["body"] + "\n", encoding="utf-8")
        (ROOT / out / "sample_ops_notification.json").write_text(json.dumps(full, indent=2), encoding="utf-8")
    assert inspection["evidence"]["conclusion"] == "NOT_COMMITTED"
    assert resolution["status"] == "RESOLVED_NOT_COMMITTED" and final["status"] == "FAILED"
    assert after == before
    EVIDENCE["Scenario C — ambiguous commit → human review (simulated DB connection loss)"] = {
        "customer_response": {"http_status": r.status_code, "status": customer["status"],
                              "conversion_id": customer["transaction_id"],
                              "after_balances_shown_to_customer": customer["balances"]["source"]["after"]},
        "balances_while_under_review": {k: held[k] for k in ("acct-usd", "acct-usdc-sol")},
        "same_key_retry": {"http_status": retry.status_code, "code": retry.json()["error"]["code"]},
        "notification_response": notifications[0],
        "notification_evidence_section": full["payload"]["evidence"],
        "reviewer_inspection_conclusion": inspection["evidence"]["conclusion"],
        "resolution": {"action": "CONFIRM_NOT_COMMITTED", "case_status": resolution["status"],
                       "customer_final_status": final["status"]},
        "balances_after_resolution_equal_start": after == before,
    }
