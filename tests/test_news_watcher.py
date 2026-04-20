"""Tests for news_watcher — feed registry, keyword matching, dedup, auto-queue."""

import sqlite3
import types
import sys


def test_add_and_list_feeds(tmp_path, monkeypatch):
    from pipeline import news_watcher as nw
    monkeypatch.setattr(nw, "DB_PATH", tmp_path / "news.sqlite")

    fid1 = nw.add_feed("https://hnrss.org/frontpage", name="HN",
                       keywords="ai,ml,llm")
    fid2 = nw.add_feed("https://example.com/rss", name="Example",
                       keywords="tesla", auto_queue=True)

    feeds = nw.list_feeds()
    assert len(feeds) == 2
    assert any(f["name"] == "HN" and f["keywords"] == "ai,ml,llm" for f in feeds)
    assert any(f["auto_queue"] == 1 and f["name"] == "Example" for f in feeds)


def test_duplicate_url_returns_existing_id(tmp_path, monkeypatch):
    from pipeline import news_watcher as nw
    monkeypatch.setattr(nw, "DB_PATH", tmp_path / "news.sqlite")

    id1 = nw.add_feed("https://x.com/rss", name="X")
    id2 = nw.add_feed("https://x.com/rss", name="X again")
    assert id1 == id2
    assert len(nw.list_feeds()) == 1


def test_remove_feed_cascades_entries(tmp_path, monkeypatch):
    from pipeline import news_watcher as nw
    monkeypatch.setattr(nw, "DB_PATH", tmp_path / "news.sqlite")

    fid = nw.add_feed("https://a.com/rss", name="A")
    # Manually seed a seen entry
    conn = sqlite3.connect(str(nw.DB_PATH))
    conn.execute(
        "INSERT INTO seen_entries (feed_id, entry_id, title, url, matched_at) "
        "VALUES (?, ?, ?, ?, datetime('now'))",
        (fid, "e1", "Title 1", "https://a.com/1"),
    )
    conn.commit()
    conn.close()

    assert nw.remove_feed(fid) is True
    # Feed gone, entries gone
    assert nw.list_feeds() == []


def test_keyword_match_filter():
    from pipeline.news_watcher import _match_keywords
    assert _match_keywords("NASA announces new mission", "nasa,spacex") is True
    assert _match_keywords("Tesla unveils robotaxi", "nasa,spacex") is False
    assert _match_keywords("Anything goes", "") is True
    assert _match_keywords("Anything goes", "   ") is True
    # Case-insensitive
    assert _match_keywords("APPLE released iPhone", "apple") is True


def test_scan_feed_with_stubbed_feedparser(tmp_path, monkeypatch):
    """Inject a fake feedparser so we can test dedup + matching without network."""
    from pipeline import news_watcher as nw
    monkeypatch.setattr(nw, "DB_PATH", tmp_path / "news.sqlite")

    fid = nw.add_feed("https://test.com/rss", name="TestFeed", keywords="tesla")

    fake_fp = types.ModuleType("feedparser")

    def fake_parse(url):
        feed = types.SimpleNamespace()
        feed.entries = [
            {"id": "e1", "title": "Tesla robotaxi launches today",
             "link": "https://t/1", "published": "2026-04-20"},
            {"id": "e2", "title": "Apple M5 chip announcement",
             "link": "https://t/2", "published": "2026-04-20"},
            {"id": "e3", "title": "Tesla Cybertruck delivery numbers",
             "link": "https://t/3", "published": "2026-04-20"},
        ]
        return feed
    fake_fp.parse = fake_parse
    monkeypatch.setitem(sys.modules, "feedparser", fake_fp)

    r = nw.scan_feed(fid)
    assert r["total_fetched"] == 3
    assert r["new_matches"] == 2  # both Tesla items

    # Second scan — should see 0 new (dedup)
    r2 = nw.scan_feed(fid)
    assert r2["new_matches"] == 0


def test_scan_disabled_feed_skipped(tmp_path, monkeypatch):
    from pipeline import news_watcher as nw
    monkeypatch.setattr(nw, "DB_PATH", tmp_path / "news.sqlite")

    fid = nw.add_feed("https://x.com/rss", name="X", enabled=False)
    r = nw.scan_feed(fid)
    assert r.get("skipped") == "disabled"


def test_inbox_returns_matched_only_by_default(tmp_path, monkeypatch):
    from pipeline import news_watcher as nw
    monkeypatch.setattr(nw, "DB_PATH", tmp_path / "news.sqlite")

    fid = nw.add_feed("https://a.com/rss", name="A")

    # Manually seed one matched + one unmatched
    conn = sqlite3.connect(str(nw.DB_PATH))
    conn.execute(
        "INSERT INTO seen_entries (feed_id, entry_id, title, matched_at, matched) "
        "VALUES (?, ?, ?, datetime('now'), 1)",
        (fid, "m1", "Matched title"),
    )
    conn.execute(
        "INSERT INTO seen_entries (feed_id, entry_id, title, matched_at, matched) "
        "VALUES (?, ?, ?, datetime('now'), 0)",
        (fid, "u1", "Unmatched title"),
    )
    conn.commit()
    conn.close()

    matched = nw.inbox(matched_only=True)
    assert len(matched) == 1
    assert matched[0]["title"] == "Matched title"

    all_ = nw.inbox(matched_only=False)
    assert len(all_) == 2


def test_update_feed_fields(tmp_path, monkeypatch):
    from pipeline import news_watcher as nw
    monkeypatch.setattr(nw, "DB_PATH", tmp_path / "news.sqlite")

    fid = nw.add_feed("https://a.com/rss", name="A", keywords="old")
    assert nw.update_feed(fid, keywords="new,kw", auto_queue=1) is True

    feeds = nw.list_feeds()
    assert feeds[0]["keywords"] == "new,kw"
    assert feeds[0]["auto_queue"] == 1


def test_notify_config_roundtrip(tmp_path, monkeypatch):
    from pipeline import news_watcher as nw, config as cfg
    monkeypatch.setattr(cfg, "SKILL_DIR", tmp_path)

    nw.save_notify_config({"telegram_bot_token": "abc", "telegram_chat_id": "123"})
    # Additive update
    nw.save_notify_config({"webhook_url": "https://hook.example"})

    cfg_loaded = nw._load_notify_config()
    assert cfg_loaded["telegram_bot_token"] == "abc"
    assert cfg_loaded["webhook_url"] == "https://hook.example"


def test_auto_queue_creates_job(tmp_path, monkeypatch):
    """When auto_queue=True and a match arrives, a queue job is created."""
    from pipeline import news_watcher as nw, queue as qmod
    monkeypatch.setattr(nw, "DB_PATH", tmp_path / "news.sqlite")
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path / "queue")

    fid = nw.add_feed("https://hot.com/rss", name="Hot",
                      keywords="nasa", auto_queue=True)

    fake_fp = types.ModuleType("feedparser")
    fake_fp.parse = lambda url: types.SimpleNamespace(entries=[
        {"id": "hot1", "title": "NASA Artemis 3 launches",
         "link": "https://h/1", "published": "2026-04-20"},
    ])
    monkeypatch.setitem(sys.modules, "feedparser", fake_fp)

    r = nw.scan_feed(fid)
    assert r["new_matches"] == 1
    assert r["queued"] == 1

    jobs = qmod.list_jobs()
    assert len(jobs) == 1
    assert "NASA" in jobs[0]["topic"]
