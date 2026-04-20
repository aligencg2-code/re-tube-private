"""Viral potential scoring — predict how well a video topic will perform.

Score = weighted blend of:
  1. TITLE_HOOK      — strong hook words, curiosity gaps, numbers ("5 things")
  2. TITLE_LENGTH    — 40-60 chars optimal for YouTube preview
  3. EMOTION_WORDS   — anger, shock, curiosity, humor signals
  4. NUMBER_IN_TITLE — listicles perform well
  5. TOPIC_TRENDING  — similar topic in recent topic_memory = saturation, -penalty
  6. LLM_JUDGEMENT   — Claude rates viral potential (0-100) with reasoning

Output:
    {
        "score": 0-100,
        "tier": "low"|"medium"|"high"|"viral",
        "breakdown": {signal: value, ...},
        "reasoning": "...",
        "recommendations": ["...", "..."],
    }

Philosophy: be a conservative predictor. Most videos are "medium"; mark
something "viral" only when multiple strong signals align.
"""

from __future__ import annotations

import json
import re
from typing import Any


# Hook / curiosity / emotion word lexicons — lowercased matches
HOOK_WORDS = {
    # English
    "shocking", "surprising", "hidden", "secret", "nobody", "everyone",
    "never", "always", "finally", "actually", "revealed", "exposed",
    "breaking", "urgent", "warning",
    # Turkish
    "şok", "sok", "gizli", "kimsenin", "herkes", "asla", "nihayet",
    "aslında", "ortaya", "acil", "dikkat", "uyari", "uyarı",
}
EMOTION_WORDS = {
    # Curiosity/intrigue
    "why", "how", "what", "when", "where", "niçin", "neden", "nasıl", "ne",
    # Shock/anger
    "crazy", "insane", "wild", "angry", "çılgın", "çilgin", "delirmiş",
    # Humor/light
    "funny", "hilarious", "komik",
}
POWER_WORDS = {
    "billion", "million", "record", "first", "last", "biggest", "smallest",
    "milyar", "milyon", "rekor", "ilk", "son", "en büyük",
}


# ────────────────────────────────────────────────────────────
# Individual signal scorers (each returns 0-100)
# ────────────────────────────────────────────────────────────
def score_title_hook(title: str) -> tuple[int, dict]:
    tl = (title or "").lower()
    hook_hits = sum(1 for w in HOOK_WORDS if w in tl)
    power_hits = sum(1 for w in POWER_WORDS if w in tl)
    total = hook_hits + power_hits
    score = min(100, total * 25)  # cap at 4 hits = 100
    return score, {"hook_words": hook_hits, "power_words": power_hits}


def score_title_length(title: str) -> tuple[int, dict]:
    n = len(title or "")
    if n == 0:
        return 0, {"length": 0, "note": "empty"}
    # Sweet spot: 40-60 chars
    if 40 <= n <= 60:
        return 100, {"length": n, "note": "optimal"}
    if 30 <= n <= 70:
        return 75, {"length": n, "note": "good"}
    if 20 <= n <= 90:
        return 50, {"length": n, "note": "acceptable"}
    return 20, {"length": n, "note": "too short" if n < 20 else "too long"}


def score_emotion(title: str) -> tuple[int, dict]:
    tl = (title or "").lower()
    hits = sum(1 for w in EMOTION_WORDS if w in tl)
    # 1 word = decent, 2+ = strong
    score = min(100, hits * 40)
    return score, {"emotion_hits": hits}


def score_number_in_title(title: str) -> tuple[int, dict]:
    # Numbers or listicle patterns
    has_digit = bool(re.search(r"\d+", title or ""))
    listicle = bool(re.search(r"\b(\d+)\s*(things|ways|reasons|facts|tips|şey|yol|sebep|ipucu)\b",
                               (title or "").lower()))
    score = 100 if listicle else (60 if has_digit else 0)
    return score, {"has_digit": has_digit, "listicle": listicle}


def score_topic_saturation(topic: str) -> tuple[int, dict]:
    """Penalize if we've done this topic recently (audience fatigue proxy)."""
    try:
        from . import topic_memory
        hits = topic_memory.find_similar(topic, threshold=0.5, days=30, limit=5)
        if not hits:
            return 100, {"recent_similar": 0, "note": "fresh topic"}
        # The higher the similarity, the bigger the penalty
        worst = max(h["similarity"] for h in hits)
        score = max(0, int(100 - worst * 100))
        return score, {
            "recent_similar": len(hits),
            "max_similarity": round(worst, 2),
            "note": f"{len(hits)} recent similar topic(s)",
        }
    except Exception:
        return 75, {"note": "topic memory unavailable"}


def score_llm_judgement(topic: str, title: str, duration: str = "short") -> tuple[int, dict]:
    """Ask the configured script_ai provider to rate viral potential.

    Expected response (JSON):
        {"score": 0-100, "reasoning": "...", "strengths": [...], "weaknesses": [...]}

    On any failure, falls back to a neutral 50.
    """
    try:
        from .draft import _call_script_ai
        prompt = (
            "You are a YouTube growth analyst. Rate the viral potential of "
            "this video idea for the algorithm on a 0-100 scale. Be conservative: "
            "most ideas should score 30-60, only genuinely viral-worthy hooks score 80+.\n\n"
            f"Topic: {topic}\n"
            f"Title: {title}\n"
            f"Format: {duration}\n\n"
            'Reply with JSON only: {"score": 0-100, "reasoning": "one short sentence", '
            '"strengths": ["..."], "weaknesses": ["..."]}'
        )
        raw = _call_script_ai(prompt).strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.startswith("json\n"):
                raw = raw[5:]
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            return 50, {"note": "LLM returned non-JSON", "raw": raw[:100]}
        data = json.loads(raw[start:end + 1])
        s = int(max(0, min(100, data.get("score", 50))))
        return s, {
            "reasoning": str(data.get("reasoning", ""))[:200],
            "strengths": data.get("strengths", [])[:3],
            "weaknesses": data.get("weaknesses", [])[:3],
        }
    except Exception as e:
        return 50, {"note": f"LLM unavailable: {e}", "fallback": True}


# ────────────────────────────────────────────────────────────
# Aggregate scorer — weighted blend
# ────────────────────────────────────────────────────────────
# Weights chosen so no single signal dominates; LLM gets a bit more weight
# because it's holistic.
SIGNAL_WEIGHTS = {
    "title_hook":        0.15,
    "title_length":      0.10,
    "emotion":           0.10,
    "number_in_title":   0.10,
    "topic_saturation":  0.20,
    "llm_judgement":     0.35,
}


def score(
    *,
    topic: str,
    title: str | None = None,
    duration: str = "short",
    use_llm: bool = True,
) -> dict:
    """Compute the viral potential score. `title` defaults to `topic`."""
    title = title or topic
    breakdown: dict[str, Any] = {}
    weighted_sum = 0.0
    weight_total = 0.0

    def _add(name, fn, weight):
        nonlocal weighted_sum, weight_total
        s, meta = fn()
        breakdown[name] = {"score": s, **meta}
        weighted_sum += s * weight
        weight_total += weight

    _add("title_hook",      lambda: score_title_hook(title),      SIGNAL_WEIGHTS["title_hook"])
    _add("title_length",    lambda: score_title_length(title),    SIGNAL_WEIGHTS["title_length"])
    _add("emotion",         lambda: score_emotion(title),         SIGNAL_WEIGHTS["emotion"])
    _add("number_in_title", lambda: score_number_in_title(title), SIGNAL_WEIGHTS["number_in_title"])
    _add("topic_saturation",lambda: score_topic_saturation(topic),SIGNAL_WEIGHTS["topic_saturation"])

    if use_llm:
        _add("llm_judgement", lambda: score_llm_judgement(topic, title, duration),
             SIGNAL_WEIGHTS["llm_judgement"])

    final = int(weighted_sum / weight_total) if weight_total else 50

    # Tier
    if final >= 80:
        tier = "viral"
    elif final >= 65:
        tier = "high"
    elif final >= 45:
        tier = "medium"
    else:
        tier = "low"

    # Recommendations — driven by the weakest signals
    recommendations: list[str] = []
    sorted_signals = sorted(breakdown.items(), key=lambda kv: kv[1]["score"])
    for name, meta in sorted_signals[:2]:
        s = meta["score"]
        if s >= 70:
            break
        if name == "title_hook" and s < 50:
            recommendations.append("Başlığa hook kelime ekle: 'Kimsenin...', 'Aslında...', 'Şok...'")
        elif name == "title_length":
            n = meta.get("length", 0)
            if n < 30:
                recommendations.append(f"Başlık çok kısa ({n} karakter) — 40-60 ideal")
            elif n > 70:
                recommendations.append(f"Başlık çok uzun ({n} karakter) — 40-60 ideal")
        elif name == "emotion" and s < 40:
            recommendations.append("Duygu sözcüğü yok (neden/nasıl/çılgın vs.) — biraz merak yarat")
        elif name == "number_in_title" and s == 0:
            recommendations.append("Sayı veya listicle dene: '5 gerçek...', '3 sebep...'")
        elif name == "topic_saturation" and s < 50:
            recommendations.append("Yakın zamanda benzer konu yapmışsın — farklı açı/kanca bul")
        elif name == "llm_judgement" and s < 50:
            weaknesses = meta.get("weaknesses", [])
            if weaknesses:
                recommendations.append(f"AI zayıflık: {weaknesses[0]}")

    # LLM reasoning rolls up to the top-level if available
    reasoning = ""
    if "llm_judgement" in breakdown and breakdown["llm_judgement"].get("reasoning"):
        reasoning = breakdown["llm_judgement"]["reasoning"]

    return {
        "score": final,
        "tier": tier,
        "breakdown": breakdown,
        "reasoning": reasoning,
        "recommendations": recommendations,
    }
