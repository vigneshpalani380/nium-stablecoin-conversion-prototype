from dataclasses import replace
from decimal import Decimal

from sqlalchemy import select

from backend.config.settings import PAIRS
from backend.models.entities import Account, ConversionPair
from backend.seed.seed import initialise, sync_pairs
from tests.helpers import USD, USDC_BASE, USDC_SOL, balances


def test_seed_creates_five_distinct_network_specific_accounts(client):
    b = balances(client)
    assert set(b) == {"acct-usd", "acct-inr", "acct-usdc-sol", "acct-usdc-base", "acct-usdt-sol"}
    assert b[USD]["available"] == Decimal("25000.00")
    assert b[USDC_SOL]["available"] == Decimal("5000")
    assert b[USDC_BASE]["available"] == Decimal("1000")
    for acct in b.values():
        assert acct["reserved"] == 0 and acct["pending"] == 0


def test_usdc_solana_and_usdc_base_are_separate_accounts(client):
    accounts = {a["id"]: a for a in client.get("/api/v1/accounts").json()["accounts"]}
    assert accounts[USDC_SOL]["asset_code"] == accounts[USDC_BASE]["asset_code"] == "USDC"
    assert accounts[USDC_SOL]["network"] == "SOLANA"
    assert accounts[USDC_BASE]["network"] == "BASE"
    assert accounts[USD]["network"] is None


def test_exactly_the_four_configured_pairs_are_enabled(client):
    cfg = client.get("/api/v1/conversion/config").json()
    pairs = {(p["source_account_id"], p["destination_account_id"]) for p in cfg["pairs"]}
    assert pairs == {
        ("acct-usdc-sol", "acct-usd"),
        ("acct-usd", "acct-usdc-sol"),
        ("acct-usdc-sol", "acct-inr"),
        ("acct-inr", "acct-usdc-sol"),
    }
    assert cfg["fee_rate"] == "0.005"
    assert cfg["quote_ttl_seconds"] == 30
    assert cfg["rate_source"] == "SIMULATED"


def test_seed_is_repeatable_and_does_not_reset_balances(container, settings, clock):
    with container.db.transaction() as s:
        s.get(Account, USD).available_minor = 123
    initialise(container.db, settings, clock)
    initialise(container.db, settings, clock)
    with container.db.transaction() as s:
        assert len(list(s.scalars(select(Account)))) == 5
        assert s.get(Account, USD).available_minor == 123
        assert len(list(s.scalars(select(ConversionPair)))) == 4


def test_pairs_are_data_driven_removing_from_config_disables_pair(container, settings, client):
    reduced = replace(settings, pairs=PAIRS[:2])  # keep only USDC-Sol <-> USD
    sync_pairs(container.db, reduced)
    cfg = client.get("/api/v1/conversion/config").json()
    assert len(cfg["pairs"]) == 2
    resp = client.post("/api/v1/conversion/quotes", json={
        "source_account_id": "acct-usdc-sol", "destination_account_id": "acct-inr", "gross_source_amount": "10"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "UNSUPPORTED_PAIR"
