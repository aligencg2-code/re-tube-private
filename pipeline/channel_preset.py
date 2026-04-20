"""Per-channel preset storage.

Each channel directory (SKILL_DIR/channels/<name>/) may carry a `preset.json`
that stores brand-consistent defaults for that channel:
    - script_ai, image, video, tts, music provider keys
    - voice_id (per-language)
    - default lang, format, duration
    - playlist_id (for auto-add, Tier 2 #8)
    - brand tone / context text to prepend to every script prompt

When a user enqueues a job targeting a channel, any missing field on the job
falls back to the channel preset, which itself falls back to the global
config. This keeps each channel's output brand-consistent without forcing
the user to re-set defaults every time.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import SKILL_DIR

CHANNELS_DIR = SKILL_DIR / "channels"


def _preset_path(channel_id: str) -> Path:
    if channel_id == "default":
        return SKILL_DIR / "default_preset.json"
    return CHANNELS_DIR / channel_id / "preset.json"


def load_preset(channel_id: str) -> dict:
    """Return preset dict or empty if none. Never raises."""
    if not channel_id:
        return {}
    p = _preset_path(channel_id)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_preset(channel_id: str, preset: dict) -> None:
    """Persist preset. Creates parent dir if needed."""
    p = _preset_path(channel_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(preset, indent=2, ensure_ascii=False), encoding="utf-8")


def merge_defaults(channel_id: str | None, **overrides) -> dict:
    """Layer overrides on top of channel preset. Non-None overrides win.

    Typical call from the UI:
        job_kwargs = merge_defaults(channel, lang=selected_lang, duration=...)

    Any key not in overrides (or None) picks up the channel preset.
    """
    base = load_preset(channel_id) if channel_id else {}
    out = dict(base)
    for k, v in overrides.items():
        if v is not None and v != "":
            out[k] = v
    return out


# Schema for the settings-page editor — (key, label_tr, label_en, type, options_or_None)
PRESET_FIELDS = [
    ("lang",          "Varsayılan Dil",          "Default Language",  "select", ["tr", "en", "de", "hi"]),
    ("format",        "Varsayılan Format",       "Default Format",    "select", ["shorts", "video"]),
    ("duration",      "Varsayılan Süre",         "Default Duration",  "select", ["short", "3min", "5min", "10min"]),
    ("script_ai",     "Script Sağlayıcısı",      "Script Provider",   "provider", "script_ai"),
    ("image",         "Görsel Sağlayıcısı",      "Image Provider",    "provider", "image"),
    ("video_prov",    "Video Sağlayıcısı",       "Video Provider",    "provider", "video"),
    ("tts",           "TTS Sağlayıcısı",         "TTS Provider",      "provider", "tts"),
    ("music",         "Müzik Sağlayıcısı",       "Music Provider",    "provider", "music"),
    ("voice_id_en",   "İngilizce Ses ID",        "English Voice ID",  "text",   None),
    ("voice_id_tr",   "Türkçe Ses ID",           "Turkish Voice ID",  "text",   None),
    ("context",       "Kanal Bağlamı (script'e eklenir)",
                      "Channel Context (prepended to scripts)",       "textarea", None),
    ("playlist_id",   "YouTube Playlist ID (opsiyonel)",
                      "YouTube Playlist ID (optional)",               "text",   None),
    ("tone",          "Marka Tonu (ciddi, eğlenceli, haber…)",
                      "Brand Tone (serious, playful, news…)",         "text",   None),
]
