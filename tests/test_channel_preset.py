"""Tests for per-channel preset storage + merge_defaults fallback."""

import json


def test_load_preset_missing_returns_empty(tmp_path, monkeypatch):
    from pipeline import channel_preset as cp
    monkeypatch.setattr(cp, "CHANNELS_DIR", tmp_path)
    from pipeline import config as _cfg
    monkeypatch.setattr(_cfg, "SKILL_DIR", tmp_path)

    assert cp.load_preset("nonexistent") == {}
    assert cp.load_preset("") == {}


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    from pipeline import channel_preset as cp
    from pipeline import config as _cfg
    monkeypatch.setattr(cp, "CHANNELS_DIR", tmp_path)
    monkeypatch.setattr(_cfg, "SKILL_DIR", tmp_path)

    preset = {
        "lang": "tr",
        "format": "shorts",
        "duration": "short",
        "tts": "elevenlabs",
        "context": "Teknoloji haber kanali",
        "playlist_id": "PLxxxx",
    }
    cp.save_preset("mychannel", preset)
    loaded = cp.load_preset("mychannel")
    assert loaded == preset


def test_save_preset_creates_parent_dir(tmp_path, monkeypatch):
    from pipeline import channel_preset as cp
    from pipeline import config as _cfg
    monkeypatch.setattr(cp, "CHANNELS_DIR", tmp_path / "channels")
    monkeypatch.setattr(_cfg, "SKILL_DIR", tmp_path)

    cp.save_preset("newchan", {"lang": "en"})
    p = tmp_path / "channels" / "newchan" / "preset.json"
    assert p.exists()


def test_corrupt_preset_returns_empty(tmp_path, monkeypatch):
    from pipeline import channel_preset as cp
    from pipeline import config as _cfg
    monkeypatch.setattr(cp, "CHANNELS_DIR", tmp_path)
    monkeypatch.setattr(_cfg, "SKILL_DIR", tmp_path)

    cp.save_preset("broken", {"ok": True})
    # Corrupt the file
    p = cp._preset_path("broken")
    p.write_text("not valid json{", encoding="utf-8")

    # Must not raise, returns empty
    assert cp.load_preset("broken") == {}


def test_merge_defaults_overrides_win(tmp_path, monkeypatch):
    from pipeline import channel_preset as cp
    from pipeline import config as _cfg
    monkeypatch.setattr(cp, "CHANNELS_DIR", tmp_path)
    monkeypatch.setattr(_cfg, "SKILL_DIR", tmp_path)

    cp.save_preset("ch", {"lang": "tr", "duration": "short", "tts": "voixor"})
    result = cp.merge_defaults("ch", lang="en", duration=None, script_ai="gpt4o")
    assert result["lang"] == "en"          # override wins
    assert result["duration"] == "short"   # None override → preset wins
    assert result["tts"] == "voixor"       # preset preserved
    assert result["script_ai"] == "gpt4o"  # override adds new


def test_merge_defaults_without_channel(tmp_path, monkeypatch):
    from pipeline import channel_preset as cp
    from pipeline import config as _cfg
    monkeypatch.setattr(cp, "CHANNELS_DIR", tmp_path)
    monkeypatch.setattr(_cfg, "SKILL_DIR", tmp_path)

    result = cp.merge_defaults(None, lang="tr", format="shorts")
    assert result == {"lang": "tr", "format": "shorts"}


def test_merge_defaults_empty_string_does_not_override(tmp_path, monkeypatch):
    """Empty string should NOT override preset (user didn't pick a value)."""
    from pipeline import channel_preset as cp
    from pipeline import config as _cfg
    monkeypatch.setattr(cp, "CHANNELS_DIR", tmp_path)
    monkeypatch.setattr(_cfg, "SKILL_DIR", tmp_path)

    cp.save_preset("ch", {"lang": "tr"})
    result = cp.merge_defaults("ch", lang="")
    assert result["lang"] == "tr"   # empty string did not override
