"""TTS voiceover — ElevenLabs, OpenAI TTS, edge-tts fallback (cross-platform)."""

import asyncio
import sys
from pathlib import Path

import requests

from .config import VOICE_ID_EN, VOICE_ID_HI, get_elevenlabs_key, _get_key, run_cmd
from .log import log
from .retry import with_retry


@with_retry(max_retries=3, base_delay=2.0)
def _call_elevenlabs(script: str, voice_id: str, api_key: str) -> bytes:
    """Call ElevenLabs TTS API and return audio bytes."""
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "text": script,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.4,
                "similarity_boost": 0.85,
                "style": 0.3,
                "use_speaker_boost": True,
            },
        },
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:200]}")
    return r.content


def _edge_tts_fallback(script: str, out_dir: Path, lang: str = "en") -> Path:
    """Microsoft Edge TTS fallback — free, high quality, cross-platform."""
    import edge_tts

    mp3_path = out_dir / f"voiceover_edge_{lang}.mp3"
    voice_map = {
        "en": "en-US-ChristopherNeural",
        "de": "de-DE-ConradNeural",
        "hi": "hi-IN-MadhurNeural",
        "tr": "tr-TR-AhmetNeural",
    }
    voice = voice_map.get(lang, "en-US-ChristopherNeural")

    async def _generate():
        communicate = edge_tts.Communicate(script, voice)
        await communicate.save(str(mp3_path))

    asyncio.run(_generate())
    log(f"Edge TTS voiceover saved: {mp3_path.name}")
    return mp3_path


@with_retry(max_retries=2, base_delay=2.0)
def _call_openai_tts(script: str, out_path: Path, model: str = "tts-1", voice: str = "alloy"):
    """Call OpenAI TTS API."""
    api_key = _get_key("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OpenAI API key not configured")

    r = requests.post(
        "https://api.openai.com/v1/audio/speech",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "input": script, "voice": voice, "response_format": "mp3"},
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(f"OpenAI TTS {r.status_code}: {r.text[:200]}")
    out_path.write_bytes(r.content)
    return out_path


def _say_fallback(script: str, out_dir: Path) -> Path:
    """macOS 'say' fallback TTS."""
    out_path = out_dir / "voiceover_say.aiff"
    mp3_path = out_dir / "voiceover_say.mp3"
    run_cmd(["say", "-o", str(out_path), script])
    run_cmd([
        "ffmpeg", "-i", str(out_path), "-acodec", "libmp3lame",
        str(mp3_path), "-y", "-loglevel", "quiet",
    ])
    return mp3_path


def generate_voiceover(script: str, out_dir: Path, lang: str = "en") -> Path:
    """Generate voiceover based on config provider selection.

    Providers:
    - elevenlabs / elevenlabs_flash: ElevenLabs TTS
    - openai_tts / openai_tts_hd: OpenAI TTS
    - edge_tts: Microsoft Edge TTS (free)
    - fallback: Edge TTS
    """
    from .config import load_config, PROVIDERS

    config = load_config()
    tts_provider = config.get("providers", {}).get("tts", "edge_tts")
    provider_info = PROVIDERS.get("tts", {}).get(tts_provider, {})

    voice_id = VOICE_ID_HI if lang == "hi" else VOICE_ID_EN

    # ElevenLabs providers
    if tts_provider in ("elevenlabs", "elevenlabs_flash"):
        api_key = get_elevenlabs_key()
        if api_key:
            log(f"Generating {lang} voiceover via {provider_info.get('name', 'ElevenLabs')}...")
            out_path = out_dir / f"voiceover_{lang}.mp3"
            try:
                audio_bytes = _call_elevenlabs(script, voice_id, api_key)
                out_path.write_bytes(audio_bytes)
                log(f"Voiceover saved: {out_path.name}")
                return out_path
            except Exception as e:
                log(f"ElevenLabs failed: {e} — falling back to Edge TTS")
        else:
            log("No ElevenLabs key — falling back to Edge TTS")
        return _edge_tts_fallback(script, out_dir, lang)

    # OpenAI TTS providers
    if tts_provider in ("openai_tts", "openai_tts_hd"):
        model = provider_info.get("model", "tts-1")
        voice = "alloy"  # Default voice
        out_path = out_dir / f"voiceover_{lang}.mp3"
        try:
            log(f"Generating {lang} voiceover via {provider_info.get('name', 'OpenAI TTS')}...")
            _call_openai_tts(script, out_path, model=model, voice=voice)
            log(f"Voiceover saved: {out_path.name}")
            return out_path
        except Exception as e:
            log(f"OpenAI TTS failed: {e} — falling back to Edge TTS")
            return _edge_tts_fallback(script, out_dir, lang)

    # Edge TTS (default / explicit)
    log(f"Generating {lang} voiceover via Edge TTS...")
    return _edge_tts_fallback(script, out_dir, lang)
