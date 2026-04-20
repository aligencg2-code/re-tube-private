"""Background worker that drains the queue.

Start it from the UI or via `python -m pipeline worker`. Only one instance
runs at a time (enforced by queue.acquire_worker_lock). Each job runs
produce then upload (if mode allows) sequentially — so uploads land in
submission order.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from . import queue as qmod
from .log import log


POLL_INTERVAL = 3.0   # seconds between queue scans when idle
MAX_IDLE_LOOPS = 120  # ~6 min idle before worker self-exits (UI will restart)


# Stage triggers mirrored from app.py for progress bar updates
STAGE_MAP = [
    ("Researching topic", 5, "Konu araştırılıyor"),
    ("Claude", 15, "Script üretiliyor"),
    ("Draft saved", 20, "Taslak kaydedildi"),
    ("b-roll frame 1", 25, "Görseller (1/6)"),
    ("b-roll frame 2", 29, "Görseller (2/6)"),
    ("b-roll frame 3", 33, "Görseller (3/6)"),
    ("b-roll frame 4", 37, "Görseller (4/6)"),
    ("b-roll frame 5", 41, "Görseller (5/6)"),
    ("b-roll frame 6", 45, "Görseller (6/6)"),
    ("voiceover", 55, "Seslendirme"),
    ("Whisper", 65, "Altyazılar"),
    ("SRT captions", 70, "Altyazılar kaydedildi"),
    ("music", 75, "Müzik"),
    ("Assembling", 85, "Video birleşiyor"),
    ("thumbnail", 90, "Thumbnail"),
    ("Uploading", 95, "Yükleniyor"),
    ("Done!", 100, "Tamamlandı"),
    ("Live:", 100, "Canlı"),
]


def _detect(line: str):
    for trigger, pct, label in STAGE_MAP:
        if trigger.lower() in line.lower():
            return pct, label
    return None


def _run_stream(cmd: list[str], job_id: str, timeout_s: int = 3600) -> tuple[int, str]:
    proc = subprocess.Popen(
        [sys.executable, "-u", "-m", "pipeline"] + cmd,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(Path(__file__).resolve().parent.parent),
        bufsize=1,
    )
    start = time.time()
    lines: list[str] = []
    try:
        assert proc.stdout is not None
        for raw in proc.stdout:
            line = raw.rstrip()
            if not line:
                continue
            lines.append(line)
            qmod.append_log(job_id, line)

            det = _detect(line)
            if det:
                pct, label = det
                job = qmod.load_job(job_id)
                if job and pct > int(job.get("progress_pct", 0)):
                    job["progress_pct"] = pct
                    job["stage"] = label
                    qmod.save_job(job)

            # cancel signal
            if qmod.is_cancelled(job_id):
                proc.terminate()
                qmod.clear_cancel_flag(job_id)
                return 130, "\n".join(lines)

            if time.time() - start > timeout_s:
                proc.kill()
                lines.append("[TIMEOUT]")
                return 124, "\n".join(lines)
        proc.wait(timeout=60)
        return proc.returncode, "\n".join(lines)
    except Exception as e:
        try:
            proc.kill()
        except Exception:
            pass
        lines.append(f"[WORKER ERROR] {e}")
        return 1, "\n".join(lines)


def _run_produce(job: dict) -> bool:
    """Draft + produce one video. Returns True on success."""
    job_id = job["id"]
    topic = job["topic"]
    lang = job.get("lang", "tr")
    fmt = job.get("format", "shorts")
    dur = job.get("duration", "short")
    force = bool(job.get("force"))
    context = job.get("context", "")

    draft_path = job.get("draft_path")

    if not draft_path:
        # 1) draft
        cmd = [
            "draft",
            "--news", topic,
            "--lang", lang,
            "--format", fmt,
            "--duration", dur,
        ]
        if context:
            cmd += ["--context", context]
        code, out = _run_stream(cmd, job_id, timeout_s=600)
        if code != 0:
            qmod.update_job(job_id, status="failed", error=f"Draft failed (code {code})")
            return False
        # Find newly created draft file
        from .config import DRAFTS_DIR
        candidates = sorted(DRAFTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            qmod.update_job(job_id, status="failed", error="Draft dosyasi olusturulamadi")
            return False
        draft_path = str(candidates[0])
        qmod.update_job(job_id, draft_path=draft_path)

    # 2) produce
    cmd = ["produce", "--draft", draft_path, "--lang", lang]
    if force:
        cmd.append("--force")
    code, _ = _run_stream(cmd, job_id, timeout_s=3600)
    if code != 0:
        qmod.update_job(
            job_id,
            status="failed",
            error=f"Produce failed (code {code})",
        )
        return False
    return True


def _run_upload(job: dict) -> bool:
    job_id = job["id"]
    draft_path = job.get("draft_path")
    if not draft_path:
        qmod.update_job(job_id, status="failed", error="Upload icin draft yok")
        return False
    lang = job.get("lang", "tr")
    cmd = ["upload", "--draft", draft_path, "--lang", lang]

    # Pass through scheduled-publish settings
    publish_at = job.get("publish_at")
    if publish_at:
        cmd += ["--publish-at", publish_at]
    privacy = job.get("privacy_status")
    if privacy and not publish_at:
        cmd += ["--privacy", privacy]
    # Playlist ID from channel preset (stored in job.extra) or directly on job
    playlist_id = (job.get("extra") or {}).get("playlist_id") or job.get("playlist_id")
    if playlist_id:
        cmd += ["--playlist-id", playlist_id]

    code, _ = _run_stream(cmd, job_id, timeout_s=1800)
    if code != 0:
        qmod.update_job(job_id, status="failed", error=f"Upload failed (code {code})")
        return False
    return True


def process_one(job: dict) -> None:
    job_id = job["id"]
    mode = job.get("mode", "full")
    log(f"[worker] start {job_id} mode={mode}")

    # Produce stage
    if mode in ("full", "video"):
        qmod.update_job(job_id, status="producing", stage="Başlatılıyor", progress_pct=1)
        ok = _run_produce(job)
        if not ok:
            return
        qmod.update_job(job_id, status="produced", stage="Üretim tamam", progress_pct=90)
        if mode == "video":
            qmod.update_job(job_id, status="done", stage="Tamamlandı", progress_pct=100)
            return
    elif mode == "draft":
        qmod.update_job(job_id, status="producing", stage="Taslak", progress_pct=10)
        ok = _run_produce(job)  # stops at draft since no produce stage called
        qmod.update_job(job_id, status="done" if ok else "failed",
                        stage="Tamamlandı" if ok else "Hata",
                        progress_pct=100 if ok else job.get("progress_pct", 0))
        return

    # Upload stage (only for mode=full)
    qmod.update_job(job_id, status="uploading", stage="Yükleniyor", progress_pct=95)
    ok = _run_upload(job)
    if ok:
        qmod.update_job(job_id, status="done", stage="Yüklendi", progress_pct=100)


def recover_stuck_jobs() -> int:
    """Reset jobs left in `producing` or `uploading` from a previous crash.

    A job is "stuck" when its status is mid-pipeline but no worker holds the
    lock (or the lock is stale). Such jobs are returned to a re-processable
    state — produce will resume from the last completed stage via state.is_done.

    NOTE: caller is responsible for ensuring no live worker is running. From
    drain_loop we call this *after* acquiring the lock.

    Returns the number of jobs recovered.
    """
    recovered = 0
    for j in qmod.list_jobs(statuses=("producing", "uploading")):
        if j["status"] == "producing":
            qmod.update_job(
                j["id"],
                status="pending",
                stage="Yeniden kuyrukta (çökme sonrası)",
                error=None,
            )
            qmod.append_log(j["id"], "[RECOVERY] worker crashed — re-queued, will resume from last completed stage")
            recovered += 1
        elif j["status"] == "uploading":
            qmod.update_job(
                j["id"],
                status="produced",
                stage="Yükleme tekrar denenecek",
                error=None,
            )
            qmod.append_log(j["id"], "[RECOVERY] upload interrupted — will retry")
            recovered += 1
    if recovered:
        log(f"[worker] recovered {recovered} stuck job(s) from previous crash")
    return recovered


def _run_thumbnail_ab_scan():
    """Rotate thumbnail A/B tests that are due. Runs each idle cycle."""
    try:
        from . import thumbnail_ab, channel_stats, upload as _up
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        def fetch_views(video_id, token_path):
            creds = Credentials.from_authorized_user_file(token_path)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            yt = build("youtube", "v3", credentials=creds)
            r = yt.videos().list(part="statistics", id=video_id).execute()
            items = r.get("items", [])
            if not items:
                return (0, 0)
            s = items[0]["statistics"]
            return (int(s.get("viewCount", 0)), int(s.get("likeCount", 0)))

        def upload_thumb(video_id, thumb_path, token_path):
            creds = Credentials.from_authorized_user_file(token_path)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            yt = build("youtube", "v3", credentials=creds)
            yt.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumb_path, mimetype="image/png"),
            ).execute()

        results = thumbnail_ab.scan_and_rotate_all(
            views_fetcher=fetch_views, uploader=upload_thumb,
        )
        for r in results:
            if r.get("action") == "rotated":
                log(f"[thumb-ab] {r['video_id']}: rotated variant {r['from']} -> {r['to']}")
            elif r.get("action") == "finished":
                log(f"[thumb-ab] {r['video_id']}: finished, winner = variant {r['winner']}")
    except Exception as e:
        log(f"[thumb-ab] scan error (ignored): {e}")


def drain_loop() -> None:
    """Main loop — runs until queue is idle for MAX_IDLE_LOOPS cycles."""
    if not qmod.acquire_worker_lock():
        log("[worker] already running — exiting")
        return

    # Crash recovery runs inside the lock so no other worker interferes
    recover_stuck_jobs()

    idle = 0
    # Thumbnail A/B: scan every 30 min (600 * 3s poll = 30 min)
    thumb_ab_counter = 0
    try:
        while True:
            # 1) Prefer uploads (keeps upload order strict)
            job = qmod.next_produced()
            if job:
                idle = 0
                _run_upload_job(job)
                continue

            # 2) Otherwise produce next pending
            job = qmod.next_pending()
            if job:
                idle = 0
                process_one(job)
                continue

            idle += 1
            thumb_ab_counter += 1
            lora_poll_counter = (thumb_ab_counter * 2) % 200  # ~10 min
            news_scan_counter = (thumb_ab_counter * 3) % 1200  # ~60 min

            if thumb_ab_counter >= 600:  # ~30 min
                thumb_ab_counter = 0
                _run_thumbnail_ab_scan()

            # LoRA training polling — every ~10 min
            if lora_poll_counter == 0:
                try:
                    from . import lora_training
                    lora_training.poll_all_running()
                except Exception as e:
                    log(f"[lora] poll error: {e}")

            # News watcher — every ~60 min
            if news_scan_counter == 0:
                try:
                    from . import news_watcher
                    news_watcher.scan_all()
                except Exception as e:
                    log(f"[news] scan error: {e}")

            # Scheduler tick — every cycle (every 3s) to catch HH:MM exactly
            try:
                from . import scheduler
                scheduler.tick()
            except Exception as e:
                if thumb_ab_counter % 20 == 0:  # only log occasionally
                    log(f"[scheduler] tick error: {e}")

            if idle >= MAX_IDLE_LOOPS:
                log("[worker] idle timeout — exiting")
                return
            time.sleep(POLL_INTERVAL)
    finally:
        qmod.release_worker_lock()


def _run_upload_job(job: dict) -> None:
    """Upload a previously-produced job."""
    job_id = job["id"]
    qmod.update_job(job_id, status="uploading", stage="Yükleniyor", progress_pct=95)
    ok = _run_upload(job)
    if ok:
        qmod.update_job(job_id, status="done", stage="Yüklendi", progress_pct=100)


def main():
    drain_loop()


if __name__ == "__main__":
    main()
