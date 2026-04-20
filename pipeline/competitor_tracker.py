"""Competitor channel tracking — what are rivals publishing + what's working.

Watch N competitor YouTube channels. Every scan:
  1. Pull their latest uploads via YouTube Data API (channels.list + playlistItems)
  2. Record title + views + likes + published_at to SQLite
  3. Compute per-channel trends: avg views, top performers
  4. Compare their topics against our topic_memory → flag topics we haven't covered
  5. Optional: surface "topic signals" to the UI — Claude summarizes what's
     resonating

Uses YouTube Data API key (not OAuth) — we only read public data. Configure
YOUTUBE_DATA_API_KEY in settings. One API key can track 50+ channels within
the free daily 10k-unit quota.

Storage: SKILL_DIR/competitors.sqlite
    competitor_channels(channel_id, name, added_at, notes)
    competitor_videos(video_id, channel_id, title, published_at, views, likes,
                       comments, duration, first_seen_at, last_checked_at)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from .config import SKILL_DIR
from .log import log


DB_PATH = SKILL_DIR / "competitors.sqlite"


def _ensure_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS competitor_channels (
                channel_id TEXT PRIMARY KEY,
                name TEXT,
                added_at TEXT NOT NULL,
                notes TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS competitor_videos (
                video_id TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL,
                title TEXT,
                published_at TEXT,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                duration_seconds INTEGER,
                first_seen_at TEXT NOT NULL,
                last_checked_at TEXT NOT NULL,
                thumbnail_url TEXT,
                FOREIGN KEY (channel_id) REFERENCES competitor_channels(channel_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cv_channel ON competitor_videos(channel_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cv_published ON competitor_videos(published_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cv_views ON competitor_videos(views DESC)")
        conn.commit()
    finally:
        conn.close()


# ────────────────────────────────────────────────────────────
# Channel registry
# ────────────────────────────────────────────────────────────
def add_channel(channel_id: str, name: str = "", notes: str = "") -> dict:
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute(
            "INSERT OR REPLACE INTO competitor_channels (channel_id, name, added_at, notes) "
            "VALUES (?, ?, ?, ?)",
            (channel_id, name or channel_id,
             datetime.now(timezone.utc).isoformat(), notes),
        )
        conn.commit()
    finally:
        conn.close()
    try:
        from . import audit
        audit.log("provider_changed", target=f"competitor:{channel_id}",
                  details={"name": name})
    except Exception:
        pass
    return {"channel_id": channel_id, "name": name}


def remove_channel(channel_id: str) -> bool:
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("DELETE FROM competitor_videos WHERE channel_id = ?", (channel_id,))
        cur = conn.execute("DELETE FROM competitor_channels WHERE channel_id = ?", (channel_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def list_channels() -> list[dict]:
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM competitor_channels ORDER BY added_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ────────────────────────────────────────────────────────────
# Fetching
# ────────────────────────────────────────────────────────────
def _build_client_from_api_key(api_key: str):
    """YouTube Data API client using just an API key (no OAuth)."""
    from googleapiclient.discovery import build
    return build("youtube", "v3", developerKey=api_key)


def scan_channel(
    channel_id: str,
    api_key: str,
    *,
    max_results: int = 10,
) -> dict:
    """Fetch recent uploads + stats for one channel. Persist to DB."""
    _ensure_db()
    try:
        yt = _build_client_from_api_key(api_key)

        # 1) Get uploads playlist ID
        ch_resp = yt.channels().list(
            part="snippet,contentDetails", id=channel_id,
        ).execute()
        items = ch_resp.get("items", [])
        if not items:
            return {"error": "channel_not_found", "channel_id": channel_id}
        ch = items[0]
        uploads_pl = ch["contentDetails"]["relatedPlaylists"]["uploads"]
        name = ch["snippet"]["title"]

        # Keep channel name up to date
        conn = sqlite3.connect(str(DB_PATH))
        try:
            conn.execute(
                "UPDATE competitor_channels SET name = ? WHERE channel_id = ?",
                (name, channel_id),
            )
            conn.commit()
        finally:
            conn.close()

        # 2) Get recent video IDs
        pl_resp = yt.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=uploads_pl,
            maxResults=max_results,
        ).execute()
        video_ids = [it["contentDetails"]["videoId"] for it in pl_resp.get("items", [])]

        # 3) Batch fetch stats
        v_resp = yt.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(video_ids),
        ).execute()

        new_count = 0
        updated_count = 0
        now = datetime.now(timezone.utc).isoformat()
        conn = sqlite3.connect(str(DB_PATH))
        try:
            for v in v_resp.get("items", []):
                sn = v["snippet"]
                st = v.get("statistics", {})
                dur_raw = v.get("contentDetails", {}).get("duration", "PT0S")
                dur_sec = _iso_duration_to_seconds(dur_raw)

                existing = conn.execute(
                    "SELECT 1 FROM competitor_videos WHERE video_id = ?",
                    (v["id"],)
                ).fetchone()

                if existing:
                    conn.execute(
                        "UPDATE competitor_videos SET views=?, likes=?, comments=?, "
                        "last_checked_at=? WHERE video_id=?",
                        (int(st.get("viewCount", 0)), int(st.get("likeCount", 0)),
                         int(st.get("commentCount", 0)), now, v["id"]),
                    )
                    updated_count += 1
                else:
                    conn.execute(
                        "INSERT INTO competitor_videos "
                        "(video_id, channel_id, title, published_at, views, likes, "
                        " comments, duration_seconds, first_seen_at, last_checked_at, thumbnail_url) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (v["id"], channel_id, sn.get("title", ""),
                         sn.get("publishedAt", ""),
                         int(st.get("viewCount", 0)), int(st.get("likeCount", 0)),
                         int(st.get("commentCount", 0)), dur_sec,
                         now, now,
                         sn.get("thumbnails", {}).get("medium", {}).get("url", "")),
                    )
                    new_count += 1
            conn.commit()
        finally:
            conn.close()

        return {"channel_id": channel_id, "name": name,
                "new": new_count, "updated": updated_count,
                "total_scanned": len(v_resp.get("items", []))}
    except Exception as e:
        log(f"[competitors] scan failed {channel_id}: {e}")
        return {"error": str(e), "channel_id": channel_id}


def scan_all(api_key: str) -> list[dict]:
    """Scan every registered channel. Returns per-channel result dicts."""
    return [scan_channel(ch["channel_id"], api_key) for ch in list_channels()]


def _iso_duration_to_seconds(s: str) -> int:
    """Convert ISO-8601 duration (PT1H23M45S) to seconds."""
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m:
        return 0
    h, mm, ss = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mm * 60 + ss


# ────────────────────────────────────────────────────────────
# Analysis
# ────────────────────────────────────────────────────────────
def top_performers(*, channel_id: str | None = None, days: int = 30,
                   limit: int = 10) -> list[dict]:
    """Highest-view videos in the last N days."""
    _ensure_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        if channel_id:
            rows = conn.execute(
                "SELECT * FROM competitor_videos WHERE channel_id=? AND published_at >= ? "
                "ORDER BY views DESC LIMIT ?",
                (channel_id, cutoff, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM competitor_videos WHERE published_at >= ? "
                "ORDER BY views DESC LIMIT ?",
                (cutoff, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def channel_stats(channel_id: str, days: int = 30) -> dict:
    """Per-channel aggregate stats."""
    _ensure_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        r = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(views),0), COALESCE(AVG(views),0), "
            "COALESCE(MAX(views),0) FROM competitor_videos "
            "WHERE channel_id=? AND published_at >= ?",
            (channel_id, cutoff),
        ).fetchone()
        count, total_views, avg_views, max_views = r
        return {
            "channel_id": channel_id,
            "video_count": int(count),
            "total_views": int(total_views),
            "avg_views": int(avg_views),
            "max_views": int(max_views),
            "days": days,
        }
    finally:
        conn.close()


def topic_gaps(
    *,
    days: int = 30,
    similarity_threshold: float = 0.4,
    limit: int = 10,
) -> list[dict]:
    """Competitor topics we HAVEN'T covered in our own topic_memory.

    Goes through competitors' top performers, compares each against our
    topic_memory, and returns the ones with no close match — these are
    opportunity topics.
    """
    try:
        from . import topic_memory
    except Exception:
        return []

    gaps = []
    for v in top_performers(days=days, limit=50):
        hits = topic_memory.find_similar(v["title"], threshold=similarity_threshold,
                                          days=days * 3, limit=1)
        if not hits:
            gaps.append({
                "competitor_title": v["title"],
                "views": v["views"],
                "channel_id": v["channel_id"],
                "video_id": v["video_id"],
                "published_at": v["published_at"],
            })
        if len(gaps) >= limit:
            break
    return gaps
