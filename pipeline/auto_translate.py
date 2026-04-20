"""Auto-translation fan-out — one video → multiple language versions.

Given a completed draft + video in language X, translate script + metadata
to N target languages and enqueue produce jobs for each. Uploaded to the
customer-configured per-language channel (if any).

Flow:
    1. Load original draft (must be produced at least once)
    2. For each target lang:
        - Translate script, title, description, tags via the configured
          script_ai provider
        - Write a NEW draft JSON (copy of original + translated fields)
        - Enqueue a produce job with mode=video (no new research)
    3. Track the fan-out in SKILL_DIR/translation_jobs.jsonl for audit

This is intentionally non-destructive — the original draft is never modified.

Channel mapping (optional): customer can set in their preset:
    {"lang_channel_map": {"en": "channel_id_a", "de": "channel_id_b"}}
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DRAFTS_DIR, SKILL_DIR
from .log import log


TRANSLATIONS_LOG = SKILL_DIR / "translation_jobs.jsonl"

# Default supported target languages + native name for LLM prompts
SUPPORTED_LANGS = {
    "en": "English",
    "tr": "Türkçe (Turkish)",
    "de": "Deutsch (German)",
    "hi": "हिन्दी (Hindi)",
    "es": "Español (Spanish)",
    "fr": "Français (French)",
    "pt": "Português (Portuguese)",
    "ar": "العربية (Arabic)",
    "ja": "日本語 (Japanese)",
    "zh": "中文 (Chinese)",
}


def _translate_fields(
    *, source_lang: str, target_lang: str, fields: dict,
) -> dict:
    """Call script_ai to translate a bundle of fields at once.

    Returns a dict with the same keys as `fields`. On LLM failure, returns
    the original untranslated fields — the caller should treat that as a
    soft failure and skip enqueueing.
    """
    target_name = SUPPORTED_LANGS.get(target_lang, target_lang)

    try:
        from .draft import _call_script_ai
    except Exception as e:
        log(f"[auto_translate] cannot import script_ai: {e}")
        return fields

    prompt = (
        f"Translate the following YouTube video fields from "
        f"{SUPPORTED_LANGS.get(source_lang, source_lang)} to {target_name}. "
        "Keep the tone, keep hook power, preserve proper nouns as-is. "
        "Reply with JSON only, no markdown fences, one key per input field.\n\n"
        + "INPUT:\n"
        + json.dumps(fields, ensure_ascii=False, indent=2)
        + "\n\nOUTPUT (JSON):"
    )

    try:
        raw = _call_script_ai(prompt).strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json\n"):
                raw = raw[5:]
            raw = raw.strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("No JSON object in response")
        result = json.loads(raw[start:end + 1])
        # Ensure all original keys present
        for k in fields:
            if k not in result:
                result[k] = fields[k]
        return result
    except Exception as e:
        log(f"[auto_translate] LLM failed for {target_lang}: {e}")
        return dict(fields)


def fan_out(
    *,
    source_draft_path: str,
    target_langs: list[str],
    lang_channel_map: dict[str, str] | None = None,
    video_format: str = "shorts",
    duration: str = "short",
) -> dict:
    """Translate + enqueue one source draft into N target languages.

    Returns:
        {"created_drafts": [...paths], "queued_jobs": [...ids], "errors": [...]}
    """
    src = Path(source_draft_path)
    if not src.exists():
        return {"error": f"source draft not found: {src}"}

    try:
        original = json.loads(src.read_text(encoding="utf-8"))
    except Exception as e:
        return {"error": f"cannot parse draft: {e}"}

    source_lang = original.get("lang", "en")
    lang_channel_map = lang_channel_map or {}
    created_drafts: list[str] = []
    queued_jobs: list[str] = []
    errors: list[str] = []

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    for tgt in target_langs:
        if tgt == source_lang:
            continue  # skip same language
        if tgt not in SUPPORTED_LANGS:
            errors.append(f"Unsupported language: {tgt}")
            continue

        # 1) Build translation input (only fields that need translating)
        to_translate = {
            "script": original.get("script", ""),
            "youtube_title": original.get("youtube_title", ""),
            "youtube_description": original.get("youtube_description", ""),
        }
        translated = _translate_fields(
            source_lang=source_lang, target_lang=tgt, fields=to_translate,
        )

        # 2) Write a new draft JSON
        import time as _t
        new_id = f"{original.get('job_id', 'x')}_{tgt}_{int(_t.time())}"
        new_draft = dict(original)
        new_draft.update({
            "job_id": new_id,
            "lang": tgt,
            "script": translated["script"],
            "youtube_title": translated["youtube_title"],
            "youtube_description": translated["youtube_description"],
            "format": video_format,
            "duration": duration,
            # CRITICAL: reset pipeline state so the produce step regenerates
            # voice/captions/etc with the new script
            "_pipeline_state": {
                "research": original.get("_pipeline_state", {}).get("research", {}),
                "draft": {"status": "done",
                          "timestamp": datetime.now(timezone.utc).isoformat()},
            },
            # broll_prompts stay the same (visuals are language-agnostic)
            "translation_source": original.get("job_id"),
        })
        out_path = DRAFTS_DIR / f"{new_id}.json"
        out_path.write_text(
            json.dumps(new_draft, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        created_drafts.append(str(out_path))

        # 3) Enqueue produce job
        try:
            from . import queue as qmod
            channel_id = lang_channel_map.get(tgt)
            job = qmod.enqueue(
                topic=translated.get("youtube_title", "") or original.get("news", ""),
                lang=tgt,
                mode="video",  # skip research/draft, go straight to produce
                video_format=video_format,
                duration=duration,
                channel=channel_id,
                draft_path=str(out_path),
            )
            queued_jobs.append(job["id"])
        except Exception as e:
            errors.append(f"queue enqueue failed for {tgt}: {e}")

    # Log to JSONL
    try:
        TRANSLATIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(TRANSLATIONS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat(),
                "source_draft": str(src),
                "source_lang": source_lang,
                "target_langs": target_langs,
                "created_drafts": created_drafts,
                "queued_jobs": queued_jobs,
                "errors": errors,
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass

    try:
        from . import audit
        audit.log("job_queued", target=",".join(queued_jobs),
                  details={"translations": target_langs,
                           "source": original.get("job_id")})
    except Exception:
        pass

    return {
        "created_drafts": created_drafts,
        "queued_jobs": queued_jobs,
        "errors": errors,
    }


def history(limit: int = 50) -> list[dict]:
    """Return recent fan-out events from the log."""
    if not TRANSLATIONS_LOG.exists():
        return []
    lines = TRANSLATIONS_LOG.read_text(encoding="utf-8").splitlines()[-limit:]
    out = []
    for line in reversed(lines):
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out
