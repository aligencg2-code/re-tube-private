"""Tests for voice_clone — local index management + API stubbing."""

import json
from unittest.mock import patch, MagicMock


def test_list_empty(tmp_path, monkeypatch):
    from pipeline import voice_clone as vc
    monkeypatch.setattr(vc, "CLONED_VOICES_FILE", tmp_path / "voices.json")
    assert vc.list_cloned_voices() == []


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    from pipeline import voice_clone as vc
    monkeypatch.setattr(vc, "CLONED_VOICES_FILE", tmp_path / "voices.json")

    idx = {
        "abc123xyz": {
            "name": "Ayaz Voice",
            "created_at": "2026-04-20T10:00:00+00:00",
            "channel_id": "ayaz",
            "sample_size_bytes": 245000,
            "mode": "instant",
        }
    }
    vc._save_index(idx)
    loaded = vc._load_index()
    assert loaded["abc123xyz"]["name"] == "Ayaz Voice"

    voices = vc.list_cloned_voices()
    assert len(voices) == 1
    assert voices[0]["voice_id"] == "abc123xyz"


def test_delete_nonexistent_returns_error(tmp_path, monkeypatch):
    from pipeline import voice_clone as vc
    monkeypatch.setattr(vc, "CLONED_VOICES_FILE", tmp_path / "voices.json")

    r = vc.delete_voice("does_not_exist")
    assert r["error"] == "not_found"


def test_delete_local_without_remote(tmp_path, monkeypatch):
    from pipeline import voice_clone as vc
    monkeypatch.setattr(vc, "CLONED_VOICES_FILE", tmp_path / "voices.json")

    vc._save_index({"abc": {"name": "Test"}})
    r = vc.delete_voice("abc", delete_remote=False)
    assert r["removed_local"] is True
    assert r["removed_remote"] is False
    assert vc._load_index() == {}


def test_clone_instant_without_api_key_returns_error(tmp_path, monkeypatch):
    from pipeline import voice_clone as vc, config as cfg
    monkeypatch.setattr(vc, "CLONED_VOICES_FILE", tmp_path / "voices.json")
    monkeypatch.setattr(vc, "_get_key", lambda k: "")

    r = vc.clone_instant(name="Test", sample_bytes=b"fake audio")
    assert "error" in r
    assert "ELEVENLABS_API_KEY" in r["error"]


def test_clone_instant_success_path(tmp_path, monkeypatch):
    """Stub ElevenLabs API to return a voice_id, verify local registration."""
    from pipeline import voice_clone as vc, config as cfg
    monkeypatch.setattr(vc, "CLONED_VOICES_FILE", tmp_path / "voices.json")
    monkeypatch.setattr(vc, "_get_key", lambda k: "el_fake_key")

    # Stub requests.post
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.ok = True
    fake_resp.json.return_value = {"voice_id": "voice_real_123"}

    with patch("requests.post", return_value=fake_resp) as mock_post:
        r = vc.clone_instant(
            name="Musteri A Voice",
            sample_bytes=b"\x00" * 1024,
            channel_id="musteri_a",
        )

    assert r.get("voice_id") == "voice_real_123"
    assert r["name"] == "Musteri A Voice"
    assert r["mode"] == "instant"

    # Local index registered
    idx = vc._load_index()
    assert "voice_real_123" in idx
    assert idx["voice_real_123"]["channel_id"] == "musteri_a"
    assert idx["voice_real_123"]["sample_size_bytes"] == 1024

    # Correct POST was made
    args, kwargs = mock_post.call_args
    assert "/v1/voices/add" in args[0]
    assert kwargs["headers"]["xi-api-key"] == "el_fake_key"
    assert "files" in kwargs
    assert kwargs["data"]["name"] == "Musteri A Voice"


def test_clone_instant_api_error_returns_error(tmp_path, monkeypatch):
    from pipeline import voice_clone as vc, config as cfg
    monkeypatch.setattr(vc, "CLONED_VOICES_FILE", tmp_path / "voices.json")
    monkeypatch.setattr(vc, "_get_key", lambda k: "el_fake_key")

    fake_resp = MagicMock()
    fake_resp.status_code = 401
    fake_resp.ok = False
    fake_resp.json.return_value = {"detail": "Invalid API key"}

    with patch("requests.post", return_value=fake_resp):
        r = vc.clone_instant(name="Test", sample_bytes=b"x")

    assert "error" in r
    assert "401" in r["error"]
    # Local index NOT updated on error
    assert vc._load_index() == {}


def test_get_voice(tmp_path, monkeypatch):
    from pipeline import voice_clone as vc
    monkeypatch.setattr(vc, "CLONED_VOICES_FILE", tmp_path / "voices.json")

    vc._save_index({"abc": {"name": "Test"}})
    assert vc.get_voice("abc")["name"] == "Test"
    assert vc.get_voice("missing") is None


def test_list_remote_voices_without_key(tmp_path, monkeypatch):
    from pipeline import voice_clone as vc, config as cfg
    monkeypatch.setattr(vc, "_get_key", lambda k: "")
    r = vc.list_remote_voices()
    assert "error" in r


def test_account_info_without_key(monkeypatch):
    from pipeline import voice_clone as vc, config as cfg
    monkeypatch.setattr(vc, "_get_key", lambda k: "")
    r = vc.account_info()
    assert r["error"] == "no_api_key"
