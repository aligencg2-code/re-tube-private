"""Tests for queue + worker crash-recovery semantics."""

import json
from pathlib import Path


def test_stuck_producing_jobs_are_requeued(tmp_path, monkeypatch):
    """A 'producing' job with no live worker must be reset to 'pending'."""
    from pipeline import queue as qmod, worker as wmod

    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)
    monkeypatch.setattr(qmod, "LOCK_FILE", tmp_path / ".worker.lock")

    job = qmod.enqueue(topic="Resume test", lang="tr", mode="draft")
    qmod.update_job(job["id"], status="producing", stage="half-done", progress_pct=50)

    # No lock file → no live worker
    assert not qmod.worker_running()

    recovered = wmod.recover_stuck_jobs()
    assert recovered == 1

    refreshed = qmod.load_job(job["id"])
    assert refreshed["status"] == "pending"
    assert "RECOVERY" in "\n".join(refreshed.get("log_tail", []))


def test_stuck_uploading_jobs_go_back_to_produced(tmp_path, monkeypatch):
    """A 'uploading' crash means video exists — reset to 'produced'."""
    from pipeline import queue as qmod, worker as wmod

    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)
    monkeypatch.setattr(qmod, "LOCK_FILE", tmp_path / ".worker.lock")

    job = qmod.enqueue(topic="Upload test", lang="tr", mode="full")
    qmod.update_job(job["id"], status="uploading", progress_pct=95)

    recovered = wmod.recover_stuck_jobs()
    assert recovered == 1

    refreshed = qmod.load_job(job["id"])
    assert refreshed["status"] == "produced"


def test_pending_and_done_jobs_untouched(tmp_path, monkeypatch):
    """Recovery must only touch in-flight statuses."""
    from pipeline import queue as qmod, worker as wmod

    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)
    monkeypatch.setattr(qmod, "LOCK_FILE", tmp_path / ".worker.lock")

    j1 = qmod.enqueue(topic="Pending job", lang="tr", mode="draft")
    j2 = qmod.enqueue(topic="Done job", lang="tr", mode="draft")
    qmod.update_job(j2["id"], status="done", progress_pct=100)

    recovered = wmod.recover_stuck_jobs()
    assert recovered == 0
    assert qmod.load_job(j1["id"])["status"] == "pending"
    assert qmod.load_job(j2["id"])["status"] == "done"


def test_fifo_order_preserved(tmp_path, monkeypatch):
    """list_jobs returns oldest first (FIFO)."""
    import time
    from pipeline import queue as qmod

    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)

    a = qmod.enqueue(topic="First", lang="tr", mode="draft")
    time.sleep(0.01)
    b = qmod.enqueue(topic="Second", lang="tr", mode="draft")
    time.sleep(0.01)
    c = qmod.enqueue(topic="Third", lang="tr", mode="draft")

    jobs = qmod.list_jobs(statuses=("pending",))
    assert [j["id"] for j in jobs] == [a["id"], b["id"], c["id"]]
    assert qmod.next_pending()["id"] == a["id"]


def test_cancel_flag_mechanism(tmp_path, monkeypatch):
    """Cancel signal for a running job = flag file; pending = direct state change."""
    from pipeline import queue as qmod

    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)

    # Pending job → direct cancellation
    j1 = qmod.enqueue(topic="Pending cancel", lang="tr", mode="draft")
    qmod.cancel_job(j1["id"])
    assert qmod.load_job(j1["id"])["status"] == "cancelled"

    # Running job → signals via flag file
    j2 = qmod.enqueue(topic="Running cancel", lang="tr", mode="draft")
    qmod.update_job(j2["id"], status="producing")
    qmod.cancel_job(j2["id"])
    assert qmod.is_cancelled(j2["id"])
    assert qmod.load_job(j2["id"])["status"] == "producing"  # worker is responsible for state transition

    qmod.clear_cancel_flag(j2["id"])
    assert not qmod.is_cancelled(j2["id"])


def test_worker_lock_exclusive(tmp_path, monkeypatch):
    """Only one worker can hold the lock at a time when lock-holder PID is alive."""
    import os
    from pipeline import queue as qmod

    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)
    monkeypatch.setattr(qmod, "LOCK_FILE", tmp_path / ".worker.lock")

    live_pid = os.getpid()
    assert qmod.acquire_worker_lock(pid=live_pid)
    # Second attempt with a different pid must fail because pytest itself is alive
    assert not qmod.acquire_worker_lock(pid=live_pid + 1)
    qmod.release_worker_lock()
    assert qmod.acquire_worker_lock(pid=live_pid)
    qmod.release_worker_lock()


def test_worker_lock_stale_pid_recovered(tmp_path, monkeypatch):
    """If lock holder PID is dead, new worker can steal the lock."""
    from pipeline import queue as qmod

    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path)
    monkeypatch.setattr(qmod, "LOCK_FILE", tmp_path / ".worker.lock")

    # Write a lock with a clearly-dead PID
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / ".worker.lock").write_text(json.dumps({"pid": 999999, "started_at": "x"}))

    # Fresh worker should steal it
    assert qmod.acquire_worker_lock()
    qmod.release_worker_lock()
