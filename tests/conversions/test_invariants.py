"""Q001: property-style invariant check over a deterministic random sequence of conversions."""
import random
from decimal import Decimal

from tests.helpers import INR, USD, USDC_SOL, balances, confirm, make_quote, new_key

PAIRS = [(USD, USDC_SOL), (USDC_SOL, USD), (USDC_SOL, INR), (INR, USDC_SOL)]
PRECISION = {USD: 2, INR: 2, USDC_SOL: 6}


def test_random_conversion_sequence_preserves_invariants(client, container):
    rng = random.Random(20261119)
    expected = {k: v["available"] for k, v in balances(client).items()}
    completed = rejected = failed = 0

    for i in range(60):
        src, dst = rng.choice(PAIRS)
        scale = Decimal(1).scaleb(-PRECISION[src])
        amount = (Decimal(rng.randint(1, 4_000_00)) / 100 * (100 if src == INR else 1)).quantize(scale)
        q = make_quote(client, src, dst, str(amount))
        if q.status_code != 201:
            assert q.json()["error"]["code"] == "INSUFFICIENT_BALANCE"
            rejected += 1
            continue
        if i % 13 == 0:
            container.faults.fail_mid_settle = True
        resp = confirm(client, q.json()["quote_id"], new_key())
        if resp.status_code == 200:
            t = resp.json()
            expected[src] -= Decimal(t["gross_source_amount"])
            expected[dst] += Decimal(t["destination_amount"])
            # per-transaction invariants
            sb, sa = t["balances"]["source"]["before"], t["balances"]["source"]["after"]
            db_, da = t["balances"]["destination"]["before"], t["balances"]["destination"]["after"]
            assert Decimal(sb["available"]) - Decimal(sa["available"]) == Decimal(t["gross_source_amount"])
            assert Decimal(da["available"]) - Decimal(db_["available"]) == Decimal(t["destination_amount"])
            assert Decimal(t["gross_source_amount"]) == Decimal(t["fee_amount"]) + Decimal(t["net_source_amount"])
            completed += 1
        else:
            assert resp.json()["error"]["code"] == "CONVERSION_FAILED"
            failed += 1

        now = balances(client)
        for acct, vals in now.items():
            assert vals["available"] >= 0
            assert vals["reserved"] == 0 and vals["pending"] == 0  # nothing left in flight
            assert vals["available"] == expected[acct], (i, acct)

    assert completed > 20 and failed >= 1
