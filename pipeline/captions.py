"""Whisper word-level timestamps + ASS subtitle generation + Pillow fallback."""

from pathlib import Path

from .log import log


def _has_ass_filter() -> bool:
    """Check if ffmpeg has libass (for ASS subtitle burn-in)."""
    import subprocess
    try:
        r = subprocess.run(
            ["ffmpeg", "-filters"],
            capture_output=True, text=True, timeout=5,
        )
        return "ass" in r.stdout
    except Exception:
        return False


def _whisper_word_timestamps(audio_path: Path, lang: str = "en") -> list[dict]:
    """Get word-level timestamps. Tries providers in order:

      1. openai-whisper (local) — if installed
      2. Groq Whisper API — if GROQ_API_KEY set (ultra-fast, free tier)
      3. OpenAI Whisper API — if OPENAI_API_KEY set
      4. Deepgram — if DEEPGRAM_API_KEY set

    Returns list of {"word": str, "start": float, "end": float}.
    Empty list if no provider available.
    """
    # --- Attempt 1: Local whisper (fastest if installed, offline-friendly) ---
    words = _try_local_whisper(audio_path, lang)
    if words:
        return words

    # --- Attempt 2: Groq Whisper API (fast, cheap) ---
    words = _try_groq_whisper(audio_path, lang)
    if words:
        return words

    # --- Attempt 3: OpenAI Whisper API ---
    words = _try_openai_whisper_api(audio_path, lang)
    if words:
        return words

    # --- Attempt 4: Deepgram ---
    words = _try_deepgram(audio_path, lang)
    if words:
        return words

    log("No caption provider available (install 'openai-whisper' pip paketi veya "
        "GROQ_API_KEY / OPENAI_API_KEY / DEEPGRAM_API_KEY ayarlayin)")
    return []


def _try_local_whisper(audio_path: Path, lang: str) -> list[dict]:
    """Try local openai-whisper. Returns empty list if not available."""
    try:
        import whisper
    except ImportError:
        return []

    # Use 'turbo' for speed+quality, 'medium' fallback for lower VRAM
    model_name = "turbo"
    log(f"Running local Whisper ({model_name}) for word-level timestamps...")
    try:
        model = whisper.load_model(model_name)
    except Exception:
        model_name = "medium"
        log(f"Turbo unavailable, falling back to {model_name}")
        try:
            model = whisper.load_model(model_name)
        except Exception as e:
            log(f"Local whisper failed: {e}")
            return []

    try:
        result = model.transcribe(
            str(audio_path),
            language=lang[:2],
            word_timestamps=True,
            condition_on_previous_text=True,
            temperature=0.0,
        )
    except Exception as e:
        log(f"Local whisper transcribe failed: {e}")
        return []

    words = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            words.append({
                "word": w["word"].strip(),
                "start": w["start"],
                "end": w["end"],
            })
    log(f"Local whisper → {len(words)} word timestamps.")
    return words


def _try_groq_whisper(audio_path: Path, lang: str) -> list[dict]:
    """Groq provides free Whisper Large v3 with word timestamps.
    Very fast (~10x faster than OpenAI). Requires GROQ_API_KEY.
    """
    from .config import _get_key
    api_key = _get_key("GROQ_API_KEY")
    if not api_key:
        return []
    try:
        import requests
        log("Running Groq Whisper API for word-level timestamps...")
        with open(audio_path, "rb") as f:
            r = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (audio_path.name, f, "audio/mpeg")},
                data={
                    "model": "whisper-large-v3",
                    "language": lang[:2],
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": "word",
                },
                timeout=120,
            )
        if not r.ok:
            log(f"Groq whisper failed: {r.status_code} {r.text[:200]}")
            return []
        data = r.json()
        words = [
            {"word": w["word"].strip(), "start": w["start"], "end": w["end"]}
            for w in data.get("words", [])
        ]
        log(f"Groq whisper → {len(words)} word timestamps.")
        return words
    except Exception as e:
        log(f"Groq whisper error: {e}")
        return []


def _try_openai_whisper_api(audio_path: Path, lang: str) -> list[dict]:
    """OpenAI's Whisper API. Paid but reliable. Requires OPENAI_API_KEY."""
    from .config import _get_key
    api_key = _get_key("OPENAI_API_KEY")
    if not api_key:
        return []
    try:
        import requests
        log("Running OpenAI Whisper API for word-level timestamps...")
        with open(audio_path, "rb") as f:
            r = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (audio_path.name, f, "audio/mpeg")},
                data={
                    "model": "whisper-1",
                    "language": lang[:2],
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": "word",
                },
                timeout=180,
            )
        if not r.ok:
            log(f"OpenAI whisper failed: {r.status_code} {r.text[:200]}")
            return []
        data = r.json()
        words = [
            {"word": w["word"].strip(), "start": w["start"], "end": w["end"]}
            for w in data.get("words", [])
        ]
        log(f"OpenAI whisper → {len(words)} word timestamps.")
        return words
    except Exception as e:
        log(f"OpenAI whisper error: {e}")
        return []


def _try_deepgram(audio_path: Path, lang: str) -> list[dict]:
    """Deepgram Nova-3 with word timestamps."""
    from .config import _get_key
    api_key = _get_key("DEEPGRAM_API_KEY")
    if not api_key:
        return []
    try:
        import requests
        log("Running Deepgram Nova-3 for word-level timestamps...")
        with open(audio_path, "rb") as f:
            audio_data = f.read()
        r = requests.post(
            f"https://api.deepgram.com/v1/listen?model=nova-3&language={lang[:2]}&punctuate=true",
            headers={
                "Authorization": f"Token {api_key}",
                "Content-Type": "audio/mpeg",
            },
            data=audio_data,
            timeout=120,
        )
        if not r.ok:
            log(f"Deepgram failed: {r.status_code} {r.text[:200]}")
            return []
        data = r.json()
        words = []
        for alt in data.get("results", {}).get("channels", [{}])[0].get("alternatives", []):
            for w in alt.get("words", []):
                words.append({
                    "word": w.get("punctuated_word", w["word"]),
                    "start": w["start"],
                    "end": w["end"],
                })
        log(f"Deepgram → {len(words)} word timestamps.")
        return words
    except Exception as e:
        log(f"Deepgram error: {e}")
        return []


def _group_words(words: list[dict], group_size: int = 4) -> list[list[dict]]:
    """Group words into chunks of group_size for caption display."""
    groups = []
    for i in range(0, len(words), group_size):
        groups.append(words[i:i + group_size])
    return groups


def _format_ass_time(seconds: float) -> str:
    """Format seconds to ASS timestamp: H:MM:SS.cc (centiseconds)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int((seconds % 1) * 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _generate_ass(words: list[dict], output_path: Path, video_width: int = 1080, video_height: int = 1920):
    """Generate ASS subtitle file with word-by-word color highlighting.

    White text for inactive words, yellow for current word.
    Semi-transparent background, positioned at lower third (~70% down).
    """
    # ASS header
    margin_v = int(video_height * 0.25)  # ~75% down from top = 25% from bottom
    header = f"""[Script Info]
Title: Pipeline Captions
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,3,3,0,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    groups = _group_words(words)
    events = []

    for group in groups:
        if not group:
            continue

        group_start = group[0]["start"]
        group_end = group[-1]["end"]

        # For each word in the group being active, emit one dialogue line
        for active_idx, active_word in enumerate(group):
            start = active_word["start"]
            end = active_word["end"]

            # Build text with override tags: yellow for active, white for rest
            parts = []
            for j, w in enumerate(group):
                if j == active_idx:
                    # Yellow, bold, slightly larger
                    parts.append(f"{{\\c&H00FFFF&\\b1\\fs80}}{w['word']}{{\\r}}")
                else:
                    parts.append(w["word"])

            text = " ".join(parts)
            events.append(
                f"Dialogue: 0,{_format_ass_time(start)},{_format_ass_time(end)},Default,,0,0,0,,{text}"
            )

    output_path.write_text(header + "\n".join(events), encoding="utf-8")
    log(f"ASS captions saved: {output_path.name}")
    return output_path


def _generate_srt(words: list[dict], output_path: Path) -> Path:
    """Generate standard SRT file from word timestamps."""
    groups = _group_words(words)
    lines = []

    for i, group in enumerate(groups, 1):
        if not group:
            continue
        start = group[0]["start"]
        end = group[-1]["end"]
        text = " ".join(w["word"] for w in group)

        start_ts = _srt_time(start)
        end_ts = _srt_time(end)
        lines.append(f"{i}\n{start_ts} --> {end_ts}\n{text}\n")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    log(f"SRT captions saved: {output_path.name}")
    return output_path


def _srt_time(seconds: float) -> str:
    """Format seconds to SRT timestamp: HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_captions(audio_path: Path, work_dir: Path, lang: str = "en") -> dict:
    """Generate captions: ASS (for burn-in) + SRT (for YouTube upload).

    Returns dict with keys: srt_path, ass_path, words (for music ducking).
    """
    words = _whisper_word_timestamps(audio_path, lang)

    result = {"words": words}

    if not words:
        log("No word timestamps — video will ship without burned-in captions.")
        log("  Hint: Install 'pip install openai-whisper' OR set GROQ_API_KEY "
            "(free tier) / OPENAI_API_KEY for cloud-based captions.")
        return result

    # Generate SRT
    srt_path = work_dir / f"captions_{lang}.srt"
    _generate_srt(words, srt_path)
    result["srt_path"] = str(srt_path)

    # Generate ASS for burn-in
    ass_path = work_dir / f"captions_{lang}.ass"
    _generate_ass(words, ass_path)
    result["ass_path"] = str(ass_path)

    return result
