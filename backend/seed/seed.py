"""Deterministic demo seed. Accounts are created once; pairs are re-synced from config on every start."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import delete, select

from backend.config.settings import Settings
from backend.db.database import Database
from backend.domain.money import to_minor
from backend.domain.support import SystemClock, network_key
from backend.models.entities import (
    Account,
    ConversionPair,
    ConversionEvent,
    ConversionQuote,
    ConversionTransaction,
    IdempotencyRecord,
    InternalNotification,
    ReviewCase,
)


def seed_accounts_if_missing(db: Database, settings: Settings, clock=None) -> int:
    now = (clock or SystemClock()).now()
    created = 0
    with db.transaction() as s:
        existing = set(s.scalars(select(Account.id).where(Account.customer_id == settings.customer_id)))
        for order, spec in enumerate(settings.assets):
            if spec.account_id in existing:
                continue
            s.add(
                Account(
                    id=spec.account_id,
                    customer_id=settings.customer_id,
                    asset_code=spec.asset_code,
                    asset_type=spec.asset_type,
                    network=spec.network,
                    network_key=network_key(spec.network),
                    precision=spec.precision,
                    sort_order=order,
                    available_minor=to_minor(Decimal(spec.seed_available), spec.precision),
                    reserved_minor=0,
                    pending_minor=0,
                    status="ACTIVE",
                    version=0,
                    created_at=now,
                    updated_at=now,
                )
            )
            created += 1
    return created


def sync_pairs(db: Database, settings: Settings) -> None:
    """Make the conversion_pairs table match config: upsert configured pairs, disable the rest."""
    wanted = {
        (p.source[0], network_key(p.source[1]), p.destination[0], network_key(p.destination[1])): p.simulated_rate
        for p in settings.pairs
    }
    with db.transaction() as s:
        rows = {
            (r.source_asset_code, r.source_network_key, r.destination_asset_code, r.destination_network_key): r
            for r in s.scalars(select(ConversionPair))
        }
        for key, row in rows.items():
            if key not in wanted:
                row.enabled = False
        for key, rate in wanted.items():
            row = rows.get(key)
            if row is None:
                s.add(
                    ConversionPair(
                        source_asset_code=key[0],
                        source_network_key=key[1],
                        destination_asset_code=key[2],
                        destination_network_key=key[3],
                        enabled=True,
                        simulated_rate=rate,
                    )
                )
            else:
                row.enabled = True
                row.simulated_rate = rate


def reset_demo_data(db: Database, settings: Settings, clock=None) -> None:
    """Demo-only: wipe quotes/transactions/idempotency/review data and restore seed balances."""
    now = (clock or SystemClock()).now()
    with db.transaction() as s:
        s.execute(delete(InternalNotification))
        s.execute(delete(ReviewCase))
        s.execute(delete(ConversionEvent))
        s.execute(delete(IdempotencyRecord))
        s.execute(delete(ConversionTransaction))
        s.execute(delete(ConversionQuote))
        for spec in settings.assets:
            acct = s.get(Account, spec.account_id)
            if acct is not None:
                acct.available_minor = to_minor(Decimal(spec.seed_available), spec.precision)
                acct.reserved_minor = 0
                acct.pending_minor = 0
                acct.status = "ACTIVE"
                acct.version += 1
                acct.updated_at = now
    seed_accounts_if_missing(db, settings, clock)
    sync_pairs(db, settings)


def initialise(db: Database, settings: Settings, clock=None) -> None:
    db.create_all()
    seed_accounts_if_missing(db, settings, clock)
    sync_pairs(db, settings)
