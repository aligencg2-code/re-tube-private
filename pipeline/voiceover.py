"""ElevenLabs TTS + edge-tts fallback (cross-platform)."""

import asyncio
import sys
from pathlib import Path

import requests

from .config import VOICE_ID_EN, VOICE_ID_HI, get_elevenlabs_key, run_cmd
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
    """Generate voiceover via ElevenLabs, with edge-tts/say fallback."""
    voice_id = VOICE_ID_HI if lang == "hi" else VOICE_ID_EN
    api_key = get_elevenlabs_key()

    if not api_key:
        log("No ElevenLabs key — using Edge TTS fallback")
        return _edge_tts_fallback(script, out_dir, lang)

    log(f"Generating {lang} voiceover via ElevenLabs...")
    out_path = out_dir / f"voiceover_{lang}.mp3"

    try:
        audio_bytes = _call_elevenlabs(script, voice_id, api_key)
        out_path.write_bytes(audio_bytes)
        log(f"Voiceover saved: {out_path.name}")
        return out_path
    except Exception as e:
        log(f"ElevenLabs failed: {e} — using Edge TTS fallback")
        return _edge_tts_fallback(script, out_dir, lang)
