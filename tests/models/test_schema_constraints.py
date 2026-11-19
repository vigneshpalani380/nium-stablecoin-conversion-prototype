import pytest
from sqlalchemy.exc import IntegrityError

from backend.models.entities import Account, IdempotencyRecord


def test_account_identity_unique_even_with_null_fiat_network(container, clock):
    now = clock.now()
    with pytest.raises(IntegrityError):
        with container.db.transaction() as s:
            s.add(Account(id="acct-usd-dup", customer_id=container.settings.customer_id, asset_code="USD",
                          asset_type="FIAT", network=None, network_key="", precision=2, available_minor=0,
                          reserved_minor=0, pending_minor=0, status="ACTIVE", version=0,
                          created_at=now, updated_at=now))


@pytest.mark.parametrize("column", ["available_minor", "reserved_minor", "pending_minor"])
def test_balances_cannot_go_negative(container, column):
    with pytest.raises(IntegrityError):
        with container.db.transaction() as s:
            setattr(s.get(Account, "acct-usd"), column, -1)


def test_idempotency_key_unique_per_customer(container, clock):
    now = clock.now()
    rec = dict(customer_id="c1", idempotency_key="k-12345678", request_fingerprint="f", state="IN_PROGRESS",
               created_at=now, updated_at=now)
    with container.db.transaction() as s:
        s.add(IdempotencyRecord(**rec))
    with pytest.raises(IntegrityError):
        with container.db.transaction() as s:
            s.add(IdempotencyRecord(**rec))


def test_failed_transaction_block_rolls_back_everything(container):
    with pytest.raises(RuntimeError):
        with container.db.transaction() as s:
            s.get(Account, "acct-usd").available_minor = 1
            raise RuntimeError("boom")
    with container.db.transaction() as s:
        assert s.get(Account, "acct-usd").available_minor == 2_500_000
