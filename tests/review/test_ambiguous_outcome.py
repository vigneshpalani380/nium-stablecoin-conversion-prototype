"""Ambiguous settlement outcome: automated recovery, human-review boundary and internal notification."""
import json
from decimal import Decimal

from sqlalchemy import func, select

from backend.models.entities import InternalNotification, ReviewCase
from tests.helpers import USD, USDC_SOL, balances, confirm, new_key, quote_id, txn_count

OPS = {"X-Ops-Token": "demo-ops-token"}
SEED_USD, SEED_USDC = Decimal("25000"), Decimal("5000")


def _count(container, model):
    with container.db.transaction() as s:
        return s.scalar(select(func.count()).select_from(model))


def _scenario_c(client, container, actual="ROLLED_BACK"):
    """USD 10,000 -> USDC-Solana; DB connection lost during COMMIT; recovery lookups also fail."""
    container.faults.update(uncertain_commit=actual, recovery_lookup_fails=True)
    qid = quote_id(client, USD, USDC_SOL, "10000.00")
    key = new_key()
    return qid, key, confirm(client, qid, key)


def _case_and_notification(client):
    case = client.get("/internal/v1/review-cases", headers=OPS).json()["review_cases"][0]
    ntf = client.get("/internal/v1/notifications", headers=OPS).json()["notifications"][0]
    return case, ntf


# 1 ------------------------------------------------------------------------------------------------
def test_normal_conversion_unaffected_and_no_notification(client, container):
    resp = confirm(client, quote_id(client, USD, USDC_SOL, "10000.00"), new_key())
    assert resp.status_code == 200 and resp.json()["status"] == "COMPLETED"
    b = balances(client)
    assert b[USD]["available"] == Decimal("15000") and b[USDC_SOL]["available"] == Decimal("14950")
    assert _count(container, InternalNotification) == 0 and _count(container, ReviewCase) == 0


# 2 ------------------------------------------------------------------------------------------------
def test_definitive_failure_releases_exactly_once_without_review(client, container):
    container.faults.fail_mid_settle = True
    qid, key = quote_id(client, USD, USDC_SOL, "10000.00"), new_key()
    resp = confirm(client, qid, key)
    assert resp.status_code == 500 and resp.json()["error"]["details"]["failure_code"] == "SETTLEMENT_FAILED"
    assert confirm(client, qid, key).headers["Idempotent-Replayed"] == "true"  # replay, no second release
    b = balances(client)
    assert b[USD] == {"available": SEED_USD, "reserved": 0, "pending": 0}
    assert b[USDC_SOL] == {"available": SEED_USDC, "reserved": 0, "pending": 0}
    assert _count(container, InternalNotification) == 0


# 3 ------------------------------------------------------------------------------------------------
def test_uncertain_commit_does_not_trigger_blind_retry(client, container, monkeypatch):
    calls = []
    svc_cls = type(container.conversions())
    original = svc_cls._settle

    def counting(self, s, txn_id):
        calls.append(txn_id)
        return original(self, s, txn_id)

    monkeypatch.setattr(svc_cls, "_settle", counting)
    _scenario_c(client, container)
    assert len(calls) == 1  # settlement attempted once; recovery only reads
    assert txn_count(container) == 1


# 4 ------------------------------------------------------------------------------------------------
def test_recovery_resolves_committed_settlement_without_human(client, container):
    container.faults.update(uncertain_commit="COMMITTED", recovery_lookup_fails=False)
    resp = confirm(client, quote_id(client, USD, USDC_SOL, "10000.00"), new_key())
    assert resp.status_code == 200 and resp.json()["status"] == "COMPLETED"
    b = balances(client)
    assert b[USD]["available"] == Decimal("15000") and b[USDC_SOL]["available"] == Decimal("14950")
    assert b[USDC_SOL]["pending"] == 0
    assert _count(container, ReviewCase) == 0 and _count(container, InternalNotification) == 0


# 5 ------------------------------------------------------------------------------------------------
def test_recovery_resolves_rolled_back_settlement_safely(client, container):
    container.faults.update(uncertain_commit="ROLLED_BACK", recovery_lookup_fails=False)
    qid, key = quote_id(client, USD, USDC_SOL, "10000.00"), new_key()
    resp = confirm(client, qid, key)
    assert resp.status_code == 500
    assert resp.json()["error"]["details"]["failure_code"] == "SETTLEMENT_NOT_COMMITTED"
    b = balances(client)
    assert b[USD] == {"available": SEED_USD, "reserved": 0, "pending": 0}  # released exactly once
    assert b[USDC_SOL] == {"available": SEED_USDC, "reserved": 0, "pending": 0}
    assert _count(container, ReviewCase) == 0


# 6 + 7 --------------------------------------------------------------------------------------------
def test_unresolvable_outcome_enters_review_and_customer_sees_under_review(client, container):
    _, key, resp = _scenario_c(client, container)
    assert resp.status_code == 202
    t = resp.json()
    assert t["status"] == "REVIEW_REQUIRED"
    assert t["balances"]["source"]["after"] is None and t["balances"]["destination"]["after"] is None
    assert t["last_updated_at"] is not None
    # Funds stay reserved; destination is pending (not credited).
    b = balances(client)
    assert b[USD] == {"available": Decimal("15000"), "reserved": Decimal("10000"), "pending": 0}
    assert b[USDC_SOL] == {"available": SEED_USDC, "reserved": 0, "pending": Decimal("9950")}
    # Status lookup by original key shows Under review; same-key retry does not resubmit.
    assert client.get(f"/api/v1/conversion/transactions/by-idempotency-key/{key}").json()["status"] == "REVIEW_REQUIRED"


def test_same_key_retry_while_under_review_is_rejected_without_new_notification(client, container):
    qid, key, _ = _scenario_c(client, container)
    for _ in range(3):
        r = confirm(client, qid, key)
        assert r.status_code == 409 and r.json()["error"]["code"] == "CONVERSION_UNDER_REVIEW"
    assert txn_count(container) == 1 and _count(container, InternalNotification) == 1


# 8 ------------------------------------------------------------------------------------------------
def test_customer_api_does_not_expose_internal_review_data(client, container):
    qid, key, resp = _scenario_c(client, container)
    case, ntf = _case_and_notification(client)
    customer_payloads = [
        resp.text,
        client.get(f"/api/v1/conversion/transactions/by-idempotency-key/{key}").text,
        client.get(f"/api/v1/conversion/transactions/{resp.json()['transaction_id']}").text,
        client.get("/api/v1/conversion/transactions").text,
        client.get("/api/v1/accounts").text,
    ]
    for text in customer_payloads:
        for secret in (case["review_case_id"], ntf["notification_id"], "notification", "review_case",
                       "OPERATIONS", "recovery", "database_error"):
            assert secret not in text, secret
    # Internal API requires the ops token.
    assert client.get("/internal/v1/notifications").status_code == 401
    assert client.get("/internal/v1/notifications", headers={"X-Ops-Token": "wrong"}).status_code == 401


# 9 ------------------------------------------------------------------------------------------------
def test_notification_contains_required_information(client, container):
    _, key, resp = _scenario_c(client, container)
    txn_id = resp.json()["transaction_id"]
    _, summary = _case_and_notification(client)
    assert summary["event"] == "CONVERSION_REVIEW_REQUIRED" and summary["channel"] == "EMAIL"
    assert summary["recipient_group"] == "OPERATIONS" and summary["status"] == "QUEUED" and summary["simulated"]
    n = client.get(f"/internal/v1/notifications/{summary['notification_id']}", headers=OPS).json()
    p = n["payload"]
    h = p["header"]
    assert h["subject"] == "Action Required – Conversion Outcome Unresolved" and h["priority"] == "HIGH"
    assert h["conversion_id"] == txn_id and h["idempotency_key"] == key and h["review_case_id"].startswith("RVW-")
    assert h["customer_id"] and h["review_triggered_at"]
    t = p["transaction"]
    assert t["source"] == "USD 10000.00" and t["destination_expected"] == "USDC-Solana 9950.000000"
    assert "1.0000" in t["conversion_rate"] and t["conversion_fee"].startswith("50.00 USD")
    assert t["original_transaction_timestamp"] and t["last_known_status"]
    f = p["financial_position"]
    assert (f["source_available"], f["source_reserved"]) == ("15000.00", "10000.00")
    assert (f["destination_available"], f["destination_pending"]) == ("5000.000000", "9950.000000")
    assert f["before_reservation"]["source"]["available"] == "25000.00"
    e = p["evidence"]
    assert e["settlement_attempted_at"] and "connection lost during settlement COMMIT" in e["database_error"]
    for k in ("conversion_record_found", "source_debit_found", "destination_credit_found"):
        assert str(e[k]).startswith("UNKNOWN")
    assert e["idempotency_lookup_result"].startswith("FAILED")
    assert len(e["automated_recovery_attempts"]) == 3
    assert all(a["result"] == "LOOKUP_FAILED" and a["at"] for a in e["automated_recovery_attempts"])
    assert e["last_known_system_response"] and e["why_automation_stopped"]
    assert "USD 10000.00 was reserved" in p["explanation"] and "No further conversion" in p["explanation"]
    assert len(p["required_reviewer_actions"]) == 5
    assert "SIMULATED EMAIL" in n["body"] and "F. REQUIRED ACTIONS" in n["body"]


# 10 -----------------------------------------------------------------------------------------------
def test_notification_not_duplicated_on_repeated_recovery_attempts(client, container):
    _, _, resp = _scenario_c(client, container)
    txn_id = resp.json()["transaction_id"]
    svc = container.conversions()
    for _ in range(3):  # automation re-escalating the same unresolved conversion
        again = svc.escalate(txn_id, container.clock.now(), "again", [], {}, "repeat")
        assert again.status_code == 202
    assert _count(container, InternalNotification) == 1 and _count(container, ReviewCase) == 1


# 11 -----------------------------------------------------------------------------------------------
def test_notification_creation_does_not_change_balances(client, container):
    container.faults.update(uncertain_commit="ROLLED_BACK", recovery_lookup_fails=True)
    qid = quote_id(client, USD, USDC_SOL, "10000.00")
    # Balances immediately after reservation are what the escalation must leave untouched.
    svc = container.conversions()
    with container.db.transaction() as s:
        from backend.services.idempotency.policy import request_fingerprint
        txn_id = svc._reserve(s, container.settings.customer_id, qid, "manual-key-1",
                              request_fingerprint(container.settings.customer_id, qid))
    after_reserve = balances(client)
    svc.escalate(txn_id, container.clock.now(), "simulated", [], {}, "test")
    assert balances(client) == after_reserve


# 12 -----------------------------------------------------------------------------------------------
def test_escalation_keeps_transaction_and_balances_unresolved(client, container):
    _, key, _ = _scenario_c(client, container)
    case, _ = _case_and_notification(client)
    before = balances(client)
    r = client.post(f"/internal/v1/review-cases/{case['review_case_id']}/resolution", headers=OPS,
                    json={"action": "ESCALATE", "reviewer": "ops.alex", "note": "DB replica lag; need engineering"})
    assert r.status_code == 200 and r.json()["status"] == "ESCALATED"
    assert r.json()["customer_visible_status"] == "REVIEW_REQUIRED"
    assert balances(client) == before
    assert client.get(f"/api/v1/conversion/transactions/by-idempotency-key/{key}").json()["status"] == "REVIEW_REQUIRED"


# Reviewer resolution procedure ----------------------------------------------------------------------
def test_reviewer_confirms_not_committed_releases_once_and_customer_sees_failed(client, container):
    _, key, _ = _scenario_c(client, container, actual="ROLLED_BACK")
    case, _ = _case_and_notification(client)
    cid = case["review_case_id"]
    insp = client.get(f"/internal/v1/review-cases/{cid}/inspection", headers=OPS).json()
    assert insp["evidence"]["conclusion"] == "NOT_COMMITTED" and insp["supported_action"] == "CONFIRM_NOT_COMMITTED"
    # A decision contradicting the evidence is refused.
    bad = client.post(f"/internal/v1/review-cases/{cid}/resolution", headers=OPS,
                      json={"action": "CONFIRM_COMMITTED", "reviewer": "ops.alex", "note": "guess"})
    assert bad.status_code == 409 and bad.json()["error"]["code"] == "RESOLUTION_NOT_SUPPORTED_BY_EVIDENCE"
    ok = client.post(f"/internal/v1/review-cases/{cid}/resolution", headers=OPS,
                     json={"action": "CONFIRM_NOT_COMMITTED", "reviewer": "ops.alex", "note": "No settlement marker; reservation intact"})
    assert ok.status_code == 200 and ok.json()["status"] == "RESOLVED_NOT_COMMITTED"
    b = balances(client)
    assert b[USD] == {"available": SEED_USD, "reserved": 0, "pending": 0}
    assert b[USDC_SOL] == {"available": SEED_USDC, "reserved": 0, "pending": 0}
    assert client.get(f"/api/v1/conversion/transactions/by-idempotency-key/{key}").json()["status"] == "FAILED"
    # Resolved cases cannot be actioned again (no double release).
    again = client.post(f"/internal/v1/review-cases/{cid}/resolution", headers=OPS,
                        json={"action": "CONFIRM_NOT_COMMITTED", "reviewer": "ops.alex", "note": "again"})
    assert again.status_code == 409
    assert balances(client) == b
    # Audit history and notification are retained after resolution.
    detail = client.get(f"/internal/v1/review-cases/{cid}", headers=OPS).json()
    events = [e["event"] for e in detail["audit_history"]]
    for expected in ("REQUESTED", "VALIDATED", "RESERVED", "SETTLEMENT_ATTEMPTED", "OUTCOME_UNCERTAIN",
                     "AUTOMATED_RECOVERY_ATTEMPT", "HUMAN_REVIEW_REQUIRED", "NOTIFICATION_QUEUED",
                     "REVIEW_RESOLVED_NOT_COMMITTED"):
        assert expected in events, expected
    assert len(detail["notifications"]) == 1 and detail["resolved_by"] == "ops.alex" and detail["resolved_at"]


def test_reviewer_confirms_committed_and_customer_sees_completed(client, container):
    qid, key, resp = _scenario_c(client, container, actual="COMMITTED")
    assert resp.json()["status"] == "REVIEW_REQUIRED"
    case, _ = _case_and_notification(client)
    cid = case["review_case_id"]
    assert client.get(f"/internal/v1/review-cases/{cid}/inspection", headers=OPS).json()["evidence"]["conclusion"] == "COMMITTED"
    bad = client.post(f"/internal/v1/review-cases/{cid}/resolution", headers=OPS,
                      json={"action": "CONFIRM_NOT_COMMITTED", "reviewer": "ops.alex", "note": "guess"})
    assert bad.status_code == 409  # cannot release funds of a committed settlement
    before = balances(client)
    ok = client.post(f"/internal/v1/review-cases/{cid}/resolution", headers=OPS,
                     json={"action": "CONFIRM_COMMITTED", "reviewer": "ops.alex", "note": "Settlement marker and postings present"})
    assert ok.json()["customer_visible_status"] == "COMPLETED"
    assert balances(client) == before  # confirming moves no money
    assert before[USD]["available"] == Decimal("15000") and before[USDC_SOL]["available"] == Decimal("14950")
    t = client.get(f"/api/v1/conversion/transactions/by-idempotency-key/{key}").json()
    assert t["status"] == "COMPLETED" and t["balances"]["destination"]["after"]["available"] == "14950.000000"
    replay = confirm(client, qid, key)
    assert replay.status_code == 200 and replay.json()["status"] == "COMPLETED"
    assert txn_count(container) == 1


def test_inconsistent_evidence_escalates_to_review(client, container):
    """Recovery can read records but they match neither outcome -> human review."""
    container.faults.update(uncertain_commit="ROLLED_BACK", recovery_lookup_fails=False)
    qid = quote_id(client, USD, USDC_SOL, "100.00")
    from backend.services.operations import evidence as ev

    original = ev.inspect_settlement

    def tampered(s, txn_id):
        # Simulate inconsistent records: reservation missing although no settlement marker exists.
        e = original(s, txn_id)
        return ev.SettlementEvidence(**{**e.to_dict(), "reservation_still_held": False,
                                        "conclusion": ev.INCONCLUSIVE, "explanation": "reservation missing"})

    import backend.services.conversions.service as conv_mod
    conv_mod.ev.inspect_settlement = tampered
    try:
        resp = confirm(client, qid, new_key())
    finally:
        conv_mod.ev.inspect_settlement = original
    assert resp.status_code == 202 and resp.json()["status"] == "REVIEW_REQUIRED"
    with container.db.transaction() as s:
        case = s.scalar(select(ReviewCase))
        assert "Inconsistent evidence" in case.reason
        assert len(json.loads(case.evidence_json)["automated_recovery_attempts"]) == 1


def test_startup_reconcile_never_touches_review_required(settings, clock):
    from fastapi.testclient import TestClient
    from backend.main import create_app

    app = create_app(settings, clock)
    client = TestClient(app, raise_server_exceptions=False)
    _scenario_c(client, app.state.container)
    held = balances(client)
    app.state.container.db.dispose()
    app2 = create_app(settings, clock)  # restart runs reconcile
    client2 = TestClient(app2, raise_server_exceptions=False)
    assert balances(client2) == held
    app2.state.container.db.dispose()
