def test_accounts_expose_three_balances_as_strings(client):
    body = client.get("/api/v1/accounts").json()
    usd = next(a for a in body["accounts"] if a["id"] == "acct-usd")
    assert usd == {
        "id": "acct-usd", "asset_code": "USD", "asset_type": "FIAT", "network": None, "display_name": "USD",
        "precision": 2, "available_balance": "25000.00", "reserved_balance": "0.00", "pending_balance": "0.00",
        "status": "ACTIVE",
    }
    sol = next(a for a in body["accounts"] if a["id"] == "acct-usdc-sol")
    assert sol["display_name"] == "USDC-Solana" and sol["available_balance"] == "5000.000000"


def test_there_is_no_balance_write_endpoint(client):
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)("/api/v1/accounts").status_code == 405
        assert getattr(client, method)("/api/v1/accounts/acct-usd").status_code in (404, 405)


def test_config_lists_assets_with_precision(client):
    cfg = client.get("/api/v1/conversion/config").json()
    precisions = {a["account_id"]: a["precision"] for a in cfg["assets"]}
    assert precisions == {"acct-usd": 2, "acct-inr": 2, "acct-usdc-sol": 6, "acct-usdc-base": 6, "acct-usdt-sol": 6}
    assert "secret" not in str(cfg).lower()


def test_unknown_route_and_errors_use_envelope_without_stack_traces(client):
    resp = client.get("/api/v1/conversion/transactions/txn-missing")
    assert resp.status_code == 404
    err = resp.json()["error"]
    assert err["code"] == "TRANSACTION_NOT_FOUND" and err["request_id"].startswith("req-")
    assert "Traceback" not in resp.text
