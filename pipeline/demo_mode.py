"""1-minute live demo mode — for sales calls.

Ships with curated "wow-factor" demo topics per language that the salesperson
can fire with one click. Spins up a job, returns instantly, and the queue
page shows progress — perfect 60-second demo.

Also bundles a "quick win" preset that picks cheap+fast providers so the
demo doesn't blow the customer's API budget.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone


DEMO_TOPICS_TR = [
    "NASA'nın yeni Ay görevi hakkında kimsenin bilmediği 5 gerçek",
    "Tesla robotaksi lansmanı: tam olarak ne zaman geliyor",
    "Yapay zeka 2026'da hangi meslekleri yok edecek",
    "Bitcoin 150000$ sınırını kırdı — sonraki hedef",
    "Türkiye'nin uzay programı: gerçek rakamlar",
]

DEMO_TOPICS_EN = [
    "5 shocking facts nobody knows about NASA's Artemis 3 Moon mission",
    "Tesla robotaxi launch: exact timeline revealed",
    "Which jobs AI will eliminate in 2026 — surprising findings",
    "Bitcoin breaks $150k — what happens next",
    "Apple Vision Pro 2 leaked specs are unbelievable",
]


# Preset that optimizes for demo speed + low cost
DEMO_PRESET = {
    "script_ai": "claude_haiku",   # fastest + cheapest Claude
    "image": "pexels",              # free stock images
    "tts": "edge_tts",              # free, fast
    "video_prov": "none",           # image-only, no Veo
    "mode": "video",                # skip upload
    "format": "shorts",
    "duration": "short",
    "lang": "tr",
}


def pick_random_topic(lang: str = "tr") -> str:
    pool = DEMO_TOPICS_TR if lang == "tr" else DEMO_TOPICS_EN
    return random.choice(pool)


def is_demo_preset_safe() -> dict:
    """Validate that demo-mode providers are all free/cheap so the salesperson
    doesn't accidentally burn budget on a dozen demos a day."""
    cheap_providers = {
        "claude_cli", "claude_haiku", "gemini_flash", "gpt4o_mini",
        "groq_llama_8b", "deepseek_chat",
        "pexels", "pixabay", "unsplash", "flux_schnell",
        "edge_tts", "openai_tts", "piper", "coqui_xtts", "voixor",
        "none",
    }
    issues = []
    for key, val in DEMO_PRESET.items():
        if key in ("script_ai", "image", "tts", "video_prov") and val not in cheap_providers:
            issues.append(f"{key}={val} is expensive")
    return {"safe": not issues, "issues": issues}


def start_demo(topic: str | None = None, lang: str = "tr",
               channel_id: str | None = None) -> dict:
    """One-click demo. Picks a random topic if none given, enqueues a cheap job."""
    from . import queue as qmod
    t = topic or pick_random_topic(lang)
    job = qmod.enqueue(
        topic=t,
        lang=lang,
        mode=DEMO_PRESET["mode"],
        video_format=DEMO_PRESET["format"],
        duration=DEMO_PRESET["duration"],
        channel=channel_id,
        extra={"demo_mode": True, "demo_started_at": datetime.now(timezone.utc).isoformat()},
    )
    try:
        from . import audit
        audit.log("job_queued", target=job["id"], actor="demo_mode",
                  details={"topic": t[:60], "via": "demo"})
    except Exception:
        pass
    return {
        "job_id": job["id"],
        "topic": t,
        "lang": lang,
        "preset": DEMO_PRESET,
    }
