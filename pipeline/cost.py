"""Usage cost tracking.

Every pipeline stage that calls a paid provider appends a JSONL entry with:
    timestamp, job_id, stage, category, provider_key, model, amount_usd, units

`units` is free-form: seconds of voiceover, # of frames, # of tokens, etc.
Records are persisted to SKILL_DIR/usage/YYYY-MM.jsonl so files rotate monthly
and parsing is O(month). Query helpers produce totals, per-provider breakdowns,
and a daily series for charting.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Iterable

from .config import SKILL_DIR, PROVIDERS


USAGE_DIR = SKILL_DIR / "usage"


def _ensure_dir() -> None:
    USAGE_DIR.mkdir(parents=True, exist_ok=True)


def _month_file(dt: datetime | None = None) -> Path:
    dt = dt or datetime.now(timezone.utc)
    return USAGE_DIR / f"{dt.strftime('%Y-%m')}.jsonl"


def record(
    *,
    job_id: str | None,
    stage: str,
    category: str,
    provider_key: str,
    model: str | None = None,
    amount_usd: float = 0.0,
    units: str = "",
    extra: dict | None = None,
) -> None:
    """Append one cost record. Never raises — logging failures must not break the pipeline."""
    try:
        _ensure_dir()
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "job_id": job_id,
            "stage": stage,
            "category": category,
            "provider": provider_key,
            "model": model,
            "amount_usd": round(float(amount_usd), 6),
            "units": units,
        }
        if extra:
            entry["extra"] = extra
        with open(_month_file(), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # Never let cost logging crash a pipeline step
        pass


def estimated_cost(category: str, provider_key: str, seconds: float = 60.0) -> float:
    """Look up per-60s cost from PROVIDERS catalog and scale by `seconds`."""
    try:
        cost_60s = PROVIDERS.get(category, {}).get(provider_key, {}).get("cost_60s", 0.0)
        return round(float(cost_60s) * (seconds / 60.0), 6)
    except Exception:
        return 0.0


def record_estimated(
    *,
    job_id: str | None,
    stage: str,
    category: str,
    provider_key: str,
    seconds: float = 60.0,
    model: str | None = None,
    extra: dict | None = None,
) -> float:
    """Convenience: compute estimated cost from PROVIDERS catalog then record it."""
    amount = estimated_cost(category, provider_key, seconds)
    record(
        job_id=job_id, stage=stage, category=category, provider_key=provider_key,
        model=model, amount_usd=amount, units=f"{seconds:.1f}s", extra=extra,
    )
    return amount


def _iter_records(since: datetime | None = None) -> Iterable[dict]:
    _ensure_dir()
    # Decide which month files to scan. Scan all if since=None.
    if since is None:
        files = sorted(USAGE_DIR.glob("*.jsonl"))
    else:
        # Inclusive: from `since`'s month onward
        start = since.replace(day=1)
        files = []
        cursor = start
        now = datetime.now(since.tzinfo or timezone.utc)
        while cursor.date() <= now.date():
            f = USAGE_DIR / f"{cursor.strftime('%Y-%m')}.jsonl"
            if f.exists():
                files.append(f)
            # Move to next month
            year, month = cursor.year, cursor.month + 1
            if month > 12:
                year, month = year + 1, 1
            cursor = cursor.replace(year=year, month=month)

    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if since is not None:
                        try:
                            ts = datetime.fromisoformat(rec["ts"].replace("Z", "+00:00"))
                            if ts < since:
                                continue
                        except Exception:
                            continue
                    yield rec
        except FileNotFoundError:
            continue


def summary(days: int = 30) -> dict:
    """Return totals for the last N days.

    Output:
        {
            "total_usd": float,
            "job_count": int,
            "by_category": {category: usd},
            "by_provider": {provider_key: usd},
            "daily_series": [{"date": "YYYY-MM-DD", "usd": x.yy}, ...],  # oldest first, zero-filled
        }
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    total = 0.0
    by_cat: dict[str, float] = {}
    by_prov: dict[str, float] = {}
    daily: dict[str, float] = {}
    jobs: set[str] = set()

    for rec in _iter_records(since=since):
        amt = float(rec.get("amount_usd", 0.0) or 0.0)
        total += amt
        by_cat[rec.get("category", "?")] = by_cat.get(rec.get("category", "?"), 0.0) + amt
        by_prov[rec.get("provider", "?")] = by_prov.get(rec.get("provider", "?"), 0.0) + amt
        try:
            d = rec["ts"][:10]
            daily[d] = daily.get(d, 0.0) + amt
        except Exception:
            pass
        jid = rec.get("job_id")
        if jid:
            jobs.add(jid)

    # Zero-fill daily series for smooth chart
    series = []
    start = (datetime.now(timezone.utc) - timedelta(days=days - 1)).date()
    for i in range(days):
        d = (start + timedelta(days=i)).strftime("%Y-%m-%d")
        series.append({"date": d, "usd": round(daily.get(d, 0.0), 4)})

    # Round totals for display
    return {
        "total_usd": round(total, 4),
        "job_count": len(jobs),
        "by_category": {k: round(v, 4) for k, v in sorted(by_cat.items(), key=lambda x: -x[1])},
        "by_provider": {k: round(v, 4) for k, v in sorted(by_prov.items(), key=lambda x: -x[1])},
        "daily_series": series,
    }


def month_to_date_usd() -> float:
    """Spend from the 1st of current month (UTC) until now."""
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total = 0.0
    for rec in _iter_records(since=start):
        total += float(rec.get("amount_usd", 0.0) or 0.0)
    return round(total, 4)


def today_usd() -> float:
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    total = 0.0
    for rec in _iter_records(since=start):
        total += float(rec.get("amount_usd", 0.0) or 0.0)
    return round(total, 4)


def per_job_costs(limit: int = 20) -> list[dict]:
    """Aggregate cost per job_id, most recent first."""
    per_job: dict[str, dict] = {}
    for rec in _iter_records():
        jid = rec.get("job_id")
        if not jid:
            continue
        if jid not in per_job:
            per_job[jid] = {"job_id": jid, "total_usd": 0.0, "last_ts": rec["ts"]}
        per_job[jid]["total_usd"] += float(rec.get("amount_usd", 0.0) or 0.0)
        if rec["ts"] > per_job[jid]["last_ts"]:
            per_job[jid]["last_ts"] = rec["ts"]
    jobs = sorted(per_job.values(), key=lambda x: x["last_ts"], reverse=True)[:limit]
    for j in jobs:
        j["total_usd"] = round(j["total_usd"], 4)
    return jobs
