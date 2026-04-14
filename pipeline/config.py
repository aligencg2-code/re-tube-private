"""Key resolution, paths, constants, and setup wizard."""

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────
# Skill home directory — all data lives here
# ─────────────────────────────────────────────────────
SKILL_DIR = Path.home() / ".youtube-shorts-pipeline"
DRAFTS_DIR = SKILL_DIR / "drafts"
MEDIA_DIR = SKILL_DIR / "media"
LOGS_DIR = SKILL_DIR / "logs"
CONFIG_FILE = SKILL_DIR / "config.json"

# ─────────────────────────────────────────────────────
# Video constants
# ─────────────────────────────────────────────────────
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920

FORMATS = {
    "shorts": {"width": 1080, "height": 1920, "aspect": "9:16"},
    "video":  {"width": 1920, "height": 1080, "aspect": "16:9"},
}

DURATIONS = {
    "short":  {"words": 180,  "seconds": 70,  "frames": 6,  "label": "Short (~70s)"},
    "3min":   {"words": 500,  "seconds": 180, "frames": 10, "label": "3 min"},
    "5min":   {"words": 800,  "seconds": 300, "frames": 15, "label": "5 min"},
    "10min":  {"words": 1500, "seconds": 600, "frames": 25, "label": "10 min"},
}

# ─────────────────────────────────────────────────────
# Provider catalog with pricing (per 60s video estimate)
# ─────────────────────────────────────────────────────
PROVIDERS = {
    "script_ai": {
        "claude_cli":       {"name": "Claude CLI (Max)",      "cost_60s": 0.00,   "model": None,                    "needs_key": None,              "tier": "free"},
        "claude_sonnet":    {"name": "Claude Sonnet 4.6",     "cost_60s": 0.004,  "model": "claude-sonnet-4-6",     "needs_key": "ANTHROPIC_API_KEY", "tier": "premium"},
        "claude_haiku":     {"name": "Claude Haiku 4.5",      "cost_60s": 0.001,  "model": "claude-haiku-4-5-20251001", "needs_key": "ANTHROPIC_API_KEY", "tier": "budget"},
        "gemini_flash":     {"name": "Gemini 2.5 Flash",      "cost_60s": 0.001,  "model": "gemini-2.5-flash",      "needs_key": "GEMINI_API_KEY",  "tier": "budget"},
        "gemini_pro":       {"name": "Gemini 3 Pro",          "cost_60s": 0.003,  "model": "gemini-3-pro",          "needs_key": "GEMINI_API_KEY",  "tier": "mid"},
        "gpt4o_mini":       {"name": "GPT-4o Mini",           "cost_60s": 0.0001, "model": "gpt-4o-mini",           "needs_key": "OPENAI_API_KEY",  "tier": "cheapest"},
        "gpt4o":            {"name": "GPT-4o",                "cost_60s": 0.003,  "model": "gpt-4o",                "needs_key": "OPENAI_API_KEY",  "tier": "mid"},
    },
    "image": {
        "pexels":           {"name": "Pexels Stok Foto",      "cost_60s": 0.00,   "model": None,                    "needs_key": "PEXELS_API_KEY",  "tier": "free"},
        "imagen4_fast":     {"name": "Imagen 4 Fast",         "cost_60s": 0.12,   "model": "imagen-4.0-fast-generate-001", "needs_key": "GEMINI_API_KEY", "tier": "budget"},
        "imagen4":          {"name": "Imagen 4 Standard",     "cost_60s": 0.24,   "model": "imagen-4.0-generate-001", "needs_key": "GEMINI_API_KEY", "tier": "mid"},
        "imagen4_ultra":    {"name": "Imagen 4 Ultra",        "cost_60s": 0.36,   "model": "imagen-4.0-ultra-generate-001", "needs_key": "GEMINI_API_KEY", "tier": "premium"},
        "gemini_imagen":    {"name": "Gemini 3 Pro Image",    "cost_60s": 0.80,   "model": "gemini-3-pro-image-preview", "needs_key": "GEMINI_API_KEY", "tier": "premium"},
        "gemini_flash_img": {"name": "Gemini 2.5 Flash Image","cost_60s": 0.23,   "model": "gemini-2.5-flash-image", "needs_key": "GEMINI_API_KEY",  "tier": "mid"},
        "dalle3":           {"name": "DALL-E 3",              "cost_60s": 0.24,   "model": "dall-e-3",              "needs_key": "OPENAI_API_KEY",  "tier": "mid"},
        "dalle3_hd":        {"name": "DALL-E 3 HD",           "cost_60s": 0.48,   "model": "dall-e-3-hd",           "needs_key": "OPENAI_API_KEY",  "tier": "premium"},
    },
    "video": {
        "none":             {"name": "Yok (Görsel Kullan)",   "cost_60s": 0.00,   "model": None,                    "needs_key": None,              "tier": "free"},
        "veo_lite":         {"name": "Veo 3.1 Lite",          "cost_60s": 2.25,   "model": "veo-3.1-lite-generate-preview", "needs_key": "GEMINI_API_KEY", "tier": "budget"},
        "veo_fast":         {"name": "Veo 3.1 Fast",          "cost_60s": 4.50,   "model": "veo-3.1-fast-generate-preview", "needs_key": "GEMINI_API_KEY", "tier": "mid"},
        "veo_standard":     {"name": "Veo 3.1 Standard",      "cost_60s": 12.00,  "model": "veo-3.1-generate-preview", "needs_key": "GEMINI_API_KEY", "tier": "premium"},
        "veo2":             {"name": "Veo 2.0",               "cost_60s": 15.00,  "model": "veo-2.0-generate-001",  "needs_key": "GEMINI_API_KEY",  "tier": "premium"},
    },
    "tts": {
        "edge_tts":         {"name": "Edge TTS (Microsoft)",  "cost_60s": 0.00,   "model": None,                    "needs_key": None,              "tier": "free"},
        "openai_tts":       {"name": "OpenAI TTS",            "cost_60s": 0.015,  "model": "tts-1",                 "needs_key": "OPENAI_API_KEY",  "tier": "budget"},
        "openai_tts_hd":    {"name": "OpenAI TTS HD",         "cost_60s": 0.03,   "model": "tts-1-hd",              "needs_key": "OPENAI_API_KEY",  "tier": "mid"},
        "google_tts":       {"name": "Google Cloud TTS",      "cost_60s": 0.004,  "model": "google-wavenet",        "needs_key": "GOOGLE_TTS_KEY",  "tier": "budget"},
        "elevenlabs_flash": {"name": "ElevenLabs Flash",      "cost_60s": 0.06,   "model": "eleven_flash_v2_5",     "needs_key": "ELEVENLABS_API_KEY", "tier": "mid"},
        "elevenlabs":       {"name": "ElevenLabs Multilingual","cost_60s": 0.12,  "model": "eleven_multilingual_v2","needs_key": "ELEVENLABS_API_KEY", "tier": "premium"},
    },
}

# ─────────────────────────────────────────────────────
# Voice config — override via env or config.json
# ─────────────────────────────────────────────────────
VOICE_ID_EN = os.environ.get("VOICE_ID_EN", "JBFqnCBsd6RMkjVDRZzb")  # George
VOICE_ID_HI = os.environ.get("VOICE_ID_HI", "JBFqnCBsd6RMkjVDRZzb")

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "from", "by", "is", "are", "was", "were", "be", "been", "has", "have",
    "had", "will", "would", "could", "should", "may", "might", "that", "this",
    "these", "those", "it", "its", "new", "ahead", "as", "into", "up", "out",
    "over", "after",
}


# ─────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────
def write_secret_file(path: Path, content: str):
    """Write a file with 0600 permissions (owner read/write only).

    Uses os.open() with explicit mode to avoid a TOCTOU race where the file
    briefly exists with default (world-readable) permissions.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)


def run_cmd(cmd, check=True, capture=False, **kwargs):
    if capture:
        r = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
        if check and r.returncode != 0:
            raise RuntimeError(r.stderr)
        return r
    subprocess.run(cmd, check=check, **kwargs)


def extract_keywords(text: str) -> str:
    words = [w.strip(".,!?\"'()[]").lower() for w in text.split()]
    return " ".join([w for w in words if w and w not in STOPWORDS and len(w) > 2][:4])


# ─────────────────────────────────────────────────────
# API key resolution — env → config.json
# ─────────────────────────────────────────────────────
def _get_key(name: str) -> str:
    """Resolve an API key: environment variable first, then config.json."""
    val = os.environ.get(name)
    if val:
        return val
    if CONFIG_FILE.exists():
        try:
            cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            val = cfg.get(name)
            if val:
                return val
        except Exception:
            pass
    return ""


def get_anthropic_key() -> str:
    return _get_key("ANTHROPIC_API_KEY")


# ─────────────────────────────────────────────────────
# Claude Max OAuth support
# ─────────────────────────────────────────────────────
CLAUDE_CREDENTIALS = Path.home() / ".claude" / ".credentials.json"


def has_claude_cli() -> bool:
    """Check if the `claude` CLI is available (Claude Code / Claude Max)."""
    import shutil
    return shutil.which("claude") is not None


def _has_claude_max_credentials() -> bool:
    """Check if Claude Max OAuth credentials exist."""
    if not CLAUDE_CREDENTIALS.exists():
        return False
    try:
        creds = json.loads(CLAUDE_CREDENTIALS.read_text(encoding="utf-8"))
        return bool(creds.get("claudeAiOauth", {}).get("accessToken"))
    except Exception:
        return False


def call_claude_cli(prompt: str, model: str = "claude-sonnet-4-6", max_tokens: int = 1500) -> str:
    """Call Claude via the `claude` CLI (uses Claude Max subscription).

    Pipes prompt via stdin to avoid Windows command-line length limits.
    No API key needed — uses Claude Max auth.
    """
    import shutil
    import tempfile
    claude_path = shutil.which("claude")
    if not claude_path:
        raise RuntimeError("claude CLI not found. Install Claude Code or set ANTHROPIC_API_KEY.")

    # Strip CLAUDECODE env var to allow running from within a Claude Code session
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    # Write prompt to temp file to avoid Windows arg length limits
    tmp = Path(tempfile.gettempdir()) / "yt_pipeline_prompt.txt"
    tmp.write_text(prompt, encoding="utf-8")

    r = subprocess.run(
        [
            claude_path, "--print",
            "--model", model,
            "--max-turns", "1",
            "--output-format", "text",
            "--system-prompt",
            "You are a YouTube Shorts scriptwriter. Respond ONLY with the requested JSON object. "
            "No questions, no commentary, no markdown fences. Stay strictly on the given topic. "
            "Do NOT ask clarifying questions. Do NOT deviate from the NEWS/TOPIC provided.",
        ],
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        env=env,
        cwd=str(Path.home()),
    )

    # Clean up temp file
    tmp.unlink(missing_ok=True)

    if r.returncode != 0:
        raise RuntimeError(f"claude CLI failed: {r.stderr[:300]}")
    output = r.stdout.strip()
    # Claude CLI may append "Error: Reached max turns" — strip it
    if output.endswith("Error: Reached max turns (3)"):
        output = output[: -len("Error: Reached max turns (3)")].strip()
    if output.endswith("Error: Reached max turns (1)"):
        output = output[: -len("Error: Reached max turns (1)")].strip()
    return output


def get_anthropic_client():
    """Create an Anthropic client if an API key is available.

    Returns the client, or None if no API key (caller should use call_claude_cli).
    """
    import anthropic

    api_key = get_anthropic_key()
    if api_key:
        return anthropic.Anthropic(api_key=api_key)

    return None


def get_claude_backend() -> str:
    """Determine which Claude backend to use.

    Returns: "api" if ANTHROPIC_API_KEY is set, "cli" if claude CLI is available.
    Raises RuntimeError if neither is available.
    """
    if get_anthropic_key():
        return "api"
    if has_claude_cli() and _has_claude_max_credentials():
        return "cli"
    raise RuntimeError(
        "No Claude access found. Either:\n"
        "  1. Set ANTHROPIC_API_KEY in env or ~/.youtube-shorts-pipeline/config.json\n"
        "  2. Log in to Claude Code (claude login) with a Claude Max subscription"
    )


def get_elevenlabs_key() -> str:
    return _get_key("ELEVENLABS_API_KEY")


def get_gemini_key() -> str:
    return _get_key("GEMINI_API_KEY")


def get_youtube_token_path() -> Path:
    token_path = SKILL_DIR / "youtube_token.json"
    if token_path.exists():
        return token_path
    raise FileNotFoundError(
        f"YouTube OAuth token not found at {token_path}.\n"
        "Run: python3 scripts/setup_youtube_oauth.py"
    )


def load_config() -> dict:
    """Load the full config.json, including topic_sources."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_config(config: dict):
    """Save config.json with restricted permissions."""
    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    write_secret_file(CONFIG_FILE, json.dumps(config, indent=2))


# ─────────────────────────────────────────────────────
# First-run interactive setup
# ─────────────────────────────────────────────────────
def run_setup():
    """Interactive first-run setup — saves config.json and runs YouTube OAuth."""
    print("\n" + "=" * 60)
    print("  YouTube Shorts Pipeline — First-Run Setup")
    print("=" * 60)
    print("\nThis wizard will configure your API keys and YouTube access.")
    print("Keys are saved to ~/.youtube-shorts-pipeline/config.json\n")

    SKILL_DIR.mkdir(parents=True, exist_ok=True)

    config = {}

    print("1. Anthropic API key (required — used for Claude script generation)")
    print("   Get yours at: https://console.anthropic.com/settings/keys")
    key = input("   ANTHROPIC_API_KEY: ").strip()
    if key:
        config["ANTHROPIC_API_KEY"] = key

    print("\n2. ElevenLabs API key (optional — fallback to macOS 'say' if omitted)")
    print("   Pro account required for server use. https://elevenlabs.io/settings/api-keys")
    key = input("   ELEVENLABS_API_KEY (press Enter to skip): ").strip()
    if key:
        config["ELEVENLABS_API_KEY"] = key

    print("\n3. Google Gemini API key (required — used for AI b-roll image generation)")
    print("   Get yours at: https://aistudio.google.com/apikey")
    key = input("   GEMINI_API_KEY: ").strip()
    if key:
        config["GEMINI_API_KEY"] = key

    save_config(config)
    print(f"\n  Config saved to {CONFIG_FILE}")

    print("\n4. YouTube OAuth setup")
    print("   You'll need a client_secret.json from Google Cloud Console.")
    print("   See references/setup.md for step-by-step instructions.")
    run_oauth = input("\n   Run YouTube OAuth now? (y/N): ").strip().lower()
    if run_oauth == "y":
        oauth_script = Path(__file__).resolve().parent.parent / "scripts" / "setup_youtube_oauth.py"
        if oauth_script.exists():
            subprocess.run([sys.executable, str(oauth_script)])
        else:
            print(f"   OAuth script not found at {oauth_script}")
            print("   Run it manually: python3 scripts/setup_youtube_oauth.py")
    else:
        print("   Skipping — run 'python3 scripts/setup_youtube_oauth.py' before uploading.")

    print("\n  Setup complete! Re-run your pipeline command to continue.\n")
    sys.exit(0)
