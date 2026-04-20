"""Job queue for multi-video production.

Stores jobs as JSON files under SKILL_DIR/queue/ and coordinates a
single-worker lock so only one job processes at a time. The UI adds jobs
instantly and the background worker drains them in FIFO order.

Lifecycle:
    pending -> producing -> produced -> uploading -> done (or failed/cancelled)

Uploads are chained after production completes so videos hit YouTube in
submission order.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .config import SKILL_DIR


QUEUE_DIR = SKILL_DIR / "queue"
LOCK_FILE = QUEUE_DIR / ".worker.lock"

STATUSES = (
    "pending",       # waiting for worker
    "producing",     # worker is generating video
    "produced",      # video ready, waiting for upload slot
    "uploading",     # worker is uploading to YouTube
    "done",          # uploaded successfully
    "failed",        # error — see .error field
    "cancelled",     # user cancelled
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_path(job_id: str) -> Path:
    return QUEUE_DIR / f"{job_id}.json"


def ensure_queue_dir() -> None:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)


def enqueue(
    *,
    topic: str,
    context: str = "",
    lang: str = "tr",
    mode: str = "full",          # full | video | draft
    video_format: str = "shorts", # shorts | video
    duration: str = "short",      # short | 3min | 5min | 10min
    channel: str | None = None,
    force: bool = False,
    draft_path: str | None = None,
    publish_at: str | None = None,   # ISO-8601 UTC for scheduled publish
    privacy_status: str = "private",
    extra: dict | None = None,
) -> dict:
    """Create a new queue job. Returns the job dict."""
    ensure_queue_dir()
    # Nanosecond precision + 4-digit collision avoidance for rapid enqueues
    import secrets
    job_id = f"q{time.time_ns()}{secrets.token_hex(2)}"
    job = {
        "id": job_id,
        "status": "pending",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "topic": topic,
        "context": context,
        "lang": lang,
        "mode": mode,
        "format": video_format,
        "duration": duration,
        "channel": channel,
        "force": bool(force),
        "draft_path": draft_path,
        "publish_at": publish_at,
        "privacy_status": privacy_status,
        "progress_pct": 0,
        "stage": "queued",
        "log_tail": [],
        "error": None,
        "extra": extra or {},
    }
    _job_path(job_id).write_text(
        json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    try:
        from . import audit as _audit
        _audit.log("job_queued", target=job_id,
                   details={"topic": topic[:80], "mode": mode, "lang": lang, "channel": channel})
    except Exception:
        pass
    return job


def load_job(job_id: str) -> dict | None:
    p = _job_path(job_id)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_job(job: dict) -> None:
    job["updated_at"] = _now_iso()
    _job_path(job["id"]).write_text(
        json.dumps(job, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def update_job(job_id: str, **fields) -> dict | None:
    job = load_job(job_id)
    if not job:
        return None
    prev_status = job.get("status")
    job.update(fields)
    save_job(job)
    # Fire webhook on status transition if the job was created via API with webhook_url
    new_status = fields.get("status")
    if new_status and new_status != prev_status:
        webhook_url = (job.get("extra") or {}).get("webhook_url")
        if webhook_url:
            try:
                from . import api_server
                api_server.send_webhook(webhook_url, {
                    "event": "job.status_changed",
                    "job_id": job_id,
                    "previous_status": prev_status,
                    "new_status": new_status,
                    "topic": job.get("topic"),
                    "progress_pct": job.get("progress_pct", 0),
                    "stage": job.get("stage"),
                    "ts": job.get("updated_at"),
                })
            except Exception:
                pass
        # Broadcast to SSE subscribers (internal real-time dashboard)
        try:
            from . import sse_server
            sse_server.emit("job.status_changed", {
                "job_id": job_id,
                "previous_status": prev_status,
                "new_status": new_status,
                "topic": job.get("topic"),
                "progress_pct": job.get("progress_pct", 0),
                "stage": job.get("stage"),
            })
        except Exception:
            pass
    return job


def list_jobs(statuses: Iterable[str] | None = None) -> list[dict]:
    ensure_queue_dir()
    jobs = []
    for p in sorted(QUEUE_DIR.glob("q*.json")):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
            if statuses is None or j.get("status") in statuses:
                jobs.append(j)
        except Exception:
            continue
    jobs.sort(key=lambda j: j.get("created_at", ""))
    return jobs


def delete_job(job_id: str) -> bool:
    p = _job_path(job_id)
    if p.exists():
        p.unlink()
        return True
    return False


def cancel_job(job_id: str) -> dict | None:
    """Mark a pending job as cancelled. Running jobs need a separate signal."""
    job = load_job(job_id)
    if not job:
        return None
    if job["status"] in ("done", "failed", "cancelled"):
        return job
    if job["status"] == "pending":
        job["status"] = "cancelled"
        job["error"] = "Kullanici tarafindan iptal edildi"
        save_job(job)
    else:
        # Signal running worker via a flag file
        (QUEUE_DIR / f"{job_id}.cancel").write_text("1", encoding="utf-8")
    try:
        from . import audit as _audit
        _audit.log("job_cancelled", target=job_id,
                   details={"was_status": job.get("status")})
    except Exception:
        pass
    return job


def is_cancelled(job_id: str) -> bool:
    return (QUEUE_DIR / f"{job_id}.cancel").exists()


def clear_cancel_flag(job_id: str) -> None:
    f = QUEUE_DIR / f"{job_id}.cancel"
    if f.exists():
        f.unlink()


def next_pending() -> dict | None:
    """Return the oldest pending job or None."""
    for j in list_jobs(statuses=("pending",)):
        return j
    return None


def next_produced() -> dict | None:
    """Oldest produced (awaiting upload) job."""
    for j in list_jobs(statuses=("produced",)):
        return j
    return None


# ── Worker lock ────────────────────────────────────────────────────────
def acquire_worker_lock(pid: int | None = None) -> bool:
    """Atomic lock so only one worker runs. Returns True if acquired."""
    ensure_queue_dir()
    pid = pid or os.getpid()
    try:
        fd = os.open(str(LOCK_FILE), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps({"pid": pid, "started_at": _now_iso()}))
        return True
    except FileExistsError:
        # Check staleness — if PID no longer exists, steal the lock
        try:
            info = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
            old_pid = int(info.get("pid", 0))
            if old_pid and not _pid_alive(old_pid):
                LOCK_FILE.unlink()
                return acquire_worker_lock(pid)
        except Exception:
            pass
        return False


def release_worker_lock() -> None:
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
    except Exception:
        pass


def worker_running() -> bool:
    if not LOCK_FILE.exists():
        return False
    try:
        info = json.loads(LOCK_FILE.read_text(encoding="utf-8"))
        pid = int(info.get("pid", 0))
        return _pid_alive(pid)
    except Exception:
        return False


def worker_info() -> dict | None:
    if not LOCK_FILE.exists():
        return None
    try:
        return json.loads(LOCK_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            h = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid
            )
            if not h:
                return False
            ctypes.windll.kernel32.CloseHandle(h)
            return True
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def append_log(job_id: str, line: str, keep_last: int = 60) -> None:
    job = load_job(job_id)
    if not job:
        return
    tail = list(job.get("log_tail") or [])
    tail.append(line)
    if len(tail) > keep_last:
        tail = tail[-keep_last:]
    job["log_tail"] = tail
    save_job(job)


def counts() -> dict:
    """Status counts for dashboard badges."""
    out = {s: 0 for s in STATUSES}
    for j in list_jobs():
        out[j.get("status", "pending")] = out.get(j.get("status", "pending"), 0) + 1
    return out


def retry_job(job_id: str, from_stage: str | None = None) -> dict | None:
    """Requeue a failed/done job. Optionally reset stages from `from_stage` onward.

    - from_stage=None: just re-upload (works if video already produced)
    - from_stage="upload": re-upload only
    - from_stage="voiceover": regenerate voiceover/captions/music/assemble/thumbnail/upload
    - from_stage="broll": regenerate everything except research/draft
    - from_stage="research": full re-run
    """
    import json
    job = load_job(job_id)
    if not job:
        return None

    draft_path = job.get("draft_path")
    if draft_path and from_stage:
        try:
            import json as _json
            from pathlib import Path as _P
            from .state import PipelineState
            p = _P(draft_path)
            draft = _json.loads(p.read_text(encoding="utf-8"))
            state = PipelineState(draft)
            dropped = state.reset_from_stage(from_stage)
            state.save(p)
            append_log(job_id, f"[RETRY] cleared stages: {', '.join(dropped) or '(none)'}")
        except Exception as e:
            append_log(job_id, f"[RETRY] draft reset failed: {e}")

    # Decide where to resume in the queue lifecycle
    if from_stage in (None, "upload"):
        # Video already produced → go to upload slot
        new_status = "produced" if draft_path else "pending"
    else:
        new_status = "pending"

    update_job(
        job_id,
        status=new_status,
        stage=f"Tekrar denenecek ({from_stage or 'upload'})",
        progress_pct=0 if new_status == "pending" else 90,
        error=None,
    )
    append_log(job_id, f"[RETRY] requeued → {new_status} (from_stage={from_stage or 'upload'})")
    try:
        from . import audit as _audit
        _audit.log("job_retried", target=job_id,
                   details={"from_stage": from_stage or "upload", "new_status": new_status})
    except Exception:
        pass
    return load_job(job_id)
