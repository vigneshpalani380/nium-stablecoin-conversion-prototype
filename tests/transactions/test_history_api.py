from tests.helpers import INR, USD, USDC_SOL, confirm, new_key, quote_id


def test_history_lists_newest_first_including_failed(client, container, clock):
    q1 = quote_id(client, USD, USDC_SOL, "100.00")
    t1 = confirm(client, q1, new_key()).json()["transaction_id"]
    clock.advance(1)
    container.faults.fail_mid_settle = True
    q2 = quote_id(client, USDC_SOL, INR, "10.000000")
    t2 = confirm(client, q2, new_key()).json()["error"]["details"]["transaction_id"]

    items = client.get("/api/v1/conversion/transactions").json()["transactions"]
    assert [i["transaction_id"] for i in items] == [t2, t1]
    assert [i["status"] for i in items] == ["FAILED", "COMPLETED"]


def test_detail_includes_rate_quote_and_snapshots(client):
    qid = quote_id(client, USD, USDC_SOL, "100.00")
    tid = confirm(client, qid, new_key()).json()["transaction_id"]
    d = client.get(f"/api/v1/conversion/transactions/{tid}").json()
    assert d["quote_id"] == qid and d["exchange_rate"] == "1.0000" and d["rate_source"] == "SIMULATED"
    assert d["balances"]["source"]["after"]["available"] == "24900.00"
    assert d["source"]["display_name"] == "USD" and d["destination"]["display_name"] == "USDC-Solana"


def test_limit_parameter_validated(client):
    assert client.get("/api/v1/conversion/transactions?limit=0").status_code == 422
