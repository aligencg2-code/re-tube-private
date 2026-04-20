"""Topic memory — prevent duplicate video topics.

Stores every produced topic in a lightweight SQLite table. Before enqueueing
a new job, check if a very similar topic was done recently and warn the user.

Similarity is computed with a tiny TF-like scoring over token-overlap that
works without sklearn / numpy dependencies. It's not state-of-the-art but
it's fast, deterministic, and catches the 95% case of "I already made this
video last week" — which is all the product actually needs.

API:
    remember(topic, job_id=None, youtube_url=None, channel=None)
    find_similar(topic, threshold=0.55, limit=5) -> list[dict]
    delete(topic_id)
    recent(days=30, limit=50) -> list[dict]
"""

from __future__ import annotations

import re
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Iterable

from .config import SKILL_DIR


DB_PATH = SKILL_DIR / "topic_memory.sqlite"

# Turkish + English stopwords to skip from token matching
_STOPWORDS = {
    # Turkish
    "ve", "ile", "bir", "bu", "şu", "o", "için", "ama", "ancak", "veya",
    "da", "de", "ta", "te", "ki", "mi", "mı", "mu", "mü", "gibi", "daha",
    "çok", "az", "en", "sonra", "önce", "olarak", "neden", "niçin",
    # English
    "a", "an", "the", "and", "or", "but", "for", "of", "in", "on", "at", "to",
    "with", "from", "by", "is", "are", "was", "were", "be", "been", "has", "have",
    "had", "will", "would", "could", "should", "may", "might", "that", "this",
    "these", "those", "it", "its", "into", "up", "out", "over", "after",
}


def _ensure_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                normalized TEXT NOT NULL,
                job_id TEXT,
                channel TEXT,
                youtube_url TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_topics_created ON topics(created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_topics_channel ON topics(channel)")
        conn.commit()
    finally:
        conn.close()


def _tokenize(text: str) -> set[str]:
    """Normalize + tokenize text. Lowercases, strips punctuation, drops stopwords."""
    if not text:
        return set()
    text = text.lower()
    # Split on non-word chars
    tokens = re.findall(r"[a-z0-9çğıöşü]+", text, flags=re.IGNORECASE)
    return {t for t in tokens if len(t) >= 3 and t not in _STOPWORDS}


def _similarity(a_tokens: set[str], b_tokens: set[str]) -> float:
    """Jaccard similarity over token sets. 0.0 = disjoint, 1.0 = identical."""
    if not a_tokens or not b_tokens:
        return 0.0
    inter = a_tokens & b_tokens
    union = a_tokens | b_tokens
    if not union:
        return 0.0
    return len(inter) / len(union)


def remember(
    topic: str,
    *,
    job_id: str | None = None,
    channel: str | None = None,
    youtube_url: str | None = None,
) -> int:
    """Record a topic. Returns new row id."""
    _ensure_db()
    normalized = " ".join(sorted(_tokenize(topic)))
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.execute(
            "INSERT INTO topics (topic, normalized, job_id, channel, youtube_url, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (topic, normalized, job_id, channel, youtube_url,
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def find_similar(
    topic: str,
    *,
    threshold: float = 0.55,
    limit: int = 5,
    days: int | None = 180,
    channel: str | None = None,
) -> list[dict]:
    """Return topics above similarity threshold, most-similar first.

    - threshold: minimum Jaccard similarity (0.0 – 1.0). 0.55 is a good
      default: catches paraphrases, ignores totally-unrelated topics.
    - days: only look at topics produced in the last N days (None = all time).
    - channel: restrict to a specific channel (None = all).
    """
    _ensure_db()
    query_tokens = _tokenize(topic)
    if not query_tokens:
        return []

    where = "1=1"
    params: list = []
    if days is not None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        where += " AND created_at >= ?"
        params.append(cutoff)
    if channel:
        where += " AND channel = ?"
        params.append(channel)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            f"SELECT * FROM topics WHERE {where} ORDER BY created_at DESC LIMIT 500",
            params,
        ).fetchall()
    finally:
        conn.close()

    scored = []
    for r in rows:
        rt_tokens = set((r["normalized"] or "").split())
        sim = _similarity(query_tokens, rt_tokens)
        if sim >= threshold:
            scored.append({
                "id": r["id"],
                "topic": r["topic"],
                "similarity": round(sim, 3),
                "created_at": r["created_at"],
                "job_id": r["job_id"],
                "channel": r["channel"],
                "youtube_url": r["youtube_url"],
            })
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:limit]


def recent(days: int = 30, limit: int = 50, channel: str | None = None) -> list[dict]:
    """Return recently-produced topics, newest first."""
    _ensure_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        params: list = [cutoff]
        where = "created_at >= ?"
        if channel:
            where += " AND channel = ?"
            params.append(channel)
        rows = conn.execute(
            f"SELECT * FROM topics WHERE {where} ORDER BY created_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete(topic_id: int) -> bool:
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def count() -> int:
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        (n,) = conn.execute("SELECT COUNT(*) FROM topics").fetchone()
        return n
    finally:
        conn.close()
