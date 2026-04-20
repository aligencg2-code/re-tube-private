"""Tests for topic_memory — storage, similarity, time filtering, channel filtering."""


def test_tokenize_drops_stopwords_and_short_tokens():
    from pipeline.topic_memory import _tokenize
    tokens = _tokenize("This is a test about the NASA lunar mission for 2026")
    # Stopwords removed, short tokens removed
    assert "the" not in tokens
    assert "is" not in tokens
    assert "a" not in tokens
    assert "nasa" in tokens
    assert "lunar" in tokens
    assert "mission" in tokens
    assert "2026" in tokens


def test_tokenize_handles_turkish_chars():
    from pipeline.topic_memory import _tokenize
    tokens = _tokenize("Yapay zeka şirketleri çöktü")
    assert "yapay" in tokens
    assert "zeka" in tokens
    assert "şirketleri" in tokens
    assert "çöktü" in tokens


def test_similarity_identical_is_one():
    from pipeline.topic_memory import _similarity, _tokenize
    a = _tokenize("NASA lunar mission 2026")
    b = _tokenize("NASA lunar mission 2026")
    assert _similarity(a, b) == 1.0


def test_similarity_disjoint_is_zero():
    from pipeline.topic_memory import _similarity, _tokenize
    a = _tokenize("Tesla robotaxi launch")
    b = _tokenize("Bitcoin hits 150000")
    assert _similarity(a, b) == 0.0


def test_similarity_partial_overlap():
    from pipeline.topic_memory import _similarity, _tokenize
    a = _tokenize("NASA lunar mission 2026 launch")
    b = _tokenize("NASA Moon mission coming soon")
    sim = _similarity(a, b)
    assert 0.0 < sim < 1.0


def test_remember_and_recent_roundtrip(tmp_path, monkeypatch):
    from pipeline import topic_memory as tm
    monkeypatch.setattr(tm, "DB_PATH", tmp_path / "mem.sqlite")

    tm.remember("First topic about lunar mission", job_id="q_a", channel="ayaz")
    tm.remember("Second topic about AI regulation", job_id="q_b", channel="ikinci")

    assert tm.count() == 2
    all_topics = tm.recent(days=30)
    topics = [t["topic"] for t in all_topics]
    assert "First topic about lunar mission" in topics
    assert "Second topic about AI regulation" in topics


def test_find_similar_detects_paraphrase(tmp_path, monkeypatch):
    from pipeline import topic_memory as tm
    monkeypatch.setattr(tm, "DB_PATH", tmp_path / "mem.sqlite")

    tm.remember("NASA launches crewed lunar mission Artemis 3", job_id="q_a")
    # Paraphrase — should be detected
    hits = tm.find_similar("NASA sends astronauts Moon Artemis", threshold=0.2, limit=5)
    assert len(hits) >= 1
    assert "NASA" in hits[0]["topic"]


def test_find_similar_ignores_unrelated(tmp_path, monkeypatch):
    from pipeline import topic_memory as tm
    monkeypatch.setattr(tm, "DB_PATH", tmp_path / "mem.sqlite")

    tm.remember("Tesla robotaxi launch event", job_id="q_a")
    hits = tm.find_similar("Bitcoin price reaches new all-time high", threshold=0.5)
    assert hits == []


def test_find_similar_respects_time_window(tmp_path, monkeypatch):
    """An old topic outside `days` window should not appear."""
    from pipeline import topic_memory as tm
    import sqlite3
    monkeypatch.setattr(tm, "DB_PATH", tmp_path / "mem.sqlite")

    tm.remember("Old topic about NASA Moon", job_id="q_old")
    # Backdate it manually
    conn = sqlite3.connect(str(tm.DB_PATH))
    conn.execute("UPDATE topics SET created_at = '2020-01-01T00:00:00+00:00'")
    conn.commit()
    conn.close()

    # With 30-day window, should not find
    hits_recent = tm.find_similar("NASA Moon mission", threshold=0.2, days=30)
    assert hits_recent == []
    # With None window, should find
    hits_all = tm.find_similar("NASA Moon mission", threshold=0.2, days=None)
    assert len(hits_all) >= 1


def test_find_similar_channel_filter(tmp_path, monkeypatch):
    from pipeline import topic_memory as tm
    monkeypatch.setattr(tm, "DB_PATH", tmp_path / "mem.sqlite")

    tm.remember("NASA lunar mission", job_id="q_a", channel="ayaz")
    tm.remember("NASA lunar mission", job_id="q_b", channel="ikinci")

    # Channel-scoped search only returns that channel's match
    hits_ayaz = tm.find_similar("NASA Moon mission", threshold=0.2, channel="ayaz")
    assert all(h["channel"] == "ayaz" for h in hits_ayaz)


def test_delete_removes_record(tmp_path, monkeypatch):
    from pipeline import topic_memory as tm
    monkeypatch.setattr(tm, "DB_PATH", tmp_path / "mem.sqlite")

    tm.remember("First", job_id="q_a")
    tm.remember("Second", job_id="q_b")
    assert tm.count() == 2
    rid = tm.recent(days=30)[0]["id"]
    assert tm.delete(rid) is True
    assert tm.count() == 1


def test_empty_topic_returns_nothing(tmp_path, monkeypatch):
    from pipeline import topic_memory as tm
    monkeypatch.setattr(tm, "DB_PATH", tmp_path / "mem.sqlite")

    tm.remember("Real topic", job_id="q")
    assert tm.find_similar("") == []
    assert tm.find_similar("   ") == []
