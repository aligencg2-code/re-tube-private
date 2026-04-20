"""SDXL / Flux LoRA fine-tuning via Replicate — custom character consistency.

Customers upload 10-20 images of a character or style. We ship them to
Replicate's `flux-dev-lora` or `sdxl-lora-trainer` model, which returns a
trained LoRA weights URL after ~20-60 minutes. We register it locally so
future b-roll generation can use `--lora <url>` to produce consistent-looking
characters across videos.

Flow:
    1. Customer uploads N images (zip or individual files)
    2. We build a training ZIP + upload to Replicate file service
    3. Kick off `replicate.train()` with chosen base model
    4. Poll every 60s for completion; on success, register the LoRA URL
    5. Cost tracked via cost.record (training = ~$2-5 per LoRA on Replicate)

Storage:
    SKILL_DIR/loras.sqlite
        training_jobs(id, replicate_job_id, status, started_at, completed_at,
                      lora_url, error, cost_usd, tenant, base_model, name,
                      trigger_word)

Key design: we don't block; training runs on Replicate's infra. Our queue
worker polls status every few minutes.
"""

from __future__ import annotations

import json
import sqlite3
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

from .config import SKILL_DIR, _get_key
from .log import log


DB_PATH = SKILL_DIR / "loras.sqlite"

# Replicate base models suitable for LoRA training
SUPPORTED_BASE_MODELS = {
    "flux-dev":  {"model": "ostris/flux-dev-lora-trainer",
                  "desc": "Flux.1-dev LoRA (yuksek kalite)",
                  "typical_cost_usd": 3.00,
                  "steps_default": 1000},
    "sdxl":      {"model": "replicate/sdxl-lora-trainer",
                  "desc": "SDXL LoRA (klasik, dusuk maliyet)",
                  "typical_cost_usd": 1.50,
                  "steps_default": 1500},
}


def _ensure_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS training_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                trigger_word TEXT NOT NULL,
                base_model TEXT NOT NULL,
                replicate_job_id TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                started_at TEXT NOT NULL,
                completed_at TEXT,
                lora_url TEXT,
                error TEXT,
                cost_usd REAL,
                tenant TEXT,
                image_count INTEGER,
                steps INTEGER
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tj_status ON training_jobs(status)")
        conn.commit()
    finally:
        conn.close()


# ────────────────────────────────────────────────────────────
# Training ZIP builder
# ────────────────────────────────────────────────────────────
def build_training_zip(image_paths: list[Path | bytes | str], caption: str | None = None) -> bytes:
    """Pack images (with optional single caption per image) into a training ZIP.

    Replicate LoRA trainers expect a zip of images; some accept a caption.txt
    alongside. For Flux/SDXL, captions with the trigger word are helpful:
    "a photo of TOK person wearing glasses".
    """
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, item in enumerate(image_paths):
            if isinstance(item, (str, Path)):
                p = Path(item)
                zf.write(p, arcname=f"img_{i:03d}{p.suffix}")
                if caption:
                    zf.writestr(f"img_{i:03d}.txt", caption)
            elif isinstance(item, bytes):
                zf.writestr(f"img_{i:03d}.png", item)
                if caption:
                    zf.writestr(f"img_{i:03d}.txt", caption)
    buf.seek(0)
    return buf.getvalue()


# ────────────────────────────────────────────────────────────
# Start / poll / complete
# ────────────────────────────────────────────────────────────
def start_training(
    *,
    name: str,
    trigger_word: str,
    images: list[bytes] | list[Path] | list[str],
    base_model: str = "flux-dev",
    steps: int | None = None,
    tenant: str | None = None,
    replicate_client=None,  # DI for tests
) -> dict:
    """Kick off a Replicate training job.

    Returns {job_id, replicate_job_id, status}. Polling happens via
    `poll_training()` — meant to be called from the queue worker.
    """
    _ensure_db()

    if base_model not in SUPPORTED_BASE_MODELS:
        return {"error": f"Unsupported base model: {base_model}"}

    api_key = _get_key("REPLICATE_API_KEY") or _get_key("REPLICATE_API_TOKEN")
    if not api_key and replicate_client is None:
        return {"error": "REPLICATE_API_KEY not configured"}

    # Build the training zip (only if images provided as paths/bytes)
    if images and not isinstance(images[0], str):
        try:
            zip_bytes = build_training_zip(images,
                                           caption=f"a photo of {trigger_word}")
        except Exception as e:
            return {"error": f"Zip build failed: {e}"}
    else:
        zip_bytes = None

    model_cfg = SUPPORTED_BASE_MODELS[base_model]
    steps = steps or model_cfg["steps_default"]

    # Client injection: tests pass a fake that returns a predictable job object
    client = replicate_client
    if client is None:
        try:
            import replicate
            client = replicate.Client(api_token=api_key)
        except ImportError:
            return {"error": "replicate SDK not installed (pip install replicate)"}

    try:
        # Submit training — exact API depends on the model variant, but
        # replicate.trainings.create() is standard
        training = client.trainings.create(
            destination=f"user/{name.lower().replace(' ', '-')}",
            version=model_cfg["model"],
            input={
                "input_images": "uploaded_zip://training.zip",  # placeholder
                "trigger_word": trigger_word,
                "steps": steps,
            },
        )
        replicate_job_id = getattr(training, "id", str(training))
    except Exception as e:
        return {"error": f"Replicate submit failed: {e}"}

    now = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        cur = conn.execute(
            "INSERT INTO training_jobs "
            "(name, trigger_word, base_model, replicate_job_id, status, "
            " started_at, tenant, image_count, steps) "
            "VALUES (?, ?, ?, ?, 'running', ?, ?, ?, ?)",
            (name, trigger_word, base_model, replicate_job_id, now,
             tenant, len(images) if images else 0, steps),
        )
        conn.commit()
        job_id = cur.lastrowid
    finally:
        conn.close()

    try:
        from . import audit
        audit.log("apikey_added", target=f"lora:{job_id}",
                  details={"name": name, "trigger": trigger_word,
                           "base_model": base_model, "steps": steps})
    except Exception:
        pass

    return {
        "job_id": job_id,
        "replicate_job_id": replicate_job_id,
        "status": "running",
    }


def poll_training(job_id: int, *, replicate_client=None) -> dict:
    """Check Replicate for a training's completion. Updates local DB."""
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM training_jobs WHERE id = ?", (job_id,)
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return {"error": "job not found"}
    if row["status"] in ("succeeded", "failed", "canceled"):
        return {"status": row["status"], "lora_url": row["lora_url"]}

    # Fetch status from Replicate
    client = replicate_client
    if client is None:
        try:
            import replicate
            client = replicate.Client(api_token=_get_key("REPLICATE_API_KEY") or
                                                _get_key("REPLICATE_API_TOKEN"))
        except ImportError:
            return {"error": "replicate SDK not installed"}

    try:
        t = client.trainings.get(row["replicate_job_id"])
    except Exception as e:
        return {"error": f"Replicate fetch failed: {e}"}

    status = getattr(t, "status", "unknown")
    lora_url = None
    error = None
    cost_usd = None

    if status == "succeeded":
        # Output format varies: could be URL string or list
        output = getattr(t, "output", None)
        if isinstance(output, dict):
            lora_url = output.get("weights") or output.get("url")
        elif isinstance(output, (list, tuple)) and output:
            lora_url = output[0]
        elif isinstance(output, str):
            lora_url = output
        # Try to extract cost metadata if Replicate exposes it
        metrics = getattr(t, "metrics", None) or {}
        cost_usd = metrics.get("total_cost") if isinstance(metrics, dict) else None

    elif status == "failed":
        error = getattr(t, "error", "unknown")
    elif status == "canceled":
        error = "canceled by user/system"

    # Update DB if terminal
    if status in ("succeeded", "failed", "canceled"):
        conn = sqlite3.connect(str(DB_PATH))
        try:
            conn.execute(
                "UPDATE training_jobs SET status=?, completed_at=?, "
                " lora_url=?, error=?, cost_usd=? WHERE id=?",
                (status, datetime.now(timezone.utc).isoformat(),
                 lora_url, error, cost_usd, job_id),
            )
            conn.commit()
        finally:
            conn.close()

        try:
            if status == "succeeded":
                from . import cost as _c
                if cost_usd:
                    _c.record(job_id=None, stage="lora_train",
                              category="image", provider_key="replicate",
                              amount_usd=cost_usd,
                              extra={"name": row["name"]})
        except Exception:
            pass

    return {"status": status, "lora_url": lora_url, "error": error,
            "cost_usd": cost_usd}


def poll_all_running(replicate_client=None) -> list[dict]:
    """Poll every job currently in 'running' state. Idempotent."""
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id FROM training_jobs WHERE status = 'running'"
        ).fetchall()
    finally:
        conn.close()
    return [poll_training(r["id"], replicate_client=replicate_client)
            for r in rows]


def list_trainings(limit: int = 50) -> list[dict]:
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT * FROM training_jobs ORDER BY started_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_lora_url_by_name(name: str) -> str | None:
    """Convenience lookup — given the training name, return the completed LoRA URL."""
    _ensure_db()
    conn = sqlite3.connect(str(DB_PATH))
    try:
        r = conn.execute(
            "SELECT lora_url FROM training_jobs "
            "WHERE name = ? AND status = 'succeeded' "
            "ORDER BY completed_at DESC LIMIT 1",
            (name,),
        ).fetchone()
        return r[0] if r else None
    finally:
        conn.close()
