"""Thumbnail A/B testing — generate variants, rotate after interval, pick winner.

Flow:
    1. At produce-time, generate 2-3 thumbnail variants via Gemini (slight prompt
       tweaks to force visual diversity).
    2. Upload variant #1 with the video (normal flow).
    3. Schedule a watcher task that every N hours:
         - Checks video.statistics for views + likes
         - Rotates to the next variant (uploads via thumbnails.set)
         - After all variants tested, picks the one with highest
           (views_gained / hours_tested) ratio and locks it in.

Variant set is stored in SKILL_DIR/thumbnail_tests.sqlite. A Streamlit
"A/B Tests" panel in Settings shows progress and lets the user kill a test.

The watcher can be invoked by cron, a loop thread, or the queue worker's
idle cycles.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from .config import SKILL_DIR


DB_PATH = SKILL_DIR / "thumbnail_tests.sqlite"

DEFAULT_ROTATION_HOURS = 24      # each variant gets 24h of exposure
DEFAULT_VARIANT_COUNT = 3


def _ensure_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ab_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL UNIQUE,
                channel TEXT,
                token_path TEXT,
                variants_json TEXT NOT NULL,
                current_variant INTEGER NOT NULL DEFAULT 0,
                rotation_hours INTEGER NOT NULL DEFAULT 24,
                status TEXT NOT NULL DEFAULT 'running',
                started_at TEXT NOT NULL,
                last_rotated_at TEXT NOT NULL,
                results_json TEXT DEFAULT '[]',
                winner_variant INTEGER,
                finished_at TEXT
            )
        """)
        conn.commit()
    finally:
        conn.close()


def create_test(
    *,
    video_id: str,
    variants: list[dict],    # [{"path": "/abs/path.png", "prompt": "..."}]
    token_path: str,
    channel: str | None = None,
    rotation_hours: int = DEFAULT_ROTATION_HOURS,
) -> int:
    """Register a new A/B test. Returns row id."""
    _ensure_db()
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.execute(
            """INSERT OR REPLACE INTO ab_tests
               (video_id, channel, token_path, variants_json, current_variant,
                rotation_hours, status, started_at, last_rotated_at, results_json)
               VALUES (?, ?, ?, ?, 0, ?, 'running', ?, ?, '[]')""",
            (video_id, channel, token_path, json.dumps(variants),
             rotation_hours, now, now),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def list_tests(status: str | None = None) -> list[dict]:
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM ab_tests WHERE status = ? ORDER BY started_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM ab_tests ORDER BY started_at DESC",
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_test(video_id: str) -> dict | None:
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        r = conn.execute(
            "SELECT * FROM ab_tests WHERE video_id = ?", (video_id,),
        ).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def kill_test(video_id: str) -> bool:
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.execute(
            "UPDATE ab_tests SET status='cancelled', finished_at=? WHERE video_id=? AND status='running'",
            (datetime.now(timezone.utc).isoformat(), video_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def _record_result(conn, test_id: int, variant_idx: int, views: int, likes: int, hours: float) -> None:
    """Append one measurement to the test's results_json."""
    r = conn.execute("SELECT results_json FROM ab_tests WHERE id=?", (test_id,)).fetchone()
    results = json.loads(r[0] or "[]")
    results.append({
        "variant": variant_idx,
        "views": views,
        "likes": likes,
        "hours_tested": round(hours, 2),
        "views_per_hour": round(views / hours, 2) if hours > 0 else 0.0,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    conn.execute("UPDATE ab_tests SET results_json=? WHERE id=?",
                 (json.dumps(results), test_id))


def check_and_rotate(
    video_id: str,
    *,
    views_fetcher=None,    # callable(video_id, token_path) -> (views, likes)
    uploader=None,         # callable(video_id, thumbnail_path, token_path) -> None
    now: datetime | None = None,
) -> dict:
    """Check if rotation is due for one test and rotate if so.

    `views_fetcher` and `uploader` are dependency-injected so this function
    is testable without hitting YouTube. In production they come from
    channel_stats + upload.py respectively.

    Returns: {"action": "none"|"rotated"|"finished", "details": ...}
    """
    test = get_test(video_id)
    if not test or test["status"] != "running":
        return {"action": "none", "reason": "not running"}

    now = now or datetime.now(timezone.utc)
    last = datetime.fromisoformat(test["last_rotated_at"].replace("Z", "+00:00"))
    hours_elapsed = (now - last).total_seconds() / 3600

    if hours_elapsed < test["rotation_hours"]:
        return {"action": "none", "hours_remaining": round(test["rotation_hours"] - hours_elapsed, 1)}

    variants = json.loads(test["variants_json"])
    current = test["current_variant"]

    # 1) Record current variant's performance
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        views, likes = (0, 0)
        if views_fetcher:
            try:
                views, likes = views_fetcher(video_id, test["token_path"])
            except Exception:
                pass

        _record_result(conn, test["id"], current, views, likes, hours_elapsed)
        conn.commit()

        # 2) Next variant? Or finalize?
        next_idx = current + 1
        if next_idx >= len(variants):
            # All variants tested — pick winner
            r = conn.execute("SELECT results_json FROM ab_tests WHERE id=?",
                             (test["id"],)).fetchone()
            results = json.loads(r[0])
            # Compare variants by views_per_hour of their final measurement
            by_variant: dict[int, float] = {}
            for rec in results:
                by_variant[rec["variant"]] = max(
                    by_variant.get(rec["variant"], 0.0), rec["views_per_hour"]
                )
            winner = max(by_variant, key=by_variant.get) if by_variant else 0
            winner_path = variants[winner]["path"]

            # Upload winner as permanent
            if uploader:
                try:
                    uploader(video_id, winner_path, test["token_path"])
                except Exception:
                    pass

            conn.execute(
                "UPDATE ab_tests SET status='finished', winner_variant=?, finished_at=? WHERE id=?",
                (winner, now.isoformat(), test["id"]),
            )
            conn.commit()
            return {"action": "finished", "winner": winner, "results": results}

        # Otherwise rotate to next variant
        next_path = variants[next_idx]["path"]
        if uploader:
            try:
                uploader(video_id, next_path, test["token_path"])
            except Exception as e:
                return {"action": "error", "error": str(e)}

        conn.execute(
            "UPDATE ab_tests SET current_variant=?, last_rotated_at=? WHERE id=?",
            (next_idx, now.isoformat(), test["id"]),
        )
        conn.commit()
        return {"action": "rotated", "from": current, "to": next_idx}
    finally:
        conn.close()


def scan_and_rotate_all(views_fetcher=None, uploader=None, now: datetime | None = None) -> list[dict]:
    """Process every running test. Call from a cron / background thread."""
    out = []
    for t in list_tests(status="running"):
        res = check_and_rotate(
            t["video_id"],
            views_fetcher=views_fetcher, uploader=uploader, now=now,
        )
        out.append({"video_id": t["video_id"], **res})
    return out
