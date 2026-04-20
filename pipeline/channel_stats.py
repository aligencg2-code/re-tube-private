"""Live YouTube channel stats using YouTube Data API v3 (read-only).

Fetches the authenticated user's channel (`mine=true`) + recent uploads.
Works with the existing `youtube.upload` OAuth scope — no extra permissions
needed beyond what the upload flow already has.

Public metrics only (subscribers, views, video count, per-video views/likes).
For watch-time/CTR/impressions we'd need the YouTube Analytics API with
`yt-analytics.readonly` scope — not implemented here to avoid re-OAuth.

Results are cached to disk for 10 minutes so repeated UI refreshes don't
burn quota.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import SKILL_DIR


CACHE_DIR = SKILL_DIR / "stats_cache"
CACHE_TTL = 600  # 10 minutes


def _cache_path(token_path: str) -> Path:
    """One cache file per OAuth token (= per channel)."""
    # Safe filename from token path
    safe = "".join(c if c.isalnum() else "_" for c in token_path)[-80:]
    return CACHE_DIR / f"{safe}.json"


def _load_cache(token_path: str) -> dict | None:
    p = _cache_path(token_path)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if time.time() - data.get("_cached_at", 0) < CACHE_TTL:
            return data
    except Exception:
        pass
    return None


def _save_cache(token_path: str, data: dict) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        data["_cached_at"] = time.time()
        _cache_path(token_path).write_text(
            json.dumps(data, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass


def _build_youtube_client(token_path: str):
    """Build authenticated YouTube API client from OAuth token file."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(token_path)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def fetch_stats(token_path: str, force_refresh: bool = False) -> dict:
    """Return channel snapshot. Format:
    {
        "channel": {"title": "...", "thumbnail": "url",
                    "subscribers": int, "views": int, "videos": int},
        "recent": [
            {"id": "...", "title": "...", "published_at": "...",
             "thumbnail": "url", "views": int, "likes": int, "comments": int},
            ...  (up to 10)
        ],
        "error": None | "message",
    }
    """
    if not force_refresh:
        cached = _load_cache(token_path)
        if cached:
            return cached

    result: dict[str, Any] = {"channel": None, "recent": [], "error": None}

    try:
        yt = _build_youtube_client(token_path)

        # 1) Channel info
        ch_resp = yt.channels().list(
            part="snippet,statistics,contentDetails",
            mine=True,
        ).execute()
        items = ch_resp.get("items", [])
        if not items:
            result["error"] = "No channel found for this OAuth token"
            return result
        ch = items[0]
        stats = ch.get("statistics", {})
        snip = ch.get("snippet", {})
        result["channel"] = {
            "id": ch["id"],
            "title": snip.get("title", ""),
            "thumbnail": (snip.get("thumbnails", {}).get("default", {}).get("url") or ""),
            "subscribers": int(stats.get("subscriberCount", 0)),
            "views": int(stats.get("viewCount", 0)),
            "videos": int(stats.get("videoCount", 0)),
            "hidden_subs": stats.get("hiddenSubscriberCount", False),
        }

        uploads_pl = ch.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")

        # 2) Recent uploads via uploads playlist
        if uploads_pl:
            pl_resp = yt.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_pl,
                maxResults=10,
            ).execute()
            video_ids = [it["contentDetails"]["videoId"] for it in pl_resp.get("items", [])]

            if video_ids:
                # 3) Per-video stats (batched)
                v_resp = yt.videos().list(
                    part="snippet,statistics",
                    id=",".join(video_ids),
                    maxResults=10,
                ).execute()
                for v in v_resp.get("items", []):
                    s = v.get("statistics", {})
                    sn = v.get("snippet", {})
                    result["recent"].append({
                        "id": v["id"],
                        "title": sn.get("title", ""),
                        "published_at": sn.get("publishedAt", ""),
                        "thumbnail": (sn.get("thumbnails", {}).get("medium", {}).get("url")
                                      or sn.get("thumbnails", {}).get("default", {}).get("url")
                                      or ""),
                        "views": int(s.get("viewCount", 0)),
                        "likes": int(s.get("likeCount", 0)),
                        "comments": int(s.get("commentCount", 0)),
                        "url": f"https://youtu.be/{v['id']}",
                    })

        _save_cache(token_path, result)
        return result

    except Exception as e:
        result["error"] = str(e)
        return result


def format_count(n: int) -> str:
    """Human-friendly: 1234 → 1.2K, 1200000 → 1.2M."""
    try:
        n = int(n)
    except Exception:
        return str(n)
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1000:.1f}K".replace(".0K", "K")
    if n < 1_000_000_000:
        return f"{n / 1_000_000:.1f}M".replace(".0M", "M")
    return f"{n / 1_000_000_000:.1f}B".replace(".0B", "B")
