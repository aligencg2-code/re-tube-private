"""Tests for queue.retry_job + PipelineState.reset_from_stage."""

import json


def test_state_reset_from_voiceover_keeps_earlier_stages():
    """Reset from voiceover must preserve research/draft/broll."""
    from pipeline.state import PipelineState, STAGES

    draft = {}
    state = PipelineState(draft)
    for s in STAGES:
        state.complete_stage(s, {"artifact": "x"})

    dropped = state.reset_from_stage("voiceover")
    assert "voiceover" in dropped
    assert "upload" in dropped
    assert state.is_done("research")
    assert state.is_done("draft")
    assert state.is_done("broll")
    assert not state.is_done("voiceover")
    assert not state.is_done("captions")
    assert not state.is_done("upload")


def test_state_reset_from_upload_only():
    from pipeline.state import PipelineState, STAGES

    state = PipelineState({})
    for s in STAGES:
        state.complete_stage(s)

    dropped = state.reset_from_stage("upload")
    assert dropped == ["upload"]
    for s in STAGES[:-1]:
        assert state.is_done(s)


def test_state_reset_invalid_stage_raises():
    from pipeline.state import PipelineState
    state = PipelineState({})
    try:
        state.reset_from_stage("nonsense")
        assert False, "Should have raised"
    except ValueError:
        pass


def test_retry_job_without_stage_requeues_as_produced(tmp_path, monkeypatch):
    """retry_job(..., from_stage=None) with draft → status=produced (upload only)."""
    from pipeline import queue as qmod
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)

    draft_file = tmp_path / "fake_draft.json"
    draft_file.write_text(json.dumps({"job_id": "x", "_pipeline_state": {}}), encoding="utf-8")

    job = qmod.enqueue(topic="Retry test", lang="tr", mode="full",
                       draft_path=str(draft_file))
    qmod.update_job(job["id"], status="failed", error="upload timeout")

    result = qmod.retry_job(job["id"], from_stage=None)
    assert result["status"] == "produced"
    assert result["error"] is None


def test_retry_job_from_voiceover_resets_state_and_requeues_pending(tmp_path, monkeypatch):
    from pipeline import queue as qmod
    from pipeline.state import STAGES
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)

    draft_file = tmp_path / "full_draft.json"
    draft = {"job_id": "y", "_pipeline_state": {s: {"status": "done"} for s in STAGES}}
    draft_file.write_text(json.dumps(draft), encoding="utf-8")

    job = qmod.enqueue(topic="Stage retry", lang="tr", mode="full",
                       draft_path=str(draft_file))
    qmod.update_job(job["id"], status="failed", error="voiceover gibberish")

    result = qmod.retry_job(job["id"], from_stage="voiceover")
    assert result["status"] == "pending"

    reloaded = json.loads(draft_file.read_text(encoding="utf-8"))
    ps = reloaded["_pipeline_state"]
    assert ps["research"]["status"] == "done"
    assert ps["broll"]["status"] == "done"
    assert "voiceover" not in ps
    assert "upload" not in ps


def test_retry_job_nonexistent_returns_none(tmp_path, monkeypatch):
    from pipeline import queue as qmod
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)
    assert qmod.retry_job("q_nonexistent_999") is None


def test_retry_job_without_draft_falls_back_to_pending(tmp_path, monkeypatch):
    """Retry on a job with no draft_path → pending (can't skip produce)."""
    from pipeline import queue as qmod
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)

    job = qmod.enqueue(topic="No draft", lang="tr", mode="full")
    qmod.update_job(job["id"], status="failed", error="draft failed")

    result = qmod.retry_job(job["id"], from_stage=None)
    assert result["status"] == "pending"
