"""Voice cloning via ElevenLabs Instant Voice Cloning (IVC) + Professional VC.

Customer uploads a 30-90 second sample of their voice. We POST to ElevenLabs
`/v1/voices/add` which returns a `voice_id`. That voice_id becomes selectable
in the TTS provider picker for that customer's channels.

Two modes:
    - Instant (IVC): works on Creator plan and up, ~instant, good quality
    - Professional (PVC): requires manual training by ElevenLabs (hours-days),
      best quality, Pro plan and up

Storage: SKILL_DIR/cloned_voices.json — {voice_id: {name, created, channel,
                                                      sample_duration_sec, model}}
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import SKILL_DIR, _get_key
from .log import log


CLONED_VOICES_FILE = SKILL_DIR / "cloned_voices.json"
ELEVENLABS_BASE = "https://api.elevenlabs.io"


def _load_index() -> dict:
    if not CLONED_VOICES_FILE.exists():
        return {}
    try:
        return json.loads(CLONED_VOICES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_index(index: dict) -> None:
    CLONED_VOICES_FILE.parent.mkdir(parents=True, exist_ok=True)
    CLONED_VOICES_FILE.write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def list_cloned_voices() -> list[dict]:
    """Return locally-registered cloned voices."""
    return [{"voice_id": vid, **meta} for vid, meta in _load_index().items()]


def get_voice(voice_id: str) -> dict | None:
    return _load_index().get(voice_id)


def delete_voice(voice_id: str, *, delete_remote: bool = True) -> dict:
    """Remove locally, optionally also delete from ElevenLabs."""
    index = _load_index()
    if voice_id not in index:
        return {"error": "not_found"}

    meta = index.pop(voice_id)
    _save_index(index)

    remote_deleted = False
    if delete_remote:
        api_key = _get_key("ELEVENLABS_API_KEY")
        if api_key:
            try:
                import requests
                r = requests.delete(
                    f"{ELEVENLABS_BASE}/v1/voices/{voice_id}",
                    headers={"xi-api-key": api_key}, timeout=30,
                )
                remote_deleted = r.ok
            except Exception as e:
                log(f"[voice_clone] remote delete failed: {e}")

    try:
        from . import audit
        audit.log("apikey_removed", target=f"voice:{voice_id}",
                  details={"name": meta.get("name"),
                           "remote_deleted": remote_deleted})
    except Exception:
        pass
    return {"voice_id": voice_id, "removed_local": True,
            "removed_remote": remote_deleted}


def clone_instant(
    *,
    name: str,
    sample_bytes: bytes,
    sample_filename: str = "sample.mp3",
    description: str = "",
    labels: dict | None = None,
    channel_id: str | None = None,
) -> dict:
    """Upload a sample to ElevenLabs IVC. Returns {voice_id, ...}.

    Raises RuntimeError on API failure so callers can surface a clear message.
    """
    api_key = _get_key("ELEVENLABS_API_KEY")
    if not api_key:
        return {"error": "ELEVENLABS_API_KEY not configured"}

    import requests
    files = {
        "files": (sample_filename, sample_bytes, "audio/mpeg"),
    }
    data = {
        "name": name,
        "description": description or f"Cloned voice: {name}",
    }
    if labels:
        data["labels"] = json.dumps(labels)

    try:
        r = requests.post(
            f"{ELEVENLABS_BASE}/v1/voices/add",
            headers={"xi-api-key": api_key, "Accept": "application/json"},
            files=files, data=data, timeout=120,
        )
        if r.status_code not in (200, 201):
            try:
                err_detail = r.json().get("detail", r.text[:300])
            except Exception:
                err_detail = r.text[:300]
            return {"error": f"HTTP {r.status_code}: {err_detail}"}

        result = r.json()
        voice_id = result.get("voice_id")
        if not voice_id:
            return {"error": "No voice_id in response", "raw": result}

        # Register locally
        index = _load_index()
        index[voice_id] = {
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "channel_id": channel_id,
            "sample_size_bytes": len(sample_bytes),
            "mode": "instant",
            "description": description,
        }
        _save_index(index)

        try:
            from . import audit
            audit.log("apikey_added", target=f"voice:{voice_id}",
                      details={"name": name, "mode": "instant",
                               "channel": channel_id})
        except Exception:
            pass
        return {"voice_id": voice_id, "name": name, "mode": "instant"}

    except requests.RequestException as e:
        return {"error": f"Network: {e}"}


def list_remote_voices() -> dict:
    """Query ElevenLabs for ALL voices on the account (built-in + cloned)."""
    api_key = _get_key("ELEVENLABS_API_KEY")
    if not api_key:
        return {"error": "ELEVENLABS_API_KEY not configured"}
    try:
        import requests
        r = requests.get(
            f"{ELEVENLABS_BASE}/v1/voices",
            headers={"xi-api-key": api_key}, timeout=15,
        )
        if not r.ok:
            return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
        return {"voices": r.json().get("voices", [])}
    except Exception as e:
        return {"error": str(e)}


def account_info() -> dict:
    """Query ElevenLabs account usage / plan (for UI display)."""
    api_key = _get_key("ELEVENLABS_API_KEY")
    if not api_key:
        return {"error": "no_api_key"}
    try:
        import requests
        r = requests.get(
            f"{ELEVENLABS_BASE}/v1/user",
            headers={"xi-api-key": api_key}, timeout=10,
        )
        if not r.ok:
            return {"error": f"HTTP {r.status_code}"}
        data = r.json()
        sub = data.get("subscription", {}) or {}
        return {
            "tier": sub.get("tier", "unknown"),
            "character_count": sub.get("character_count"),
            "character_limit": sub.get("character_limit"),
            "can_use_instant_voice_cloning": sub.get("can_use_instant_voice_cloning", False),
            "can_use_professional_voice_cloning": sub.get("can_use_professional_voice_cloning", False),
            "voice_slots_used": len(data.get("voices", [])) if "voices" in data else None,
        }
    except Exception as e:
        return {"error": str(e)}
