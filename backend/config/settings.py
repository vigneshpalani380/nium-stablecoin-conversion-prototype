"""Central configuration: assets, enabled pairs, fee, quote TTL and simulated rates.

Changing which pairs are enabled is a config change here; the seed step syncs it into the
`conversion_pairs` table on startup. UI and services never hard-code pairs.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from decimal import Decimal

DEMO_CUSTOMER_ID = "cust-demo-marketplace"
RATE_SOURCE = "SIMULATED"


@dataclass(frozen=True)
class AssetSpec:
    account_id: str
    asset_code: str
    asset_type: str  # FIAT | STABLECOIN
    network: str | None  # None for fiat
    precision: int
    seed_available: str  # decimal string


@dataclass(frozen=True)
class PairSpec:
    source: tuple[str, str | None]  # (asset_code, network)
    destination: tuple[str, str | None]
    simulated_rate: str  # destination units per 1 source unit; SIMULATED, not market data


ASSETS: tuple[AssetSpec, ...] = (
    AssetSpec("acct-usd", "USD", "FIAT", None, 2, "25000.00"),
    AssetSpec("acct-inr", "INR", "FIAT", None, 2, "2000000.00"),
    AssetSpec("acct-usdc-sol", "USDC", "STABLECOIN", "SOLANA", 6, "5000.000000"),
    AssetSpec("acct-usdc-base", "USDC", "STABLECOIN", "BASE", 6, "1000.000000"),
    AssetSpec("acct-usdt-sol", "USDT", "STABLECOIN", "SOLANA", 6, "1000.000000"),
)

# Product-owner decision 2026-11-19: only USDC-Solana <-> USD and USDC-Solana <-> INR.
PAIRS: tuple[PairSpec, ...] = (
    PairSpec(("USDC", "SOLANA"), ("USD", None), "1.0000"),
    PairSpec(("USD", None), ("USDC", "SOLANA"), "1.0000"),
    PairSpec(("USDC", "SOLANA"), ("INR", None), "83.2500"),
    PairSpec(("INR", None), ("USDC", "SOLANA"), "0.01201201"),
)


@dataclass(frozen=True)
class Settings:
    database_url: str = "sqlite:///./wallet.db"
    demo_mode: bool = True
    fee_rate: Decimal = Decimal("0.005")  # 0.5% of gross, in source currency
    quote_ttl_seconds: int = 30
    customer_id: str = DEMO_CUSTOMER_ID
    stuck_reservation_seconds: int = 60
    ops_token: str = "demo-ops-token"  # internal operations API (demo credential)
    assets: tuple[AssetSpec, ...] = field(default=ASSETS)
    pairs: tuple[PairSpec, ...] = field(default=PAIRS)


def load_settings() -> Settings:
    return Settings(
        database_url=os.getenv("WALLET_DATABASE_URL", "sqlite:///./wallet.db"),
        demo_mode=os.getenv("WALLET_DEMO_MODE", "true").lower() in ("1", "true", "yes"),
        quote_ttl_seconds=int(os.getenv("WALLET_QUOTE_TTL_SECONDS", "30")),
        ops_token=os.getenv("WALLET_OPS_TOKEN", "demo-ops-token"),
    )
