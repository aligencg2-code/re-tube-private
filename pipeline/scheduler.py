"""Recurring job scheduler — "gece modu" (night mode), daily digest, recurring publishes.

Customers save lists of topics to publish on a schedule:
    - "Her gün 09:00, 12:00, 18:00 saatlerinde 1 video üret"
    - "Gece yatmadan 5 konu bırak, sabah kuyruk hazır olsun"

Scheduling is persisted to SKILL_DIR/schedules.json. The queue worker's
idle loop checks pending schedules every minute and enqueues jobs as their
time arrives.

Schedule types:
    - "cron": runs at specified UTC hours (list of HH:MM)
    - "burst": picks N topics from a pool, enqueues them staggered
    - "daily_topic_pool": rotates through a topic list, 1/day
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .config import SKILL_DIR


SCHEDULES_FILE = SKILL_DIR / "schedules.json"


def _load() -> list[dict]:
    if not SCHEDULES_FILE.exists():
        return []
    try:
        return json.loads(SCHEDULES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(schedules: list[dict]) -> None:
    SCHEDULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    SCHEDULES_FILE.write_text(
        json.dumps(schedules, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def list_schedules() -> list[dict]:
    return _load()


def create_schedule(
    *,
    name: str,
    kind: str = "cron",
    topics: list[str],
    hours_utc: list[str] | None = None,
    count_per_burst: int = 3,
    channel: str | None = None,
    lang: str = "tr",
    mode: str = "full",
    enabled: bool = True,
) -> dict:
    """Create a new recurring schedule.

    kind='cron' → enqueue one of `topics` at each time in `hours_utc`
    kind='burst' → enqueue `count_per_burst` topics immediately, staggered
    kind='daily_topic_pool' → rotate through `topics`, one per day
    """
    schedules = _load()
    sid = f"sch_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    sched = {
        "id": sid,
        "name": name,
        "kind": kind,
        "topics": topics,
        "hours_utc": hours_utc or [],
        "count_per_burst": count_per_burst,
        "channel": channel,
        "lang": lang,
        "mode": mode,
        "enabled": enabled,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_fired_at": None,
        "fired_count": 0,
        "topic_index": 0,
    }
    schedules.append(sched)
    _save(schedules)
    try:
        from . import audit
        audit.log("tenant_created", target=f"schedule:{sid}",
                  details={"name": name, "kind": kind})
    except Exception:
        pass
    return sched


def delete_schedule(schedule_id: str) -> bool:
    schedules = _load()
    before = len(schedules)
    schedules = [s for s in schedules if s["id"] != schedule_id]
    if len(schedules) == before:
        return False
    _save(schedules)
    return True


def toggle_schedule(schedule_id: str, enabled: bool) -> bool:
    schedules = _load()
    for s in schedules:
        if s["id"] == schedule_id:
            s["enabled"] = enabled
            _save(schedules)
            return True
    return False


def run_burst(schedule_id: str) -> dict:
    """Manually fire a burst schedule now — useful for 'Gece Modu' button."""
    schedules = _load()
    sched = next((s for s in schedules if s["id"] == schedule_id), None)
    if not sched:
        return {"error": "not_found"}
    return _fire_schedule(sched, schedules)


def _fire_schedule(sched: dict, all_schedules: list[dict],
                    now: datetime | None = None) -> dict:
    """Enqueue jobs for this schedule. Mutates `sched` + saves.

    When called via tick(), pass the synthetic `now` so last_fired_at stays
    consistent with the injected time (makes tests deterministic).
    """
    from . import queue as qmod
    queued = []
    kind = sched["kind"]
    if not sched["topics"]:
        return {"error": "no_topics"}

    if kind == "cron":
        # Pick a random topic
        topic = random.choice(sched["topics"])
        job = qmod.enqueue(
            topic=topic, lang=sched["lang"], mode=sched["mode"],
            channel=sched["channel"],
            extra={"scheduled_by": sched["id"]},
        )
        queued.append(job["id"])

    elif kind == "burst":
        n = min(sched["count_per_burst"], len(sched["topics"]))
        picks = random.sample(sched["topics"], n)
        for t in picks:
            job = qmod.enqueue(
                topic=t, lang=sched["lang"], mode=sched["mode"],
                channel=sched["channel"],
                extra={"scheduled_by": sched["id"]},
            )
            queued.append(job["id"])

    elif kind == "daily_topic_pool":
        idx = sched.get("topic_index", 0) % len(sched["topics"])
        topic = sched["topics"][idx]
        job = qmod.enqueue(
            topic=topic, lang=sched["lang"], mode=sched["mode"],
            channel=sched["channel"],
            extra={"scheduled_by": sched["id"]},
        )
        queued.append(job["id"])
        sched["topic_index"] = (idx + 1) % len(sched["topics"])

    sched["last_fired_at"] = (now or datetime.now(timezone.utc)).isoformat()
    sched["fired_count"] = sched.get("fired_count", 0) + 1
    _save(all_schedules)
    return {"schedule_id": sched["id"], "queued": queued}


def tick(now: datetime | None = None) -> list[dict]:
    """Called by worker every minute. Fires due cron schedules. Returns what was fired."""
    now = now or datetime.now(timezone.utc)
    schedules = _load()
    fired = []
    for sched in schedules:
        if not sched.get("enabled"):
            continue
        if sched["kind"] != "cron":
            continue  # burst/daily are manual-fire only
        hours = sched.get("hours_utc", [])
        if not hours:
            continue

        # Check if any of this schedule's hours matches current UTC HH:MM
        now_key = now.strftime("%H:%M")
        if now_key not in hours:
            continue

        # Already fired within this minute? Skip.
        last = sched.get("last_fired_at")
        if last:
            try:
                last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                if (now - last_dt).total_seconds() < 60:
                    continue
            except Exception:
                pass

        res = _fire_schedule(sched, schedules, now=now)
        fired.append(res)

    return fired
