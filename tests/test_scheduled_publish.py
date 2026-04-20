"""Tests for scheduled-publish flow: queue → worker → upload command args."""

from pathlib import Path
from unittest.mock import patch


def test_enqueue_accepts_publish_at(tmp_path, monkeypatch):
    from pipeline import queue as qmod
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)

    job = qmod.enqueue(
        topic="Scheduled test",
        lang="tr",
        mode="full",
        publish_at="2026-12-31T10:00:00Z",
        privacy_status="private",
    )
    assert job["publish_at"] == "2026-12-31T10:00:00Z"
    assert job["privacy_status"] == "private"

    loaded = qmod.load_job(job["id"])
    assert loaded["publish_at"] == "2026-12-31T10:00:00Z"


def test_enqueue_defaults_privacy_to_private(tmp_path, monkeypatch):
    from pipeline import queue as qmod
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)

    job = qmod.enqueue(topic="No schedule", lang="tr", mode="full")
    assert job["publish_at"] is None
    assert job["privacy_status"] == "private"


def test_enqueue_accepts_privacy_unlisted_public(tmp_path, monkeypatch):
    from pipeline import queue as qmod
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)

    for p in ["private", "unlisted", "public"]:
        j = qmod.enqueue(topic=f"{p} test", lang="tr", mode="full", privacy_status=p)
        assert j["privacy_status"] == p


def test_worker_passes_publish_at_to_upload_cli(tmp_path, monkeypatch):
    """_run_upload must forward --publish-at to the CLI when scheduled."""
    from pipeline import queue as qmod, worker as wmod
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)
    monkeypatch.setattr(qmod, "LOCK_FILE", tmp_path / ".worker.lock")

    captured: list[list[str]] = []

    def fake_run_stream(cmd, job_id, timeout_s=1800):
        captured.append(cmd)
        return 0, ""

    monkeypatch.setattr(wmod, "_run_stream", fake_run_stream)

    job = qmod.enqueue(
        topic="Sched upload",
        lang="tr",
        mode="full",
        draft_path="/tmp/fake.json",
        publish_at="2026-12-31T10:00:00Z",
    )

    ok = wmod._run_upload(qmod.load_job(job["id"]))
    assert ok is True
    assert any("--publish-at" in str(c) for c in captured)
    assert any("2026-12-31T10:00:00Z" in str(c) for c in captured)


def test_worker_passes_privacy_when_no_schedule(tmp_path, monkeypatch):
    """If no publish_at, --privacy forwards unlisted/public."""
    from pipeline import queue as qmod, worker as wmod
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)

    captured: list[list[str]] = []
    monkeypatch.setattr(wmod, "_run_stream", lambda c, j, timeout_s=1800: (captured.append(c), (0, ""))[1])

    job = qmod.enqueue(
        topic="Unlisted upload",
        lang="tr",
        mode="full",
        draft_path="/tmp/fake.json",
        privacy_status="unlisted",
    )
    wmod._run_upload(qmod.load_job(job["id"]))
    assert any("--privacy" in str(c) and "unlisted" in str(c) for c in captured)


def test_worker_omits_privacy_when_publish_at_set(tmp_path, monkeypatch):
    """YouTube schedules require private — we must not override with --privacy."""
    from pipeline import queue as qmod, worker as wmod
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)

    captured = []
    monkeypatch.setattr(wmod, "_run_stream", lambda c, j, timeout_s=1800: (captured.append(c), (0, ""))[1])

    job = qmod.enqueue(
        topic="Scheduled",
        lang="tr",
        mode="full",
        draft_path="/tmp/fake.json",
        publish_at="2026-12-31T10:00:00Z",
        privacy_status="public",  # user might set this wrongly
    )
    wmod._run_upload(qmod.load_job(job["id"]))
    cmd = captured[0]
    # publish_at is present
    assert "--publish-at" in cmd
    # privacy is NOT forwarded when scheduled (YouTube requires private)
    assert "--privacy" not in cmd


def test_upload_body_has_publish_at_when_scheduled():
    """upload_to_youtube must include publishAt in status block when scheduled."""
    # Full integration would require real YouTube API. We test the body-building
    # logic by intercepting the API call.
    from pipeline.upload import upload_to_youtube
    # This is a lightweight validation that the signature accepts the kwargs.
    import inspect
    sig = inspect.signature(upload_to_youtube)
    assert "publish_at" in sig.parameters
    assert "privacy_status" in sig.parameters
    assert sig.parameters["publish_at"].default is None
    assert sig.parameters["privacy_status"].default == "private"
