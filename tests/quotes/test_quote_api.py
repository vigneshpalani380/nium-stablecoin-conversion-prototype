from datetime import datetime

import pytest

from tests.helpers import INR, USD, USDC_BASE, USDC_SOL, USDT_SOL, balances, make_quote


def test_valid_quote_has_all_fields_and_does_not_move_balances(client):
    before = balances(client)
    resp = make_quote(client, USD, USDC_SOL, "10000.00")
    assert resp.status_code == 201
    q = resp.json()
    assert q["quote_id"].startswith("q-")
    assert q["status"] == "OPEN" and q["rate_source"] == "SIMULATED"
    assert q["gross_source_amount"] == "10000.00"
    assert q["fee_rate"] == "0.005" and q["fee_amount"] == "50.00" and q["fee_currency"] == "USD"
    assert q["net_source_amount"] == "9950.00"
    assert q["exchange_rate"] == "1.0000"
    assert q["destination_amount"] == "9950.000000"
    created = datetime.fromisoformat(q["created_at"].rstrip("Z"))
    expires = datetime.fromisoformat(q["expires_at"].rstrip("Z"))
    assert (expires - created).total_seconds() == 30
    assert balances(client) == before


def test_usdc_to_inr_quote(client):
    q = make_quote(client, USDC_SOL, INR, "100.000000").json()
    assert q["fee_amount"] == "0.500000" and q["fee_currency"] == "USDC"
    assert q["destination_amount"] == "8283.38"  # 99.5 * 83.25 = 8283.375 -> 8283.38


@pytest.mark.parametrize("src,dst", [
    (USD, USDT_SOL),        # not configured
    (USD, USDC_BASE),       # USDC network mismatch: only USDC-Solana is enabled
    (USDC_BASE, INR),       # USDC network mismatch on the source side
    (USD, INR),             # fiat-fiat not configured
    (INR, USD),
])
def test_unsupported_pairs_rejected(client, src, dst):
    resp = make_quote(client, src, dst, "10")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "UNSUPPORTED_PAIR"


def test_same_account_rejected(client):
    resp = make_quote(client, USD, USD, "10")
    assert resp.status_code == 400 and resp.json()["error"]["code"] == "SAME_ACCOUNT"


@pytest.mark.parametrize("amount,code", [
    ("0", "INVALID_AMOUNT"), ("-10", "INVALID_AMOUNT"), ("abc", "INVALID_AMOUNT"),
    ("10.001", "PRECISION_EXCEEDED"),
])
def test_invalid_amounts_rejected(client, amount, code):
    resp = make_quote(client, USD, USDC_SOL, amount)
    assert resp.status_code == 400 and resp.json()["error"]["code"] == code


def test_stablecoin_allows_six_decimals_but_not_seven(client):
    assert make_quote(client, USDC_SOL, USD, "1.123456").status_code == 201
    resp = make_quote(client, USDC_SOL, USD, "1.1234567")
    assert resp.json()["error"]["code"] == "PRECISION_EXCEEDED"


def test_json_number_amount_rejected_as_schema_error(client):
    resp = client.post("/api/v1/conversion/quotes", json={
        "source_account_id": USD, "destination_account_id": USDC_SOL, "gross_source_amount": 10.5})
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_insufficient_balance_at_quote_time(client):
    resp = make_quote(client, USD, USDC_SOL, "25000.01")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INSUFFICIENT_BALANCE"


def test_unknown_account_404(client):
    resp = make_quote(client, "acct-nope", USDC_SOL, "1")
    assert resp.status_code == 404 and resp.json()["error"]["code"] == "ACCOUNT_NOT_FOUND"


def test_quote_reports_expired_after_ttl_and_cancel(client, clock):
    qid = make_quote(client, USD, USDC_SOL, "10").json()["quote_id"]
    clock.advance(30)
    assert client.get(f"/api/v1/conversion/quotes/{qid}").json()["status"] == "EXPIRED"
    qid2 = make_quote(client, USD, USDC_SOL, "10").json()["quote_id"]
    assert client.post(f"/api/v1/conversion/quotes/{qid2}/cancel").json()["status"] == "CANCELLED"
