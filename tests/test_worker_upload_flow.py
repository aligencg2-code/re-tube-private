"""Regression tests for produce -> upload chain in worker.process_one.

Bug v2.0.1: process_one() called _run_upload(job) with a stale local dict
that didn't have draft_path set by _run_produce(). Result: every "full" mode
job failed at upload with "Upload icin draft yok" even though produce had
just generated the draft successfully.

These tests verify:
  1. _run_produce mutates the local job dict with draft_path
  2. process_one reloads from disk before upload as a safety net
  3. End-to-end: full mode job goes draft_path-less → produce → upload uses
     the new draft_path correctly
"""

import json
from pathlib import Path


def test_run_produce_sets_draft_path_on_local_job(tmp_path, monkeypatch):
    """When _run_produce auto-generates a draft, the LOCAL job dict must be updated."""
    from pipeline import worker, queue as qmod, config as cfg
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path / "queue")
    monkeypatch.setattr(cfg, "DRAFTS_DIR", tmp_path / "drafts")
    (tmp_path / "drafts").mkdir()

    # Mock _run_stream to "succeed" without actually running anything
    captured_cmds = []
    def fake_stream(cmd, job_id, timeout_s=None):
        captured_cmds.append(list(cmd))
        # Simulate draft creation: write a fake draft file
        if cmd[0] == "draft":
            (cfg.DRAFTS_DIR / "fake_draft.json").write_text(
                json.dumps({"job_id": "fake", "script": "x"}), encoding="utf-8"
            )
        return 0, ""
    monkeypatch.setattr(worker, "_run_stream", fake_stream)

    # Enqueue a job WITHOUT a draft_path
    job = qmod.enqueue(topic="Test topic", lang="tr", mode="full")
    assert job["draft_path"] is None  # precondition

    ok = worker._run_produce(job)
    assert ok is True
    # Critical: local job dict was updated with the new draft_path
    assert job["draft_path"] is not None, (
        "BUG: _run_produce did not update local job dict with draft_path. "
        "Subsequent _run_upload(job) call would fail."
    )
    assert "fake_draft.json" in job["draft_path"]


def test_full_mode_chain_uses_draft_path_in_upload(tmp_path, monkeypatch):
    """End-to-end: full mode goes draft → produce → upload with correct draft_path."""
    from pipeline import worker, queue as qmod, config as cfg
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path / "queue")
    monkeypatch.setattr(cfg, "DRAFTS_DIR", tmp_path / "drafts")
    (tmp_path / "drafts").mkdir()

    captured_cmds = []
    def fake_stream(cmd, job_id, timeout_s=None):
        captured_cmds.append(list(cmd))
        if cmd[0] == "draft":
            (cfg.DRAFTS_DIR / "draft_full.json").write_text(
                json.dumps({"job_id": "full"}), encoding="utf-8"
            )
        return 0, ""
    monkeypatch.setattr(worker, "_run_stream", fake_stream)

    job = qmod.enqueue(topic="End to end test", lang="tr", mode="full")
    worker.process_one(job)

    # Inspect the captured commands to verify upload got the draft path
    upload_cmds = [c for c in captured_cmds if c and c[0] == "upload"]
    assert len(upload_cmds) == 1, (
        f"Expected exactly 1 upload command, got {len(upload_cmds)}. "
        f"All cmds: {captured_cmds}"
    )
    upload_cmd = upload_cmds[0]
    assert "--draft" in upload_cmd
    draft_idx = upload_cmd.index("--draft")
    draft_arg = upload_cmd[draft_idx + 1]
    assert "draft_full.json" in draft_arg, (
        f"upload command got draft path '{draft_arg}', "
        f"expected to contain 'draft_full.json'"
    )

    # Final job status should be 'done' (or at least not 'failed' with draft error)
    final = qmod.load_job(job["id"])
    assert final["status"] != "failed", (
        f"Job failed: {final.get('error')}. Full mode should complete cleanly."
    )


def test_process_one_reloads_job_before_upload(tmp_path, monkeypatch):
    """Even if _run_produce somehow fails to update local dict, process_one
    reloads from disk to recover. This is the safety-net guard."""
    from pipeline import worker, queue as qmod, config as cfg
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path / "queue")
    monkeypatch.setattr(cfg, "DRAFTS_DIR", tmp_path / "drafts")
    (tmp_path / "drafts").mkdir()

    captured = []
    def fake_stream(cmd, job_id, timeout_s=None):
        captured.append(list(cmd))
        return 0, ""
    monkeypatch.setattr(worker, "_run_stream", fake_stream)

    # Stub _run_produce to set draft_path ONLY in the DB (simulating the
    # pre-fix bug where local dict wasn't updated)
    def buggy_produce(job):
        # Simulate: DB updated, local dict NOT updated
        qmod.update_job(job["id"], draft_path="/fake/path/draft.json")
        return True
    monkeypatch.setattr(worker, "_run_produce", buggy_produce)

    job = qmod.enqueue(topic="Reload test", lang="tr", mode="full")
    worker.process_one(job)

    # process_one should have reloaded from disk and seen the draft_path
    upload_cmds = [c for c in captured if c and c[0] == "upload"]
    assert len(upload_cmds) == 1
    assert "/fake/path/draft.json" in " ".join(upload_cmds[0])

    # Job should NOT have the "Upload icin draft yok" error
    final = qmod.load_job(job["id"])
    assert final.get("error") != "Upload icin draft yok"


def test_video_mode_skips_upload(tmp_path, monkeypatch):
    """mode=video should NOT trigger upload (sanity check we didn't break this)."""
    from pipeline import worker, queue as qmod, config as cfg
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path / "queue")
    monkeypatch.setattr(cfg, "DRAFTS_DIR", tmp_path / "drafts")
    (tmp_path / "drafts").mkdir()

    captured = []
    def fake_stream(cmd, job_id, timeout_s=None):
        captured.append(list(cmd))
        if cmd[0] == "draft":
            (cfg.DRAFTS_DIR / "vid.json").write_text("{}", encoding="utf-8")
        return 0, ""
    monkeypatch.setattr(worker, "_run_stream", fake_stream)

    job = qmod.enqueue(topic="Video only", lang="tr", mode="video")
    worker.process_one(job)

    # No upload command should have run
    upload_cmds = [c for c in captured if c and c[0] == "upload"]
    assert upload_cmds == [], "video mode should not trigger upload"

    # Job should be done
    final = qmod.load_job(job["id"])
    assert final["status"] == "done"
