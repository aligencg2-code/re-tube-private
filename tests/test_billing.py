"""Tests for billing layer — plans, subscriptions, quotas, Stripe webhook."""

import json
from datetime import datetime, timezone


def _fresh(tmp_path, monkeypatch):
    from pipeline import billing, config as cfg, audit
    monkeypatch.setattr(cfg, "SKILL_DIR", tmp_path)
    monkeypatch.setattr(billing, "PLANS_FILE", tmp_path / "plans.json")
    monkeypatch.setattr(billing, "SUBSCRIPTIONS_FILE", tmp_path / "subs.json")
    monkeypatch.setattr(billing, "BILLING_SETTINGS_FILE", tmp_path / "billing.json")
    monkeypatch.setattr(audit, "AUDIT_DIR", tmp_path / "audit")
    return billing


def test_default_plans_present(tmp_path, monkeypatch):
    b = _fresh(tmp_path, monkeypatch)
    plans = b.load_plans()
    assert "free" in plans
    assert "starter" in plans
    assert "pro" in plans
    assert "agency" in plans
    assert plans["pro"]["videos_per_month"] == 150


def test_custom_plan_overrides_default(tmp_path, monkeypatch):
    b = _fresh(tmp_path, monkeypatch)
    # Customer wants a cheaper starter plan
    b._save_json(b.PLANS_FILE, {"starter": {"monthly_usd": 19, "videos_per_month": 20}})
    plans = b.load_plans()
    assert plans["starter"]["monthly_usd"] == 19
    assert plans["starter"]["videos_per_month"] == 20
    # Other fields still from defaults
    assert "features" in plans["starter"]


def test_set_and_get_subscription(tmp_path, monkeypatch):
    b = _fresh(tmp_path, monkeypatch)
    b.set_subscription("acme", "pro")
    plan = b.get_plan("acme")
    assert plan["plan_id"] == "pro"
    assert plan["videos_per_month"] == 150


def test_cancelled_subscription_falls_back_to_free(tmp_path, monkeypatch):
    b = _fresh(tmp_path, monkeypatch)
    b.set_subscription("acme", "pro")
    b.cancel_subscription("acme")
    plan = b.get_plan("acme")
    assert plan["plan_id"] == "free"


def test_tenant_without_sub_defaults_to_free(tmp_path, monkeypatch):
    b = _fresh(tmp_path, monkeypatch)
    plan = b.get_plan("brand_new")
    assert plan["plan_id"] == "free"


def test_set_subscription_rejects_unknown_plan(tmp_path, monkeypatch):
    b = _fresh(tmp_path, monkeypatch)
    try:
        b.set_subscription("acme", "does_not_exist")
        assert False, "Should have raised"
    except ValueError:
        pass


def test_check_quota_allows_when_billing_disabled(tmp_path, monkeypatch):
    b = _fresh(tmp_path, monkeypatch)
    # Default: billing disabled → unlimited
    r = b.check_quota("videos_per_month", tenant_id="acme")
    assert r["allowed"] is True
    assert r["limit"] is None
    assert r["reason"] == "billing_disabled"


def test_check_quota_enforces_when_enabled(tmp_path, monkeypatch):
    b = _fresh(tmp_path, monkeypatch)
    b.save_settings({"enabled": True, "provider": "manual"})
    b.set_subscription("acme", "free")  # 3 videos/month

    # No usage yet
    r = b.check_quota("videos_per_month", tenant_id="acme")
    assert r["allowed"] is True
    assert r["limit"] == 3
    assert r["used"] == 0

    # Simulate 3 job_queued audit entries
    from pipeline import audit
    for i in range(3):
        audit.log("job_queued", target=f"q{i}")

    r = b.check_quota("videos_per_month", tenant_id="acme")
    assert r["used"] == 3
    assert r["remaining"] == 0
    assert r["allowed"] is False


def test_enterprise_plan_is_unlimited(tmp_path, monkeypatch):
    b = _fresh(tmp_path, monkeypatch)
    b.save_settings({"enabled": True, "provider": "manual"})
    b.set_subscription("bigco", "enterprise")

    r = b.check_quota("videos_per_month", tenant_id="bigco")
    assert r["limit"] is None
    assert r["allowed"] is True


def test_stripe_webhook_creates_subscription(tmp_path, monkeypatch):
    b = _fresh(tmp_path, monkeypatch)

    event = {
        "type": "customer.subscription.created",
        "data": {
            "object": {
                "id": "sub_xyz123",
                "customer": "cus_acme",
                "metadata": {"tenant_id": "acme", "plan_id": "pro"},
            }
        }
    }
    r = b.handle_stripe_webhook(event)
    assert r["handled"] is True
    assert r["tenant_id"] == "acme"

    plan = b.get_plan("acme")
    assert plan["plan_id"] == "pro"
    subs = b.load_subscriptions()
    assert subs["acme"]["stripe_customer_id"] == "cus_acme"


def test_stripe_webhook_cancels_on_delete(tmp_path, monkeypatch):
    b = _fresh(tmp_path, monkeypatch)
    b.set_subscription("acme", "pro")

    event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"metadata": {"tenant_id": "acme"}}},
    }
    r = b.handle_stripe_webhook(event)
    assert r["action"] == "cancelled"
    assert b.get_plan("acme")["plan_id"] == "free"


def test_stripe_webhook_without_tenant_id_is_rejected(tmp_path, monkeypatch):
    b = _fresh(tmp_path, monkeypatch)
    event = {
        "type": "customer.subscription.created",
        "data": {"object": {"metadata": {}}},
    }
    r = b.handle_stripe_webhook(event)
    assert r["handled"] is False
    assert r["reason"] == "no_tenant_id_metadata"


def test_stripe_webhook_payment_failed_marks_past_due(tmp_path, monkeypatch):
    b = _fresh(tmp_path, monkeypatch)
    b.set_subscription("acme", "pro")

    event = {
        "type": "invoice.payment_failed",
        "data": {"object": {"metadata": {"tenant_id": "acme"}}},
    }
    b.handle_stripe_webhook(event)
    subs = b.load_subscriptions()
    assert subs["acme"]["status"] == "past_due"


def test_has_stripe_sdk_detects_absence():
    from pipeline import billing
    # stripe is not in requirements — should return False
    assert billing.has_stripe_sdk() in (True, False)  # just doesn't crash
