"""Tests for thumbnail A/B state machine — create, rotate, finalize."""

from datetime import datetime, timezone, timedelta


def test_create_and_get_test(tmp_path, monkeypatch):
    from pipeline import thumbnail_ab as ab
    monkeypatch.setattr(ab, "DB_PATH", tmp_path / "ab.sqlite")

    variants = [
        {"path": "/t/v1.png", "prompt": "cinematic"},
        {"path": "/t/v2.png", "prompt": "cartoon"},
        {"path": "/t/v3.png", "prompt": "minimalist"},
    ]
    ab.create_test(video_id="vid_abc", variants=variants, token_path="/t/token.json",
                   channel="ayaz", rotation_hours=24)

    t = ab.get_test("vid_abc")
    assert t is not None
    assert t["status"] == "running"
    assert t["current_variant"] == 0
    assert t["rotation_hours"] == 24


def test_list_tests_filters_by_status(tmp_path, monkeypatch):
    from pipeline import thumbnail_ab as ab
    monkeypatch.setattr(ab, "DB_PATH", tmp_path / "ab.sqlite")

    ab.create_test(video_id="v1", variants=[{"path": "/a.png"}], token_path="/t")
    ab.create_test(video_id="v2", variants=[{"path": "/b.png"}], token_path="/t")
    ab.kill_test("v1")

    running = ab.list_tests(status="running")
    cancelled = ab.list_tests(status="cancelled")
    assert len(running) == 1 and running[0]["video_id"] == "v2"
    assert len(cancelled) == 1 and cancelled[0]["video_id"] == "v1"


def test_check_and_rotate_noops_when_not_yet_due(tmp_path, monkeypatch):
    from pipeline import thumbnail_ab as ab
    monkeypatch.setattr(ab, "DB_PATH", tmp_path / "ab.sqlite")

    ab.create_test(video_id="v1", variants=[
        {"path": "/a.png"}, {"path": "/b.png"}
    ], token_path="/t", rotation_hours=48)

    res = ab.check_and_rotate("v1", views_fetcher=lambda v, t: (100, 5),
                              uploader=lambda v, p, t: None)
    assert res["action"] == "none"
    assert "hours_remaining" in res


def test_check_and_rotate_advances_when_due(tmp_path, monkeypatch):
    from pipeline import thumbnail_ab as ab
    monkeypatch.setattr(ab, "DB_PATH", tmp_path / "ab.sqlite")

    ab.create_test(video_id="v1", variants=[
        {"path": "/a.png"}, {"path": "/b.png"}, {"path": "/c.png"},
    ], token_path="/t", rotation_hours=24)

    future = datetime.now(timezone.utc) + timedelta(hours=25)
    uploader_calls = []
    res = ab.check_and_rotate(
        "v1",
        views_fetcher=lambda v, tok: (120, 6),
        uploader=lambda v, p, tok: uploader_calls.append((v, p)),
        now=future,
    )
    assert res["action"] == "rotated"
    assert res["to"] == 1
    assert uploader_calls == [("v1", "/b.png")]

    # Second rotation
    future2 = future + timedelta(hours=25)
    uploader_calls.clear()
    res = ab.check_and_rotate(
        "v1",
        views_fetcher=lambda v, tok: (240, 12),
        uploader=lambda v, p, tok: uploader_calls.append((v, p)),
        now=future2,
    )
    assert res["action"] == "rotated"
    assert res["to"] == 2
    assert uploader_calls == [("v1", "/c.png")]


def test_rotation_finalizes_after_all_variants(tmp_path, monkeypatch):
    from pipeline import thumbnail_ab as ab
    monkeypatch.setattr(ab, "DB_PATH", tmp_path / "ab.sqlite")

    ab.create_test(video_id="v1", variants=[
        {"path": "/a.png"}, {"path": "/b.png"},
    ], token_path="/t", rotation_hours=1)

    # Variant 0 → 1 (rotation at +1h)
    now1 = datetime.now(timezone.utc) + timedelta(hours=1, minutes=1)
    upload_calls = []
    ab.check_and_rotate("v1",
                        views_fetcher=lambda v, tok: (50, 2),
                        uploader=lambda v, p, tok: upload_calls.append(p),
                        now=now1)

    # Variant 1 → finalize (rotation at +2h)
    now2 = now1 + timedelta(hours=1, minutes=1)
    res = ab.check_and_rotate("v1",
                              views_fetcher=lambda v, tok: (200, 10),
                              uploader=lambda v, p, tok: upload_calls.append(p),
                              now=now2)
    assert res["action"] == "finished"
    assert res["winner"] == 1  # b.png had higher views_per_hour
    assert upload_calls[-1] == "/b.png"  # winner uploaded permanently

    t = ab.get_test("v1")
    assert t["status"] == "finished"
    assert t["winner_variant"] == 1


def test_kill_test_stops_rotation(tmp_path, monkeypatch):
    from pipeline import thumbnail_ab as ab
    monkeypatch.setattr(ab, "DB_PATH", tmp_path / "ab.sqlite")

    ab.create_test(video_id="v1", variants=[
        {"path": "/a.png"}, {"path": "/b.png"},
    ], token_path="/t", rotation_hours=1)

    assert ab.kill_test("v1") is True
    # Now rotation check should noop
    future = datetime.now(timezone.utc) + timedelta(hours=25)
    res = ab.check_and_rotate("v1", now=future,
                              views_fetcher=lambda v, t: (100, 5),
                              uploader=lambda v, p, t: None)
    assert res["action"] == "none"


def test_scan_all_processes_multiple_tests(tmp_path, monkeypatch):
    from pipeline import thumbnail_ab as ab
    monkeypatch.setattr(ab, "DB_PATH", tmp_path / "ab.sqlite")

    ab.create_test(video_id="v1", variants=[
        {"path": "/a.png"}, {"path": "/b.png"},
    ], token_path="/t", rotation_hours=1)
    ab.create_test(video_id="v2", variants=[
        {"path": "/c.png"}, {"path": "/d.png"},
    ], token_path="/t", rotation_hours=1)

    future = datetime.now(timezone.utc) + timedelta(hours=25)
    results = ab.scan_and_rotate_all(
        views_fetcher=lambda v, t: (100, 5),
        uploader=lambda v, p, tok: None,
        now=future,
    )
    assert len(results) == 2
    assert all(r["action"] == "rotated" for r in results)
