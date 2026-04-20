"""Tests for competitor_tracker — registry + stats + topic gap analysis."""

from datetime import datetime, timezone


def test_add_and_list_channels(tmp_path, monkeypatch):
    from pipeline import competitor_tracker as ct
    monkeypatch.setattr(ct, "DB_PATH", tmp_path / "competitors.sqlite")

    ct.add_channel("UC_abc123", name="TechRival", notes="Main competitor")
    ct.add_channel("UC_def456", name="AnotherRival")

    channels = ct.list_channels()
    assert len(channels) == 2
    names = [c["name"] for c in channels]
    assert "TechRival" in names
    assert "AnotherRival" in names


def test_add_channel_upsert(tmp_path, monkeypatch):
    from pipeline import competitor_tracker as ct
    monkeypatch.setattr(ct, "DB_PATH", tmp_path / "competitors.sqlite")

    ct.add_channel("UC_abc", name="OldName")
    ct.add_channel("UC_abc", name="NewName")

    channels = ct.list_channels()
    assert len(channels) == 1
    assert channels[0]["name"] == "NewName"


def test_remove_channel_cascades_videos(tmp_path, monkeypatch):
    from pipeline import competitor_tracker as ct
    import sqlite3
    monkeypatch.setattr(ct, "DB_PATH", tmp_path / "competitors.sqlite")

    ct.add_channel("UC_abc", name="Rival")
    # Manually seed some videos
    conn = sqlite3.connect(str(ct.DB_PATH))
    try:
        conn.execute(
            "INSERT INTO competitor_videos "
            "(video_id, channel_id, title, published_at, views, likes, comments, "
            " duration_seconds, first_seen_at, last_checked_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("v1", "UC_abc", "Video 1", datetime.now(timezone.utc).isoformat(),
             100, 10, 2, 60, datetime.now(timezone.utc).isoformat(),
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()

    assert ct.remove_channel("UC_abc") is True
    # Channel + its videos gone
    assert ct.list_channels() == []


def test_iso_duration_parser():
    from pipeline.competitor_tracker import _iso_duration_to_seconds
    assert _iso_duration_to_seconds("PT0S") == 0
    assert _iso_duration_to_seconds("PT45S") == 45
    assert _iso_duration_to_seconds("PT3M") == 180
    assert _iso_duration_to_seconds("PT1H23M45S") == 3600 + 23 * 60 + 45
    assert _iso_duration_to_seconds("") == 0
    assert _iso_duration_to_seconds("bad") == 0


def test_channel_stats_computes_aggregate(tmp_path, monkeypatch):
    from pipeline import competitor_tracker as ct
    import sqlite3
    monkeypatch.setattr(ct, "DB_PATH", tmp_path / "competitors.sqlite")
    ct.add_channel("UC_abc", name="Rival")

    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(ct.DB_PATH))
    try:
        for i, views in enumerate([1000, 5000, 25000, 500]):
            conn.execute(
                "INSERT INTO competitor_videos "
                "(video_id, channel_id, title, published_at, views, likes, comments, "
                " duration_seconds, first_seen_at, last_checked_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"v{i}", "UC_abc", f"Video {i}", now, views, views // 50,
                 views // 200, 60, now, now),
            )
        conn.commit()
    finally:
        conn.close()

    s = ct.channel_stats("UC_abc", days=30)
    assert s["video_count"] == 4
    assert s["total_views"] == 1000 + 5000 + 25000 + 500
    assert s["max_views"] == 25000
    assert s["avg_views"] == (1000 + 5000 + 25000 + 500) // 4


def test_top_performers_orders_by_views(tmp_path, monkeypatch):
    from pipeline import competitor_tracker as ct
    import sqlite3
    monkeypatch.setattr(ct, "DB_PATH", tmp_path / "competitors.sqlite")
    ct.add_channel("UC_abc", name="Rival")

    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(ct.DB_PATH))
    try:
        for i, views in enumerate([100, 50000, 10]):
            conn.execute(
                "INSERT INTO competitor_videos "
                "(video_id, channel_id, title, published_at, views, likes, comments, "
                " duration_seconds, first_seen_at, last_checked_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"v{i}", "UC_abc", f"Video {i}", now, views, 0, 0, 60, now, now),
            )
        conn.commit()
    finally:
        conn.close()

    top = ct.top_performers(days=30, limit=3)
    assert [t["views"] for t in top] == [50000, 100, 10]


def test_topic_gaps_filters_our_covered_topics(tmp_path, monkeypatch):
    """Topics we already produced shouldn't appear as gaps."""
    from pipeline import competitor_tracker as ct, topic_memory
    import sqlite3
    monkeypatch.setattr(ct, "DB_PATH", tmp_path / "competitors.sqlite")
    monkeypatch.setattr(topic_memory, "DB_PATH", tmp_path / "topic_memory.sqlite")

    # We've already covered "NASA Artemis Moon mission launches"
    topic_memory.remember("NASA Artemis Moon mission launches")

    # Two competitor videos: one matches our memory, one is fresh
    ct.add_channel("UC_abc", name="Rival")
    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(ct.DB_PATH))
    try:
        conn.execute(
            "INSERT INTO competitor_videos "
            "(video_id, channel_id, title, published_at, views, likes, comments, "
            " duration_seconds, first_seen_at, last_checked_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("v1", "UC_abc", "NASA Artemis Moon mission launches today",
             now, 50000, 0, 0, 60, now, now),
        )
        conn.execute(
            "INSERT INTO competitor_videos "
            "(video_id, channel_id, title, published_at, views, likes, comments, "
            " duration_seconds, first_seen_at, last_checked_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("v2", "UC_abc", "Tesla unveils surprising new battery chemistry",
             now, 100000, 0, 0, 60, now, now),
        )
        conn.commit()
    finally:
        conn.close()

    gaps = ct.topic_gaps(days=30, similarity_threshold=0.3, limit=10)
    # Tesla topic not in our memory → should appear
    # NASA topic IS in our memory → should NOT appear
    titles = [g["competitor_title"] for g in gaps]
    assert any("Tesla" in t for t in titles)
    assert not any("Artemis" in t for t in titles)
