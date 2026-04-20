"""Billing & quota layer — pluggable, Stripe-optional.

This module tracks per-tenant (or single-user) usage and enforces plan limits.
Actual payment processing is pluggable — a customer can:
    1. Leave it disabled (no billing, unlimited usage) — factory default
    2. Use the manual "invoice" mode — admin sets quota manually via UI
    3. Connect Stripe — webhooks update subscription state automatically

Plans are defined in SKILL_DIR/billing_plans.json. Subscriptions go in
SKILL_DIR/billing_subscriptions.json.

Quota types:
    - videos_per_month: hard cap on new `job_queued` events
    - api_calls_per_day: hard cap on REST API requests (future)
    - storage_gb: soft warning when media/ exceeds

`check_quota(tenant_id, kind)` returns (allowed, remaining, limit) — callers
decide whether to block or warn. Quota evaluation is quota-vs-audit-log:
count job_queued events for the current tenant in the current billing period,
compare against plan.

The Stripe hook is deferred import. If stripe isn't installed, only manual
mode works. Admin pastes webhook secret in Settings → we register the
webhook and persist events via api_server.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from . import config as _cfg


PLANS_FILE = _cfg.SKILL_DIR / "billing_plans.json"
SUBSCRIPTIONS_FILE = _cfg.SKILL_DIR / "billing_subscriptions.json"
BILLING_SETTINGS_FILE = _cfg.SKILL_DIR / "billing_settings.json"


# ────────────────────────────────────────────────────────────
# Built-in starter plans — customers can override in PLANS_FILE
# ────────────────────────────────────────────────────────────
DEFAULT_PLANS: dict[str, dict[str, Any]] = {
    "free": {
        "name": "Free",
        "monthly_usd": 0,
        "videos_per_month": 3,
        "storage_gb": 2,
        "api_calls_per_day": 0,
        "features": ["basic"],
    },
    "starter": {
        "name": "Starter",
        "monthly_usd": 29,
        "videos_per_month": 30,
        "storage_gb": 20,
        "api_calls_per_day": 100,
        "features": ["basic", "scheduled_publish", "playlist"],
    },
    "pro": {
        "name": "Pro",
        "monthly_usd": 99,
        "videos_per_month": 150,
        "storage_gb": 100,
        "api_calls_per_day": 1000,
        "features": ["basic", "scheduled_publish", "playlist", "ab_test",
                     "comment_mod", "topic_memory", "channel_stats"],
    },
    "agency": {
        "name": "Agency",
        "monthly_usd": 499,
        "videos_per_month": 1000,
        "storage_gb": 500,
        "api_calls_per_day": 10000,
        "features": ["basic", "scheduled_publish", "playlist", "ab_test",
                     "comment_mod", "topic_memory", "channel_stats",
                     "multi_tenant", "white_label", "api", "audit_export"],
    },
    "enterprise": {
        "name": "Enterprise",
        "monthly_usd": None,  # custom
        "videos_per_month": None,  # unlimited
        "storage_gb": None,
        "api_calls_per_day": None,
        "features": ["all"],
    },
}


# ────────────────────────────────────────────────────────────
# Storage helpers (load/save)
# ────────────────────────────────────────────────────────────
def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_plans() -> dict:
    custom = _load_json(PLANS_FILE, {})
    # Merge custom over defaults
    out = {k: dict(v) for k, v in DEFAULT_PLANS.items()}
    for k, v in custom.items():
        out[k] = {**out.get(k, {}), **v}
    return out


def load_subscriptions() -> dict:
    """Map tenant_id -> subscription dict."""
    return _load_json(SUBSCRIPTIONS_FILE, {})


def load_settings() -> dict:
    return _load_json(BILLING_SETTINGS_FILE, {
        "enabled": False,
        "provider": "disabled",  # disabled | manual | stripe
        "stripe_public_key": "",
        "stripe_secret_key": "",
        "stripe_webhook_secret": "",
    })


def save_settings(settings: dict) -> None:
    current = load_settings()
    current.update(settings)
    _save_json(BILLING_SETTINGS_FILE, current)


# ────────────────────────────────────────────────────────────
# Subscription management (manual mode — admin sets the plan)
# ────────────────────────────────────────────────────────────
def set_subscription(
    tenant_id: str,
    plan_id: str,
    *,
    started_at: str | None = None,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
) -> dict:
    plans = load_plans()
    if plan_id not in plans:
        raise ValueError(f"Unknown plan: {plan_id}")
    subs = load_subscriptions()
    subs[tenant_id] = {
        "plan_id": plan_id,
        "status": "active",
        "started_at": started_at or datetime.now(timezone.utc).isoformat(),
        "stripe_customer_id": stripe_customer_id,
        "stripe_subscription_id": stripe_subscription_id,
    }
    _save_json(SUBSCRIPTIONS_FILE, subs)
    try:
        from . import audit
        audit.log("provider_changed", target=f"billing:{tenant_id}",
                  details={"plan_id": plan_id})
    except Exception:
        pass
    return subs[tenant_id]


def cancel_subscription(tenant_id: str) -> bool:
    subs = load_subscriptions()
    if tenant_id not in subs:
        return False
    subs[tenant_id]["status"] = "cancelled"
    subs[tenant_id]["cancelled_at"] = datetime.now(timezone.utc).isoformat()
    _save_json(SUBSCRIPTIONS_FILE, subs)
    return True


def get_plan(tenant_id: str) -> dict:
    """Return the tenant's active plan (or `free` if none)."""
    subs = load_subscriptions()
    plans = load_plans()
    sub = subs.get(tenant_id) or {}
    plan_id = sub.get("plan_id", "free")
    if sub.get("status") == "cancelled":
        plan_id = "free"
    return {"plan_id": plan_id, **plans.get(plan_id, plans["free"])}


# ────────────────────────────────────────────────────────────
# Usage counting — queries audit log
# ────────────────────────────────────────────────────────────
def _period_start_utc() -> datetime:
    """Start of the current billing month (simple calendar month)."""
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def videos_used_this_period(tenant_id: str | None = None) -> int:
    """Count job_queued events in the current billing period for this tenant.

    Since audit log doesn't yet carry tenant_id explicitly for every entry,
    we count all job_queued in the period. Once tenant-aware audit is wired,
    add a filter here.
    """
    try:
        from . import audit
        start = _period_start_utc()
        days = (datetime.now(timezone.utc) - start).days + 1
        entries = audit.query(action="job_queued", days=days, limit=10000)
        return len(entries)
    except Exception:
        return 0


def check_quota(kind: str, tenant_id: str | None = None) -> dict:
    """Return {allowed, used, limit, remaining, plan} for a quota kind.

    kind: "videos_per_month" | "api_calls_per_day" | "storage_gb"
    """
    # When billing is disabled, everything is allowed
    settings = load_settings()
    if not settings.get("enabled"):
        return {"allowed": True, "used": 0, "limit": None,
                "remaining": None, "plan": "unlimited",
                "reason": "billing_disabled"}

    tid = tenant_id or "default"
    plan = get_plan(tid)
    limit = plan.get(kind)
    if limit is None:  # enterprise = unlimited
        return {"allowed": True, "used": 0, "limit": None,
                "remaining": None, "plan": plan.get("plan_id")}

    if kind == "videos_per_month":
        used = videos_used_this_period(tid)
    elif kind == "storage_gb":
        used = 0  # TODO: scan media/ size
    else:
        used = 0

    remaining = max(0, limit - used)
    return {
        "allowed": used < limit,
        "used": used,
        "limit": limit,
        "remaining": remaining,
        "plan": plan.get("plan_id"),
    }


# ────────────────────────────────────────────────────────────
# Stripe integration (optional)
# ────────────────────────────────────────────────────────────
def has_stripe_sdk() -> bool:
    """Is the stripe PyPI package installed?"""
    try:
        import stripe  # noqa: F401
        return True
    except ImportError:
        return False


def handle_stripe_webhook(payload: dict, signature: str | None = None) -> dict:
    """Process a Stripe event payload. Returns {handled, action, tenant_id}.

    Supported events:
        customer.subscription.created / updated / deleted
        invoice.paid, invoice.payment_failed
    """
    event_type = payload.get("type", "")
    obj = (payload.get("data") or {}).get("object", {}) or {}

    # Map Stripe customer metadata → tenant_id (customer must set tenant_id
    # in metadata at checkout)
    tenant_id = (obj.get("metadata") or {}).get("tenant_id")
    if not tenant_id:
        return {"handled": False, "reason": "no_tenant_id_metadata"}

    if event_type in ("customer.subscription.created",
                      "customer.subscription.updated"):
        plan_id = (obj.get("metadata") or {}).get("plan_id", "pro")
        set_subscription(
            tenant_id, plan_id,
            stripe_customer_id=obj.get("customer"),
            stripe_subscription_id=obj.get("id"),
        )
        try:
            from . import audit
            audit.log("provider_changed", target=f"stripe:{tenant_id}",
                      details={"event": event_type, "plan_id": plan_id})
        except Exception:
            pass
        return {"handled": True, "action": "subscription_upserted",
                "tenant_id": tenant_id}

    if event_type == "customer.subscription.deleted":
        cancel_subscription(tenant_id)
        return {"handled": True, "action": "cancelled", "tenant_id": tenant_id}

    if event_type == "invoice.payment_failed":
        subs = load_subscriptions()
        if tenant_id in subs:
            subs[tenant_id]["status"] = "past_due"
            _save_json(SUBSCRIPTIONS_FILE, subs)
        return {"handled": True, "action": "marked_past_due",
                "tenant_id": tenant_id}

    return {"handled": False, "reason": f"unhandled_event:{event_type}"}
