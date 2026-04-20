"""YouTube comment moderator.

Fetches recent comments on a channel's videos, classifies each with an LLM
as one of:
    - spam        → auto-hide (requires youtube.force-ssl scope, which the
                    OAuth setup already requests)
    - question    → flagged in the UI "inbox" for the creator to answer
    - thanks      → optional auto-heart
    - discussion  → left alone

Comments + classifications are stored in SKILL_DIR/comments.sqlite so the
panel can show a rolling inbox across all channels + act on them.

The LLM call is lazy (uses `pipeline.draft._call_script_ai`) so it inherits
the user's chosen script_ai provider — no new API key. On provider failure,
we degrade to heuristic keyword matching so the module still works offline.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Iterable, Optional

from .config import SKILL_DIR
from .log import log


DB_PATH = SKILL_DIR / "comments.sqlite"

CATEGORIES = ("spam", "question", "thanks", "discussion")

# Keyword fallbacks for when no LLM is reachable
_SPAM_PATTERNS = [
    r"https?://\S+",                           # any URL
    r"\b(check out|visit|click here|free|promo|subscribe back|sub4sub)\b",
    r"\b(kanalıma|kanalima|gel abone)\b",
    r"(💰|💵|🤑|🎁){2,}",
]
_QUESTION_PATTERNS = [r"\?", r"\bhow\b", r"\bwhy\b", r"\bwhat\b", r"\bne zaman\b",
                      r"\bnasıl\b", r"\bneden\b", r"\bkim\b"]
_THANKS_PATTERNS  = [r"\b(thanks|thank you|teşekkür\w*|sağ ol|tesekkur\w*|sagol\w*)\b",
                     r"(❤|🙏|👍){1,}"]


def _ensure_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id TEXT PRIMARY KEY,
                video_id TEXT NOT NULL,
                channel TEXT,
                author TEXT,
                text TEXT NOT NULL,
                published_at TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                category TEXT,
                confidence REAL,
                action TEXT DEFAULT 'none',
                acted_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cm_video ON comments(video_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cm_cat   ON comments(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cm_pub   ON comments(published_at DESC)")
        conn.commit()
    finally:
        conn.close()


def classify_heuristic(text: str) -> tuple[str, float]:
    """Regex-only fallback classifier. Returns (category, confidence 0.0–1.0)."""
    t = (text or "").lower()
    for pat in _SPAM_PATTERNS:
        if re.search(pat, t, flags=re.IGNORECASE):
            return ("spam", 0.6)
    for pat in _QUESTION_PATTERNS:
        if re.search(pat, t, flags=re.IGNORECASE):
            return ("question", 0.55)
    for pat in _THANKS_PATTERNS:
        if re.search(pat, t, flags=re.IGNORECASE):
            return ("thanks", 0.65)
    return ("discussion", 0.4)


def classify_llm(text: str) -> tuple[str, float]:
    """Call the configured script_ai provider to classify a comment.

    Falls back to heuristic on any error. Expected output (JSON):
        {"category": "spam|question|thanks|discussion", "confidence": 0.xx}
    """
    try:
        from .draft import _call_script_ai
        prompt = (
            "Classify this YouTube comment into exactly ONE category. "
            "Reply with JSON only: {\"category\": \"...\", \"confidence\": 0.0-1.0}\n\n"
            "Categories:\n"
            "- spam: self-promo, URLs, engagement farming, scams\n"
            "- question: asking something, needs creator response\n"
            "- thanks: appreciation, emoji hearts, no question\n"
            "- discussion: opinion, reply, general commentary\n\n"
            f"Comment: {text[:500]}"
        )
        raw = _call_script_ai(prompt)
        # Extract JSON
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json\n"):
                raw = raw[5:]
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(raw[start:end + 1])
            cat = data.get("category", "").strip().lower()
            conf = float(data.get("confidence", 0.5))
            if cat in CATEGORIES:
                return (cat, max(0.0, min(1.0, conf)))
    except Exception:
        pass
    return classify_heuristic(text)


def _build_youtube_client(token_path: str):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(token_path)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def fetch_recent_comments(
    *, token_path: str, video_ids: list[str] | None = None,
    max_per_video: int = 20,
) -> list[dict]:
    """Fetch newest comments across the given videos (or auto-discovers from channel).

    Returns list of raw comment dicts — classification happens in process_new.
    """
    yt = _build_youtube_client(token_path)

    # Auto-discover recent video IDs if not provided
    if not video_ids:
        from . import channel_stats
        snap = channel_stats.fetch_stats(token_path, force_refresh=False)
        video_ids = [v["id"] for v in snap.get("recent", [])][:10]

    out: list[dict] = []
    for vid in video_ids[:20]:  # hard-cap to avoid quota burn
        try:
            resp = yt.commentThreads().list(
                part="snippet",
                videoId=vid,
                maxResults=max_per_video,
                order="time",
                textFormat="plainText",
            ).execute()
            for it in resp.get("items", []):
                s = it["snippet"]["topLevelComment"]["snippet"]
                out.append({
                    "id": it["id"],
                    "video_id": vid,
                    "author": s.get("authorDisplayName", ""),
                    "text": s.get("textDisplay", ""),
                    "published_at": s.get("publishedAt", ""),
                })
        except Exception as e:
            log(f"[comments] fetch error on {vid}: {e}")
            continue
    return out


def process_new(
    *, token_path: str, channel: str | None = None,
    video_ids: list[str] | None = None,
    use_llm: bool = True,
) -> dict:
    """Pull fresh comments, classify them, store in DB. Returns stats."""
    _ensure_db()
    raw = fetch_recent_comments(token_path=token_path, video_ids=video_ids)
    if not raw:
        return {"new": 0, "skipped": 0}

    now = datetime.now(timezone.utc).isoformat()
    classifier = classify_llm if use_llm else classify_heuristic

    new_count = 0
    skipped = 0
    conn = sqlite3.connect(str(DB_PATH))
    try:
        for c in raw:
            # Skip if we already classified this comment
            existing = conn.execute(
                "SELECT 1 FROM comments WHERE id = ?", (c["id"],)
            ).fetchone()
            if existing:
                skipped += 1
                continue

            cat, conf = classifier(c["text"])
            conn.execute(
                """INSERT INTO comments
                   (id, video_id, channel, author, text, published_at,
                    fetched_at, category, confidence)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (c["id"], c["video_id"], channel, c["author"], c["text"],
                 c["published_at"], now, cat, conf),
            )
            new_count += 1
        conn.commit()
    finally:
        conn.close()

    return {"new": new_count, "skipped": skipped, "total_fetched": len(raw)}


def inbox(
    *, category: str | None = None, channel: str | None = None,
    limit: int = 50, days: int = 14,
) -> list[dict]:
    """Return classified comments, newest first."""
    _ensure_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    where = "fetched_at >= ?"
    params: list = [cutoff]
    if category:
        where += " AND category = ?"
        params.append(category)
    if channel:
        where += " AND channel = ?"
        params.append(channel)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            f"SELECT * FROM comments WHERE {where} ORDER BY published_at DESC LIMIT ?",
            params + [limit],
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def hide_comment(comment_id: str, token_path: str) -> bool:
    """Hide a comment on YouTube (status=heldForReview).

    Requires the `youtube.force-ssl` scope (already in the OAuth flow).
    Marks the comment `action='hidden'` locally on success.
    """
    _ensure_db()
    try:
        yt = _build_youtube_client(token_path)
        yt.comments().setModerationStatus(
            id=comment_id,
            moderationStatus="heldForReview",
            banAuthor=False,
        ).execute()
        _mark_action(comment_id, "hidden")
        try:
            from . import audit as _audit
            _audit.log("comment_hidden", target=comment_id)
        except Exception:
            pass
        return True
    except Exception as e:
        log(f"[comments] hide failed for {comment_id}: {e}")
        return False


def mark_handled(comment_id: str) -> None:
    """User-initiated: mark as handled so it leaves the inbox."""
    _mark_action(comment_id, "handled")
    try:
        from . import audit as _audit
        _audit.log("comment_handled", target=comment_id)
    except Exception:
        pass


def counts(days: int = 14, channel: str | None = None) -> dict:
    """Return {category: count} for the recent window."""
    _ensure_db()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    where = "fetched_at >= ?"
    params: list = [cutoff]
    if channel:
        where += " AND channel = ?"
        params.append(channel)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        rows = conn.execute(
            f"SELECT category, COUNT(*) FROM comments WHERE {where} GROUP BY category",
            params,
        ).fetchall()
        out = {c: 0 for c in CATEGORIES}
        for cat, n in rows:
            out[cat] = n
        return out
    finally:
        conn.close()


def _mark_action(comment_id: str, action: str) -> None:
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute(
            "UPDATE comments SET action=?, acted_at=? WHERE id=?",
            (action, datetime.now(timezone.utc).isoformat(), comment_id),
        )
        conn.commit()
    finally:
        conn.close()
