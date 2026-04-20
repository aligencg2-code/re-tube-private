"""News watcher — monitor RSS feeds + optional X/Twitter, raise signals.

Customer configures:
    - one or more RSS feed URLs (Hacker News, tech blogs, local news)
    - keyword filters (only match if title contains ___)
    - notification channels: Telegram bot, webhook URL, in-panel inbox

Every scan cycle (triggered by the worker idle loop or cron):
    1. For each configured feed, fetch latest entries
    2. Apply keyword filter
    3. Dedupe against seen entries (SQLite)
    4. For each new match: optionally create a draft job automatically

Storage: SKILL_DIR/news_watcher.sqlite
    feeds(id, url, keywords, enabled, auto_queue, last_checked_at)
    seen_entries(id, feed_id, entry_id, title, url, published_at, matched_at,
                 queued_job_id)
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

from .config import SKILL_DIR
from .log import log


DB_PATH = SKILL_DIR / "news_watcher.sqlite"


def _ensure_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                name TEXT,
                keywords TEXT,
                enabled INTEGER DEFAULT 1,
                auto_queue INTEGER DEFAULT 0,
                channel_id TEXT,
                last_checked_at TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feed_id INTEGER NOT NULL,
                entry_id TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT,
                published_at TEXT,
                matched_at TEXT NOT NULL,
                matched BOOLEAN DEFAULT 0,
                queued_job_id TEXT,
                UNIQUE (feed_id, entry_id),
                FOREIGN KEY (feed_id) REFERENCES feeds(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_se_feed ON seen_entries(feed_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_se_matched ON seen_entries(matched, matched_at DESC)")
        conn.commit()
    finally:
        conn.close()


# ────────────────────────────────────────────────────────────
# Feed registry
# ────────────────────────────────────────────────────────────
def add_feed(
    url: str,
    *,
    name: str = "",
    keywords: str = "",
    enabled: bool = True,
    auto_queue: bool = False,
    channel_id: str | None = None,
) -> int:
    """Register an RSS feed. Returns new feed id."""
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.execute(
            "INSERT OR IGNORE INTO feeds "
            "(url, name, keywords, enabled, auto_queue, channel_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (url, name or url, keywords,
             1 if enabled else 0, 1 if auto_queue else 0,
             channel_id, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        if cur.lastrowid:
            return cur.lastrowid
        # Was a duplicate URL — find existing id
        r = conn.execute("SELECT id FROM feeds WHERE url = ?", (url,)).fetchone()
        return r[0] if r else 0
    finally:
        conn.close()


def remove_feed(feed_id: int) -> bool:
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("DELETE FROM seen_entries WHERE feed_id = ?", (feed_id,))
        cur = conn.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def list_feeds() -> list[dict]:
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM feeds ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_feed(feed_id: int, **fields) -> bool:
    if not fields:
        return False
    _ensure_db()
    cols = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [feed_id]
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.execute(f"UPDATE feeds SET {cols} WHERE id = ?", params)
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


# ────────────────────────────────────────────────────────────
# Scanning
# ────────────────────────────────────────────────────────────
def _match_keywords(title: str, keywords_csv: str) -> bool:
    """Return True if title matches any of the comma-separated keywords.

    Empty keywords → match everything.
    """
    if not keywords_csv or not keywords_csv.strip():
        return True
    keys = [k.strip().lower() for k in keywords_csv.split(",") if k.strip()]
    tl = title.lower()
    return any(k in tl for k in keys)


def scan_feed(feed_id: int) -> dict:
    """Fetch one feed, filter by keywords, store new matches. Returns summary."""
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        feed = conn.execute("SELECT * FROM feeds WHERE id = ?", (feed_id,)).fetchone()
    finally:
        conn.close()
    if not feed:
        return {"error": "feed_not_found"}
    if not feed["enabled"]:
        return {"skipped": "disabled", "feed_id": feed_id}

    try:
        import feedparser
        parsed = feedparser.parse(feed["url"])
    except Exception as e:
        log(f"[news_watcher] parse failed {feed['url']}: {e}")
        return {"error": f"parse_failed: {e}", "feed_id": feed_id}

    new_matches = []
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        for entry in parsed.entries[:25]:
            entry_id = entry.get("id") or entry.get("link") or entry.get("title")
            if not entry_id:
                continue
            title = entry.get("title", "")
            link = entry.get("link", "")
            pub = entry.get("published", "") or entry.get("updated", "")
            matched = _match_keywords(title, feed["keywords"] or "")

            try:
                conn.execute(
                    "INSERT INTO seen_entries "
                    "(feed_id, entry_id, title, url, published_at, matched_at, matched) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (feed_id, entry_id, title, link, pub, now_iso,
                     1 if matched else 0),
                )
                conn.commit()
                if matched:
                    new_matches.append({
                        "title": title, "url": link,
                        "published_at": pub, "entry_id": entry_id,
                    })
            except sqlite3.IntegrityError:
                # Already seen — skip silently
                pass

        # Update last_checked_at
        conn.execute("UPDATE feeds SET last_checked_at = ? WHERE id = ?",
                     (now_iso, feed_id))
        conn.commit()
    finally:
        conn.close()

    # Auto-queue + notify
    queued_count = 0
    if feed["auto_queue"] and new_matches:
        try:
            from . import queue as qmod
            for m in new_matches:
                job = qmod.enqueue(
                    topic=m["title"],
                    lang="tr",
                    mode="full",
                    channel=feed["channel_id"],
                )
                # Link back
                conn = sqlite3.connect(str(DB_PATH))
                try:
                    conn.execute(
                        "UPDATE seen_entries SET queued_job_id = ? "
                        "WHERE feed_id = ? AND entry_id = ?",
                        (job["id"], feed_id, m["entry_id"]),
                    )
                    conn.commit()
                finally:
                    conn.close()
                queued_count += 1
        except Exception as e:
            log(f"[news_watcher] auto-queue failed: {e}")

    if new_matches:
        _notify(f"📰 {len(new_matches)} yeni haber: {feed['name'] or feed['url']}",
                "\n".join(f"• {m['title'][:100]}" for m in new_matches[:5]))

    return {
        "feed_id": feed_id,
        "total_fetched": len(parsed.entries),
        "new_matches": len(new_matches),
        "queued": queued_count,
    }


def scan_all() -> list[dict]:
    return [scan_feed(f["id"]) for f in list_feeds() if f["enabled"]]


def inbox(*, matched_only: bool = True, limit: int = 50) -> list[dict]:
    """Return recently-seen entries, newest first."""
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        if matched_only:
            rows = conn.execute(
                "SELECT se.*, f.name AS feed_name FROM seen_entries se "
                "JOIN feeds f ON se.feed_id = f.id "
                "WHERE se.matched = 1 ORDER BY se.matched_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT se.*, f.name AS feed_name FROM seen_entries se "
                "JOIN feeds f ON se.feed_id = f.id "
                "ORDER BY se.matched_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ────────────────────────────────────────────────────────────
# Notifications
# ────────────────────────────────────────────────────────────
def _load_notify_config() -> dict:
    """Load notification settings from SKILL_DIR/notify_config.json."""
    p = SKILL_DIR / "notify_config.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_notify_config(cfg: dict) -> None:
    p = SKILL_DIR / "notify_config.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    current = _load_notify_config()
    current.update(cfg)
    p.write_text(json.dumps(current, indent=2), encoding="utf-8")


def _notify(title: str, body: str) -> None:
    """Send to Telegram + webhook if configured. Best-effort."""
    cfg = _load_notify_config()
    # Telegram
    tg_bot = cfg.get("telegram_bot_token")
    tg_chat = cfg.get("telegram_chat_id")
    if tg_bot and tg_chat:
        try:
            import requests
            requests.post(
                f"https://api.telegram.org/bot{tg_bot}/sendMessage",
                json={"chat_id": tg_chat,
                      "text": f"*{title}*\n{body}",
                      "parse_mode": "Markdown"},
                timeout=5,
            )
        except Exception as e:
            log(f"[news_watcher] telegram send failed: {e}")
    # Generic webhook
    webhook = cfg.get("webhook_url")
    if webhook:
        try:
            from . import api_server
            api_server.send_webhook(webhook, {"event": "news.matched",
                                              "title": title, "body": body})
        except Exception:
            pass


def send_telegram_test(bot_token: str, chat_id: str) -> dict:
    """Verify a Telegram configuration by sending a test message."""
    try:
        import requests
        r = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": "RE-Tube haber watcher test ✅"},
            timeout=5,
        )
        return {"ok": r.ok, "status_code": r.status_code,
                "response": r.json() if r.ok else r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}
