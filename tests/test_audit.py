"""Tests for audit log — storage, filtering, exports, resilience."""

import csv
import json


def test_log_appends_entry(tmp_path, monkeypatch):
    from pipeline import audit
    monkeypatch.setattr(audit, "AUDIT_DIR", tmp_path)

    audit.log("job_queued", target="q_abc",
              actor="ayaz@example.com",
              details={"topic": "Test", "mode": "full"})

    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1
    line = files[0].read_text(encoding="utf-8").strip()
    rec = json.loads(line)
    assert rec["action"] == "job_queued"
    assert rec["target"] == "q_abc"
    assert rec["actor"] == "ayaz@example.com"
    assert rec["details"]["topic"] == "Test"
    assert rec["result"] == "ok"


def test_log_defaults_actor_to_system(tmp_path, monkeypatch):
    from pipeline import audit
    monkeypatch.setattr(audit, "AUDIT_DIR", tmp_path)

    audit.log("worker_started", "worker")
    rec = json.loads(list(tmp_path.glob("*.jsonl"))[0].read_text(encoding="utf-8").strip())
    assert rec["actor"] == "system"


def test_query_by_action(tmp_path, monkeypatch):
    from pipeline import audit
    monkeypatch.setattr(audit, "AUDIT_DIR", tmp_path)

    audit.log("job_queued", "q1")
    audit.log("job_queued", "q2")
    audit.log("video_uploaded", "vid1")
    audit.log("comment_hidden", "c1")

    queued = audit.query(action="job_queued")
    assert len(queued) == 2
    uploads = audit.query(action="video_uploaded")
    assert len(uploads) == 1


def test_query_by_actor_and_result(tmp_path, monkeypatch):
    from pipeline import audit
    monkeypatch.setattr(audit, "AUDIT_DIR", tmp_path)

    audit.log("job_queued", "q1", actor="alice")
    audit.log("job_queued", "q2", actor="bob")
    audit.log("job_failed", "q1", actor="alice", result="fail")

    alice = audit.query(actor="alice")
    assert len(alice) == 2
    alice_fails = audit.query(actor="alice", result="fail")
    assert len(alice_fails) == 1


def test_query_target_contains_substring(tmp_path, monkeypatch):
    from pipeline import audit
    monkeypatch.setattr(audit, "AUDIT_DIR", tmp_path)

    audit.log("video_uploaded", target="https://youtu.be/abc123")
    audit.log("video_uploaded", target="https://youtu.be/def456")

    hits = audit.query(target_contains="abc")
    assert len(hits) == 1
    assert "abc123" in hits[0]["target"]


def test_query_newest_first(tmp_path, monkeypatch):
    from pipeline import audit
    import time
    monkeypatch.setattr(audit, "AUDIT_DIR", tmp_path)

    audit.log("job_queued", "q1")
    time.sleep(0.01)
    audit.log("job_queued", "q2")
    time.sleep(0.01)
    audit.log("job_queued", "q3")

    all_q = audit.query(action="job_queued")
    assert all_q[0]["target"] == "q3"
    assert all_q[-1]["target"] == "q1"


def test_counts_by_action(tmp_path, monkeypatch):
    from pipeline import audit
    monkeypatch.setattr(audit, "AUDIT_DIR", tmp_path)

    for _ in range(5):
        audit.log("job_queued", "x")
    for _ in range(2):
        audit.log("video_uploaded", "y")
    audit.log("comment_hidden", "c")

    c = audit.counts_by_action(days=30)
    assert c["job_queued"] == 5
    assert c["video_uploaded"] == 2
    assert c["comment_hidden"] == 1
    # Ordering: highest first
    keys = list(c.keys())
    assert keys[0] == "job_queued"


def test_export_csv_writes_header_and_rows(tmp_path, monkeypatch):
    from pipeline import audit
    monkeypatch.setattr(audit, "AUDIT_DIR", tmp_path)

    audit.log("job_queued", "q1", actor="alice",
              details={"mode": "full"})
    audit.log("video_uploaded", "vid1", actor="alice",
              details={"url": "https://youtu.be/xyz"})

    out = tmp_path / "export.csv"
    audit.export_csv(out, days=30)
    assert out.exists()

    with open(out, encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) == 2
    actions = [r["action"] for r in reader]
    assert "job_queued" in actions
    assert "video_uploaded" in actions


def test_log_never_raises_on_disk_error(tmp_path, monkeypatch):
    """Audit is best-effort — must not break the caller on disk failure."""
    from pipeline import audit
    # Point to a file instead of dir to force an error
    bad = tmp_path / "not-a-dir"
    bad.write_text("x")
    monkeypatch.setattr(audit, "AUDIT_DIR", bad)

    # Must not raise
    audit.log("job_queued", "q1")


def test_corrupt_line_skipped_in_query(tmp_path, monkeypatch):
    from pipeline import audit
    monkeypatch.setattr(audit, "AUDIT_DIR", tmp_path)

    audit.log("job_queued", "q1")
    # Append garbage
    mf = list(tmp_path.glob("*.jsonl"))[0]
    with open(mf, "a") as f:
        f.write("not-json\n")

    results = audit.query(action="job_queued")
    assert len(results) == 1  # garbage line ignored
