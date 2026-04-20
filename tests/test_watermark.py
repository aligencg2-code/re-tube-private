"""Tests for watermark module — fingerprint storage, similarity, registry."""

import sqlite3
from pathlib import Path


def test_hamming_distance_basic():
    from pipeline.watermark import _hamming_distance, _similarity
    assert _hamming_distance("", "") == 0
    # Identical hashes
    h = "deadbeef" * 8
    assert _hamming_distance(h, h) == 0
    assert _similarity(h, h) == 1.0
    # Completely different (all bits flipped)
    h1 = "ff" * 8
    h2 = "00" * 8
    assert _similarity(h1, h2) == 0.0


def test_similarity_handles_mismatched_lengths():
    from pipeline.watermark import _similarity
    assert _similarity("abc", "abcdef") == 0.0
    assert _similarity("", "abc") == 0.0


def test_register_and_list_prints(tmp_path, monkeypatch):
    from pipeline import watermark as wm
    monkeypatch.setattr(wm, "DB_PATH", tmp_path / "fp.sqlite")

    # Stub compute_fingerprint so we don't need ffmpeg here
    monkeypatch.setattr(wm, "compute_fingerprint",
                        lambda p: {"hash": "abcdef12" * 8, "method": "stub", "ok": True})

    wm.register("vid_001", "/nowhere.mp4", label="Test video 1")
    wm.register("vid_002", "/nowhere2.mp4", label="Test video 2",
                watermark_id="wm_abc")

    prints = wm.list_prints()
    assert len(prints) == 2
    ids = [p["video_id"] for p in prints]
    assert "vid_001" in ids and "vid_002" in ids

    # Watermark field carried through
    v2 = next(p for p in prints if p["video_id"] == "vid_002")
    assert v2["watermark_id"] == "wm_abc"


def test_register_upsert_same_video_id(tmp_path, monkeypatch):
    from pipeline import watermark as wm
    monkeypatch.setattr(wm, "DB_PATH", tmp_path / "fp.sqlite")

    counter = [0]
    def fake_fp(p):
        counter[0] += 1
        return {"hash": f"aa{counter[0]:02d}" * 16, "method": "stub", "ok": True}
    monkeypatch.setattr(wm, "compute_fingerprint", fake_fp)

    wm.register("vid_x", "/old.mp4", label="old")
    wm.register("vid_x", "/new.mp4", label="updated")

    prints = wm.list_prints()
    assert len(prints) == 1
    assert prints[0]["label"] == "updated"


def test_check_against_empty_registry_returns_no_match(tmp_path, monkeypatch):
    from pipeline import watermark as wm
    monkeypatch.setattr(wm, "DB_PATH", tmp_path / "fp.sqlite")
    monkeypatch.setattr(wm, "compute_fingerprint",
                        lambda p: {"hash": "00" * 32, "method": "stub", "ok": True})

    r = wm.check_against_registry("/some.mp4")
    assert r["best_match"] is None
    assert r["above_threshold"] is False


def test_check_finds_identical_fingerprint(tmp_path, monkeypatch):
    from pipeline import watermark as wm
    monkeypatch.setattr(wm, "DB_PATH", tmp_path / "fp.sqlite")

    # Register a video with a known hash
    same_hash = "deadbeef" * 8
    monkeypatch.setattr(wm, "compute_fingerprint",
                        lambda p: {"hash": same_hash, "method": "stub", "ok": True})
    wm.register("original_vid", "/orig.mp4", label="Original")

    # A suspect copy has the exact same hash → should match at 100%
    r = wm.check_against_registry("/suspect.mp4", threshold=0.85,
                                    source_url="https://youtube.com/suspect")
    assert r["best_match"] is not None
    assert r["best_match"]["video_id"] == "original_vid"
    assert r["best_match"]["similarity"] == 1.0
    assert r["above_threshold"] is True


def test_check_below_threshold_returns_false_positive_free(tmp_path, monkeypatch):
    from pipeline import watermark as wm
    monkeypatch.setattr(wm, "DB_PATH", tmp_path / "fp.sqlite")

    monkeypatch.setattr(wm, "compute_fingerprint",
                        lambda p: {"hash": "aabbccdd" * 8, "method": "stub", "ok": True})
    wm.register("original_vid", "/orig.mp4")

    # Switch the fingerprint for the "suspect"
    monkeypatch.setattr(wm, "compute_fingerprint",
                        lambda p: {"hash": "11223344" * 8, "method": "stub", "ok": True})

    r = wm.check_against_registry("/unrelated.mp4", threshold=0.85)
    assert r["best_match"] is not None
    assert r["above_threshold"] is False


def test_check_only_compares_same_method(tmp_path, monkeypatch):
    """Chromaprint fingerprints aren't comparable with audio_digest ones."""
    from pipeline import watermark as wm
    monkeypatch.setattr(wm, "DB_PATH", tmp_path / "fp.sqlite")

    monkeypatch.setattr(wm, "compute_fingerprint",
                        lambda p: {"hash": "aaaa" * 16, "method": "chromaprint", "ok": True})
    wm.register("vid_cr", "/a.mp4")

    # Suspect uses different method → no comparison possible
    monkeypatch.setattr(wm, "compute_fingerprint",
                        lambda p: {"hash": "aaaa" * 16, "method": "audio_digest", "ok": True})
    r = wm.check_against_registry("/b.mp4")
    # No same-method prints to compare against
    assert r["best_match"] is None or len(r.get("all_comparisons", [])) == 0


def test_recent_matches_records_and_returns(tmp_path, monkeypatch):
    from pipeline import watermark as wm
    monkeypatch.setattr(wm, "DB_PATH", tmp_path / "fp.sqlite")

    same_hash = "cafebabe" * 8
    monkeypatch.setattr(wm, "compute_fingerprint",
                        lambda p: {"hash": same_hash, "method": "stub", "ok": True})
    wm.register("orig", "/orig.mp4")
    wm.check_against_registry("/copy1.mp4", source_url="https://y.com/c1")
    wm.check_against_registry("/copy2.mp4", source_url="https://y.com/c2")

    matches = wm.recent_matches()
    assert len(matches) >= 2
    assert all(m["matched_video_id"] == "orig" for m in matches)


def test_compute_fingerprint_handles_missing_ffmpeg(tmp_path, monkeypatch):
    """Graceful failure when fingerprinting fails completely."""
    from pipeline import watermark as wm
    monkeypatch.setattr(wm, "has_chromaprint", lambda: False)

    # Force _audio_digest_fingerprint to raise
    def boom(p):
        raise RuntimeError("No ffmpeg")
    monkeypatch.setattr(wm, "_audio_digest_fingerprint", boom)

    r = wm.compute_fingerprint("/nowhere.mp4")
    assert r["ok"] is False
    assert "error" in r
