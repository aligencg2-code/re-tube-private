"""Audit log — record every meaningful action for compliance + debugging.

Events go to SKILL_DIR/audit/YYYY-MM.jsonl. Monthly rotation keeps individual
files small enough to grep quickly but still gives a long history.

Every entry captures:
    timestamp (UTC ISO8601), actor (user/tenant id), action (verb), target,
    details (free-form dict), ip (if web), result ("ok"|"fail"|"denied").

The `log()` call is fire-and-forget — never raises, never blocks on disk I/O
errors. An audit outage must not break the product.

API
    log(action, target, *, actor=None, details=None, result="ok", ip=None)
    query(filters={}, days=30, limit=500) -> list[dict]
    export_csv(out_path, days=90) -> Path
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Iterable

from .config import SKILL_DIR


AUDIT_DIR = SKILL_DIR / "audit"


# Canonical action verbs — extendable, these are just the ones we emit from
# the codebase today. Keep them lowercase + underscore.
ACTIONS = {
    # Auth / channels
    "channel_added", "channel_removed", "channel_oauth",
    # Queue
    "job_queued", "job_cancelled", "job_retried", "job_completed", "job_failed",
    # Draft / script
    "draft_edited", "script_regenerated", "draft_requeued",
    # Publish
    "video_uploaded", "video_scheduled", "video_deleted",
    "playlist_added", "thumbnail_rotated", "thumbnail_winner_picked",
    # Moderation
    "comment_hidden", "comment_handled",
    # System
    "worker_started", "worker_stopped", "worker_recovered",
    "preset_saved", "preset_deleted",
    "provider_changed", "apikey_added", "apikey_removed",
    # Admin
    "tenant_created", "tenant_deleted", "user_login", "user_logout",
}


def _ensure_dir() -> None:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)


def _current_file() -> Path:
    return AUDIT_DIR / f"{datetime.now(timezone.utc).strftime('%Y-%m')}.jsonl"


def log(
    action: str,
    target: str = "",
    *,
    actor: str | None = None,
    details: dict | None = None,
    result: str = "ok",
    ip: str | None = None,
) -> None:
    """Record one audit entry. Never raises."""
    try:
        _ensure_dir()
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "actor": actor or "system",
            "action": action,
            "target": target,
            "result": result,
            "details": details or {},
        }
        if ip:
            entry["ip"] = ip
        with open(_current_file(), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # Audit logging is best-effort — never break the caller
        pass


def _iter_records(since: datetime | None = None) -> Iterable[dict]:
    _ensure_dir()
    if since is None:
        files = sorted(AUDIT_DIR.glob("*.jsonl"))
    else:
        # Scan from `since`'s month onward
        start = since.replace(day=1)
        files = []
        cursor = start
        now = datetime.now(since.tzinfo or timezone.utc)
        while cursor.date() <= now.date():
            f = AUDIT_DIR / f"{cursor.strftime('%Y-%m')}.jsonl"
            if f.exists():
                files.append(f)
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


def query(
    *,
    action: str | None = None,
    actor: str | None = None,
    result: str | None = None,
    target_contains: str | None = None,
    days: int = 30,
    limit: int = 500,
) -> list[dict]:
    """Query audit log with AND-style filters. Newest first."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    out: list[dict] = []
    for rec in _iter_records(since=since):
        if action and rec.get("action") != action:
            continue
        if actor and rec.get("actor") != actor:
            continue
        if result and rec.get("result") != result:
            continue
        if target_contains and target_contains.lower() not in (rec.get("target") or "").lower():
            continue
        out.append(rec)
    out.sort(key=lambda x: x.get("ts", ""), reverse=True)
    return out[:limit]


def counts_by_action(days: int = 7) -> dict[str, int]:
    """Return {action: count} over last N days — for a leaderboard widget."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    out: dict[str, int] = {}
    for rec in _iter_records(since=since):
        a = rec.get("action", "?")
        out[a] = out.get(a, 0) + 1
    return dict(sorted(out.items(), key=lambda x: -x[1]))


def export_csv(out_path: Path, *, days: int = 90) -> Path:
    """Write a flat CSV for external audit / compliance."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "actor", "action", "target", "result", "ip", "details"])
        for rec in _iter_records(since=since):
            w.writerow([
                rec.get("ts", ""),
                rec.get("actor", ""),
                rec.get("action", ""),
                rec.get("target", ""),
                rec.get("result", ""),
                rec.get("ip", ""),
                json.dumps(rec.get("details", {}), ensure_ascii=False),
            ])
    return out_path
