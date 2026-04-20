"""Tests for auto-add-to-playlist flow."""

import inspect


def test_upload_signature_has_playlist_id():
    from pipeline.upload import upload_to_youtube
    sig = inspect.signature(upload_to_youtube)
    assert "playlist_id" in sig.parameters
    assert sig.parameters["playlist_id"].default is None


def test_worker_passes_playlist_from_extra(tmp_path, monkeypatch):
    from pipeline import queue as qmod, worker as wmod
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)

    captured = []
    monkeypatch.setattr(wmod, "_run_stream",
                        lambda c, j, timeout_s=1800: (captured.append(c), (0, ""))[1])

    job = qmod.enqueue(
        topic="Playlist test", lang="tr", mode="full",
        draft_path="/tmp/fake.json",
        extra={"playlist_id": "PLxyz123"},
    )
    wmod._run_upload(qmod.load_job(job["id"]))
    cmd = captured[0]
    assert "--playlist-id" in cmd
    assert "PLxyz123" in cmd


def test_worker_passes_playlist_from_direct_field(tmp_path, monkeypatch):
    """If job has playlist_id directly (not from preset), still forwarded."""
    from pipeline import queue as qmod, worker as wmod
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)

    captured = []
    monkeypatch.setattr(wmod, "_run_stream",
                        lambda c, j, timeout_s=1800: (captured.append(c), (0, ""))[1])

    job = qmod.enqueue(topic="Direct playlist", lang="tr", mode="full",
                       draft_path="/tmp/fake.json")
    qmod.update_job(job["id"], playlist_id="PLdirectfield")
    wmod._run_upload(qmod.load_job(job["id"]))
    cmd = captured[0]
    assert "--playlist-id" in cmd
    assert "PLdirectfield" in cmd


def test_worker_omits_playlist_when_none(tmp_path, monkeypatch):
    from pipeline import queue as qmod, worker as wmod
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)

    captured = []
    monkeypatch.setattr(wmod, "_run_stream",
                        lambda c, j, timeout_s=1800: (captured.append(c), (0, ""))[1])

    job = qmod.enqueue(topic="No playlist", lang="tr", mode="full",
                       draft_path="/tmp/fake.json")
    wmod._run_upload(qmod.load_job(job["id"]))
    cmd = captured[0]
    assert "--playlist-id" not in cmd


def test_channel_preset_playlist_flows_through_enqueue_job(tmp_path, monkeypatch):
    """When a channel preset has playlist_id, enqueue_job should copy it into extra."""
    from pipeline import channel_preset as cp, queue as qmod, config as cfg
    monkeypatch.setattr(cp, "CHANNELS_DIR", tmp_path / "channels")
    monkeypatch.setattr(cfg, "SKILL_DIR", tmp_path)
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path / "queue")

    cp.save_preset("brandchan", {"playlist_id": "PL_brand_xyz", "tone": "news"})

    # Inline enqueue_job-like merge — we test the merge_defaults pathway directly
    merged = cp.merge_defaults("brandchan", lang="tr")
    assert merged["playlist_id"] == "PL_brand_xyz"
    assert merged["tone"] == "news"
    assert merged["lang"] == "tr"
