"""Conversion configuration for the UI: enabled pairs (resolved to account ids), fee, TTL, precision."""
from fastapi import APIRouter, Depends

from backend.api.deps import get_container
from backend.config.settings import RATE_SOURCE
from backend.container import Container
from backend.domain.money import ROUNDING
from backend.domain.support import display_name
from backend.repositories.accounts import AccountRepository
from backend.repositories.records import PairRepository

router = APIRouter(prefix="/api/v1", tags=["config"])


@router.get("/conversion/config")
def conversion_config(c: Container = Depends(get_container)) -> dict:
    with c.db.transaction() as s:
        accounts = AccountRepository(s).list_for_customer(c.settings.customer_id)
        pairs = PairRepository(s).list_enabled()
    by_identity = {(a.asset_code, a.network_key): a for a in accounts}
    resolved = []
    for p in pairs:
        src = by_identity.get((p.source_asset_code, p.source_network_key))
        dst = by_identity.get((p.destination_asset_code, p.destination_network_key))
        if src is None or dst is None:
            continue
        resolved.append({
            "source_account_id": src.id,
            "destination_account_id": dst.id,
            "source_display_name": display_name(src.asset_code, src.network),
            "destination_display_name": display_name(dst.asset_code, dst.network),
        })
    return {
        "customer_id": c.settings.customer_id,
        "fee_rate": str(c.settings.fee_rate),
        "fee_currency_mode": "SOURCE",
        "quote_ttl_seconds": c.settings.quote_ttl_seconds,
        "rate_source": RATE_SOURCE,
        "rounding": ROUNDING,
        "assets": [
            {"account_id": a.id, "asset_code": a.asset_code, "network": a.network,
             "display_name": display_name(a.asset_code, a.network), "precision": a.precision}
            for a in accounts
        ],
        "pairs": resolved,
        "demo_mode": c.settings.demo_mode,
    }
