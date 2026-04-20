"""Tests for channel_stats module: caching + format helpers + error handling."""

import json
import time


def test_format_count_human_friendly():
    from pipeline.channel_stats import format_count
    assert format_count(0) == "0"
    assert format_count(999) == "999"
    assert format_count(1000) == "1K"
    assert format_count(1200) == "1.2K"
    assert format_count(15000) == "15K"
    assert format_count(1_500_000) == "1.5M"
    assert format_count(12_000_000) == "12M"
    assert format_count(2_500_000_000) == "2.5B"


def test_format_count_handles_bad_input():
    from pipeline.channel_stats import format_count
    assert format_count("abc") == "abc"
    assert format_count(None) == "None"


def test_cache_miss_returns_none(tmp_path, monkeypatch):
    from pipeline import channel_stats as cs
    monkeypatch.setattr(cs, "CACHE_DIR", tmp_path)
    assert cs._load_cache("/no/such/token") is None


def test_cache_hit_within_ttl(tmp_path, monkeypatch):
    from pipeline import channel_stats as cs
    monkeypatch.setattr(cs, "CACHE_DIR", tmp_path)

    data = {"channel": {"title": "Test"}, "recent": []}
    cs._save_cache("/tmp/token.json", data)

    loaded = cs._load_cache("/tmp/token.json")
    assert loaded is not None
    assert loaded["channel"]["title"] == "Test"


def test_cache_expires_after_ttl(tmp_path, monkeypatch):
    from pipeline import channel_stats as cs
    monkeypatch.setattr(cs, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(cs, "CACHE_TTL", 0)  # expire immediately

    cs._save_cache("/tmp/token.json", {"channel": {"title": "Old"}})
    time.sleep(0.01)
    assert cs._load_cache("/tmp/token.json") is None


def test_corrupt_cache_ignored(tmp_path, monkeypatch):
    from pipeline import channel_stats as cs
    monkeypatch.setattr(cs, "CACHE_DIR", tmp_path)

    # Write a valid cache then corrupt it
    cs._save_cache("/tmp/token.json", {"x": "y"})
    p = cs._cache_path("/tmp/token.json")
    p.write_text("not json{", encoding="utf-8")

    assert cs._load_cache("/tmp/token.json") is None


def test_fetch_stats_returns_error_on_api_failure(tmp_path, monkeypatch):
    """When YouTube API client fails, return {error: "..."} instead of raising."""
    from pipeline import channel_stats as cs
    monkeypatch.setattr(cs, "CACHE_DIR", tmp_path)

    def boom(token_path):
        raise RuntimeError("network down")
    monkeypatch.setattr(cs, "_build_youtube_client", boom)

    r = cs.fetch_stats("/nonexistent/token.json", force_refresh=True)
    assert r["channel"] is None
    assert r["recent"] == []
    assert "network down" in r["error"]


def test_cache_path_isolates_by_token(tmp_path, monkeypatch):
    """Two different tokens (= two channels) must have distinct cache files."""
    from pipeline import channel_stats as cs
    monkeypatch.setattr(cs, "CACHE_DIR", tmp_path)

    p1 = cs._cache_path("/home/u/.yt/channels/ayaz/token.json")
    p2 = cs._cache_path("/home/u/.yt/channels/ikinci/token.json")
    assert p1 != p2
