"""B005: reserve -> settle / release, atomicity and rollback."""
import threading
import time
from decimal import Decimal

from sqlalchemy import select

from backend.models.entities import ConversionQuote, ConversionTransaction
from tests.helpers import (
    INR, USD, USDC_SOL, balances, confirm, idem_count, make_quote, new_key, quote_id, txn_count,
)


def test_t1_normal_conversion_updates_both_balances_and_stores_one_transaction(client, container):
    qid = quote_id(client, USD, USDC_SOL, "10000.00")
    resp = confirm(client, qid, new_key())
    assert resp.status_code == 200, resp.text
    t = resp.json()
    assert t["status"] == "COMPLETED"
    assert t["gross_source_amount"] == "10000.00" and t["fee_amount"] == "50.00"
    assert t["net_source_amount"] == "9950.00" and t["destination_amount"] == "9950.000000"
    assert t["balances"]["source"] == {
        "before": {"available": "25000.00", "reserved": "0.00", "pending": "0.00"},
        "after": {"available": "15000.00", "reserved": "0.00", "pending": "0.00"},
    }
    assert t["balances"]["destination"] == {
        "before": {"available": "5000.000000", "reserved": "0.000000", "pending": "0.000000"},
        "after": {"available": "14950.000000", "reserved": "0.000000", "pending": "0.000000"},
    }
    b = balances(client)
    assert b[USD]["available"] == Decimal("15000") and b[USDC_SOL]["available"] == Decimal("14950")
    assert txn_count(container) == 1
    with container.db.transaction() as s:
        assert s.get(ConversionQuote, qid).status == "CONFIRMED"


def test_reserved_and_pending_are_visible_while_conversion_is_in_flight(client, container):
    container.faults.pause_after_reserve_seconds = 0.6
    qid = quote_id(client, USD, USDC_SOL, "10000.00")
    result = {}
    worker = threading.Thread(target=lambda: result.setdefault("r", confirm(client, qid, new_key())))
    worker.start()
    time.sleep(0.3)
    mid = balances(client)
    worker.join()
    assert mid[USD] == {"available": Decimal("15000"), "reserved": Decimal("10000"), "pending": 0}
    assert mid[USDC_SOL] == {"available": Decimal("5000"), "reserved": 0, "pending": Decimal("9950")}
    assert result["r"].status_code == 200
    end = balances(client)
    assert end[USD] == {"available": Decimal("15000"), "reserved": 0, "pending": 0}
    assert end[USDC_SOL] == {"available": Decimal("14950"), "reserved": 0, "pending": 0}


def test_injected_failure_before_reserve_commit_rolls_back_everything(client, container):
    before = balances(client)
    qid = quote_id(client, USD, USDC_SOL, "100.00")
    container.faults.fail_mid_reserve = True
    key = new_key()
    resp = confirm(client, qid, key)
    assert resp.status_code == 500 and resp.json()["error"]["code"] == "INTERNAL_ERROR"
    assert balances(client) == before
    assert txn_count(container) == 0 and idem_count(container) == 0
    with container.db.transaction() as s:
        assert s.get(ConversionQuote, qid).status == "OPEN"
    # Nothing was recorded, so retrying with the SAME key is safe and succeeds exactly once.
    assert confirm(client, qid, key).status_code == 200
    assert txn_count(container) == 1


def test_injected_failure_mid_settlement_releases_reservation(client, container):
    before = balances(client)
    qid = quote_id(client, USD, USDC_SOL, "100.00")
    container.faults.fail_mid_settle = True
    key = new_key()
    resp = confirm(client, qid, key)
    assert resp.status_code == 500
    err = resp.json()["error"]
    assert err["code"] == "CONVERSION_FAILED" and err["details"]["failure_code"] == "SETTLEMENT_FAILED"
    assert balances(client) == before  # available restored, reserved/pending back to zero
    with container.db.transaction() as s:
        txn = s.scalar(select(ConversionTransaction))
        assert txn.status == "FAILED" and txn.released_at is not None
        assert txn.src_available_after == txn.src_available_before
    # Replaying the same key returns the same stored failure; no second attempt is made.
    replay = confirm(client, qid, key)
    assert replay.status_code == 500 and replay.headers["Idempotent-Replayed"] == "true"
    assert replay.json()["error"]["details"]["transaction_id"] == err["details"]["transaction_id"]
    assert txn_count(container) == 1


def test_t2_expired_quote_cannot_execute(client, container, clock):
    before = balances(client)
    qid = quote_id(client, USD, USDC_SOL, "10000.00")
    clock.advance(31)
    resp = confirm(client, qid, new_key())
    assert resp.status_code == 409
    assert resp.json()["error"] == {
        "code": "QUOTE_EXPIRED", "message": "This quote has expired. Request a new quote.",
        "retryable": True, "request_id": resp.headers["X-Request-ID"],
    }
    assert balances(client) == before
    assert txn_count(container) == 0
    with container.db.transaction() as s:
        assert s.get(ConversionQuote, qid).status == "EXPIRED"


def test_quote_expires_exactly_at_ttl_boundary(client, clock):
    qid = quote_id(client, USD, USDC_SOL, "1.00")
    clock.advance(30)
    assert confirm(client, qid, new_key()).json()["error"]["code"] == "QUOTE_EXPIRED"


def test_demo_expire_endpoint(client):
    qid = quote_id(client, USD, USDC_SOL, "1.00")
    assert client.post(f"/api/v1/demo/quotes/{qid}/expire").json()["expired"] is True
    assert confirm(client, qid, new_key()).json()["error"]["code"] == "QUOTE_EXPIRED"


def test_balance_rechecked_at_confirmation(client, container):
    q1 = quote_id(client, USD, USDC_SOL, "20000.00")
    q2 = quote_id(client, USD, USDC_SOL, "10000.00")  # valid at quote time
    assert confirm(client, q1, new_key()).status_code == 200
    before = balances(client)
    resp = confirm(client, q2, new_key())
    assert resp.status_code == 409 and resp.json()["error"]["code"] == "INSUFFICIENT_BALANCE"
    assert balances(client) == before
    with container.db.transaction() as s:
        assert s.get(ConversionQuote, q2).status == "OPEN"  # rollback left the quote unconsumed


def test_quote_cannot_be_used_twice_with_different_keys(client, container):
    qid = quote_id(client, USD, USDC_SOL, "100.00")
    assert confirm(client, qid, new_key()).status_code == 200
    resp = confirm(client, qid, new_key())
    assert resp.status_code == 409 and resp.json()["error"]["code"] == "QUOTE_ALREADY_USED"
    assert txn_count(container) == 1


def test_cancelled_quote_cannot_execute(client):
    qid = quote_id(client, USD, USDC_SOL, "100.00")
    client.post(f"/api/v1/conversion/quotes/{qid}/cancel")
    assert confirm(client, qid, new_key()).json()["error"]["code"] == "QUOTE_CANCELLED"


def test_destination_rounding_persisted(client):
    qid = quote_id(client, USDC_SOL, INR, "1.234567")
    t = confirm(client, qid, new_key()).json()
    assert t["fee_amount"] == "0.006173" and t["destination_amount"] == "102.26"
    b = balances(client)
    assert b[INR]["available"] == Decimal("2000102.26")
    assert b[USDC_SOL]["available"] == Decimal("5000") - Decimal("1.234567")


def test_reconcile_releases_stuck_reservation_and_late_settle_does_not_double_apply(client, container):
    before = balances(client)
    container.faults.pause_after_reserve_seconds = 0.6
    qid = quote_id(client, USD, USDC_SOL, "500.00")
    key = new_key()
    result = {}
    worker = threading.Thread(target=lambda: result.setdefault("r", confirm(client, qid, key)))
    worker.start()
    time.sleep(0.3)
    released = client.post("/api/v1/demo/reconcile?older_than_seconds=0").json()["released_transaction_ids"]
    worker.join()
    assert len(released) == 1
    assert balances(client) == before
    # The paused request finds the transaction already finalised and returns the stored failure.
    assert result["r"].status_code == 500
    assert result["r"].json()["error"]["details"]["failure_code"] == "RECONCILED_RELEASE"
    assert txn_count(container) == 1


def test_startup_reconcile_releases_reserved_transactions(settings, clock, tmp_path):
    from backend.main import create_app
    from fastapi.testclient import TestClient

    app = create_app(settings, clock)
    c = app.state.container
    client = TestClient(app, raise_server_exceptions=False)
    qid = quote_id(client, USD, USDC_SOL, "100.00")
    # Simulate a crash after phase 1: reserve directly, never settle.
    from backend.services.idempotency.policy import request_fingerprint
    with c.db.transaction() as s:
        c.conversions()._reserve(s, settings.customer_id, qid, "crash-key-1", request_fingerprint(settings.customer_id, qid))
    assert balances(client)[USD]["reserved"] == Decimal("100")
    c.db.dispose()
    app2 = create_app(settings, clock)  # restart
    client2 = TestClient(app2, raise_server_exceptions=False)
    b = balances(client2)
    assert b[USD] == {"available": Decimal("25000"), "reserved": 0, "pending": 0}
    assert client2.get("/api/v1/conversion/transactions/by-idempotency-key/crash-key-1").json()["status"] == "FAILED"
    app2.state.container.db.dispose()
