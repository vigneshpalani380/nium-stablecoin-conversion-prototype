"""B006: idempotency, uncertain-outcome recovery and double-click concurrency."""
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from backend.domain.errors import AppError
from tests.helpers import (
    USD, USDC_SOL, balances, completed_count, confirm, new_key, quote_id, txn_count,
)


def test_same_key_same_payload_replays_original_result(client, container):
    qid = quote_id(client, USD, USDC_SOL, "1000.00")
    key = new_key()
    first = confirm(client, qid, key)
    second = confirm(client, qid, key)
    assert first.status_code == second.status_code == 200
    assert second.headers["Idempotent-Replayed"] == "true"
    assert first.json() == second.json()
    assert txn_count(container) == 1
    assert balances(client)[USD]["available"] == Decimal("24000")


def test_same_key_different_payload_conflicts(client, container):
    key = new_key()
    q1 = quote_id(client, USD, USDC_SOL, "100.00")
    q2 = quote_id(client, USD, USDC_SOL, "200.00")
    assert confirm(client, q1, key).status_code == 200
    resp = confirm(client, q2, key)
    assert resp.status_code == 409 and resp.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert txn_count(container) == 1


@pytest.mark.parametrize("key,code", [(None, "MISSING_IDEMPOTENCY_KEY"), ("short", "INVALID_IDEMPOTENCY_KEY"),
                                      ("has spaces in it", "INVALID_IDEMPOTENCY_KEY")])
def test_idempotency_key_required_and_validated(client, key, code):
    qid = quote_id(client, USD, USDC_SOL, "1.00")
    resp = confirm(client, qid, key)
    assert resp.status_code == 400 and resp.json()["error"]["code"] == code


def test_t3_timeout_after_commit_recovers_by_original_key_without_duplicate(client, container):
    qid = quote_id(client, USD, USDC_SOL, "10000.00")
    key = new_key()
    container.faults.timeout_after_commit = True
    lost = confirm(client, qid, key)
    assert lost.status_code == 504 and lost.json()["error"]["code"] == "RESPONSE_TIMEOUT"

    # Client keeps its original key and asks for status.
    status = client.get(f"/api/v1/conversion/transactions/by-idempotency-key/{key}")
    assert status.status_code == 200
    original = status.json()
    assert original["status"] == "COMPLETED"

    # Retrying confirm with the same key replays; it does not convert again.
    replay = confirm(client, qid, key)
    assert replay.status_code == 200 and replay.json()["transaction_id"] == original["transaction_id"]
    b = balances(client)
    assert b[USD]["available"] == Decimal("15000") and b[USDC_SOL]["available"] == Decimal("14950")
    assert txn_count(container) == 1


def test_unknown_key_lookup_is_404_meaning_safe_to_retry_same_key(client):
    resp = client.get("/api/v1/conversion/transactions/by-idempotency-key/never-sent-key")
    assert resp.status_code == 404 and resp.json()["error"]["code"] == "TRANSACTION_NOT_FOUND"


# ---------------------------------------------------------------- T4 double-click races

def _race(fn, n=2):
    barrier = threading.Barrier(n)

    def run(i):
        barrier.wait()
        return fn(i)

    with ThreadPoolExecutor(max_workers=n) as pool:
        return list(pool.map(run, range(n)))


def _service_confirm(container, qid, key):
    try:
        outcome = container.conversions().confirm(container.settings.customer_id, qid, key)
        return ("ok", outcome.status_code, outcome.replayed, outcome.body.get("transaction_id"))
    except AppError as exc:
        return ("err", exc.http_status, exc.code, exc.details.get("transaction_id"))


def test_t4a_double_click_same_key_converts_once(client, container):
    container.faults.pause_after_reserve_seconds = 0.3  # first request is still in flight
    qid = quote_id(client, USD, USDC_SOL, "10000.00")
    key = new_key()
    results = _race(lambda i: _service_confirm(container, qid, key))
    oks = [r for r in results if r[0] == "ok" and not r[2]]
    others = [r for r in results if r not in oks]
    assert len(oks) == 1 and len(others) == 1
    assert others[0][:3] == ("err", 409, "CONVERSION_IN_PROGRESS") or others[0][2] is True
    assert txn_count(container) == 1
    assert balances(client)[USD]["available"] == Decimal("15000")


def test_t4a_double_click_same_key_without_pause_converts_once(client, container):
    for _ in range(5):
        qid = quote_id(client, USD, USDC_SOL, "1000.00")
        key = new_key()
        results = _race(lambda i: _service_confirm(container, qid, key))
        fresh = [r for r in results if r[0] == "ok" and r[2] is False]
        assert len(fresh) == 1, results
        for r in results:
            assert (r[0] == "ok") or r[2] == "CONVERSION_IN_PROGRESS"
    assert txn_count(container) == 5
    assert balances(client)[USD]["available"] == Decimal("20000")


def test_t4b_double_click_different_keys_same_quote_converts_once(client, container):
    qid = quote_id(client, USD, USDC_SOL, "10000.00")
    results = _race(lambda i: _service_confirm(container, qid, new_key()))
    assert sorted(r[0] for r in results) == ["err", "ok"]
    err = next(r for r in results if r[0] == "err")
    assert err[1:3] == (409, "QUOTE_ALREADY_USED")
    assert txn_count(container) == 1
    assert balances(client)[USD]["available"] == Decimal("15000")


def test_t4c_two_quotes_exceeding_balance_only_one_reserves(client, container):
    q1 = quote_id(client, USD, USDC_SOL, "15000.00")  # each 60% of 25,000
    q2 = quote_id(client, USD, USDC_SOL, "15000.00")
    quotes = [q1, q2]
    results = _race(lambda i: _service_confirm(container, quotes[i], new_key()))
    assert sorted(r[0] for r in results) == ["err", "ok"]
    err = next(r for r in results if r[0] == "err")
    assert err[1:3] == (409, "INSUFFICIENT_BALANCE")
    b = balances(client)
    assert b[USD] == {"available": Decimal("10000"), "reserved": 0, "pending": 0}
    assert completed_count(container) == 1


def test_t4_api_level_rapid_double_click_many_threads(app, container):
    """Ten concurrent HTTP confirms with the same key (a very fast double/triple click)."""
    client = TestClient(app, raise_server_exceptions=False)
    qid = quote_id(client, USD, USDC_SOL, "25000.00")  # entire balance
    key = new_key()
    results = _race(lambda i: TestClient(app, raise_server_exceptions=False).post(
        f"/api/v1/conversion/quotes/{qid}/confirm", headers={"Idempotency-Key": key}), n=10)
    codes = sorted(r.status_code for r in results)
    assert set(codes) <= {200, 409}
    txn_ids = {r.json()["transaction_id"] for r in results if r.status_code == 200}
    assert len(txn_ids) == 1
    for r in results:
        if r.status_code == 409:
            assert r.json()["error"]["code"] == "CONVERSION_IN_PROGRESS"
    b = balances(client)
    assert b[USD] == {"available": Decimal("0"), "reserved": 0, "pending": 0}
    assert txn_count(container) == 1
