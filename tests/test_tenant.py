"""Tests for multi-tenant feature flag + migration + tenant management."""

import json
from pathlib import Path


def _reset_tenant_module(monkeypatch, tmp_path):
    """Redirect tenant module's paths to a tmp area and reset in-memory state."""
    from pipeline import tenant, config as cfg
    monkeypatch.setattr(cfg, "SKILL_DIR", tmp_path)
    monkeypatch.setattr(tenant, "FEATURES_FILE", tmp_path / "features.json")
    monkeypatch.setattr(tenant, "TENANTS_ROOT", tmp_path / "tenants")
    monkeypatch.setattr(tenant, "TENANTS_INDEX", tmp_path / "tenants.json")
    tenant._process_current = "default"
    return tenant


def test_default_flag_is_off(tmp_path, monkeypatch):
    t = _reset_tenant_module(monkeypatch, tmp_path)
    assert t.is_multi_tenant_enabled() is False


def test_tenant_dir_returns_skill_dir_when_flag_off(tmp_path, monkeypatch):
    t = _reset_tenant_module(monkeypatch, tmp_path)
    from pipeline import config as cfg
    assert t.tenant_dir() == cfg.SKILL_DIR
    assert t.current_tenant_id() == "default"


def test_list_tenants_empty_when_flag_off(tmp_path, monkeypatch):
    t = _reset_tenant_module(monkeypatch, tmp_path)
    assert t.list_tenants() == []


def test_enable_multi_tenant_migrates_data(tmp_path, monkeypatch):
    t = _reset_tenant_module(monkeypatch, tmp_path)

    # Seed SKILL_DIR with some data
    (tmp_path / "config.json").write_text('{"test": 1}', encoding="utf-8")
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "d1.json").write_text("{}", encoding="utf-8")
    (tmp_path / "channels").mkdir()
    (tmp_path / "channels" / "ayaz").mkdir()
    (tmp_path / "channels" / "ayaz" / "youtube_token.json").write_text('{"token":"x"}', encoding="utf-8")

    result = t.enable_multi_tenant(skip_backup=True)
    assert t.is_multi_tenant_enabled() is True
    assert "config.json" in result["migrated"]
    assert "drafts" in result["migrated"]
    assert "channels" in result["migrated"]

    # After migration: data lives under tenants/default/
    default_dir = tmp_path / "tenants" / "default"
    assert (default_dir / "config.json").exists()
    assert (default_dir / "drafts" / "d1.json").exists()
    assert (default_dir / "channels" / "ayaz" / "youtube_token.json").exists()

    # Originals removed
    assert not (tmp_path / "config.json").exists()
    assert not (tmp_path / "drafts").exists()


def test_youtube_token_survives_migration(tmp_path, monkeypatch):
    """Critical: OAuth tokens must move intact so customers don't re-auth."""
    t = _reset_tenant_module(monkeypatch, tmp_path)

    token_content = '{"token": "ya29.real", "refresh_token": "rt_real"}'
    (tmp_path / "youtube_token.json").write_text(token_content, encoding="utf-8")
    (tmp_path / "channels").mkdir()
    (tmp_path / "channels" / "ayaz").mkdir()
    (tmp_path / "channels" / "ayaz" / "youtube_token.json").write_text(
        token_content, encoding="utf-8"
    )

    t.enable_multi_tenant(skip_backup=True)

    # Tokens must be preserved bit-for-bit in their new location
    new_default_token = tmp_path / "tenants" / "default" / "youtube_token.json"
    assert new_default_token.read_text(encoding="utf-8") == token_content

    new_ayaz_token = tmp_path / "tenants" / "default" / "channels" / "ayaz" / "youtube_token.json"
    assert new_ayaz_token.read_text(encoding="utf-8") == token_content


def test_enable_is_idempotent(tmp_path, monkeypatch):
    t = _reset_tenant_module(monkeypatch, tmp_path)
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")

    r1 = t.enable_multi_tenant(skip_backup=True)
    r2 = t.enable_multi_tenant(skip_backup=True)
    assert "migrated" in r1
    assert r2.get("already_enabled") is True


def test_disable_restores_data_to_skill_dir(tmp_path, monkeypatch):
    t = _reset_tenant_module(monkeypatch, tmp_path)
    (tmp_path / "config.json").write_text('{"v":1}', encoding="utf-8")
    (tmp_path / "drafts").mkdir()

    t.enable_multi_tenant(skip_backup=True)
    assert t.is_multi_tenant_enabled()

    # Now disable
    r = t.disable_multi_tenant(skip_backup=True)
    assert t.is_multi_tenant_enabled() is False
    assert "config.json" in r["restored"]
    # Data back at SKILL_DIR root
    assert (tmp_path / "config.json").exists()
    assert (tmp_path / "config.json").read_text() == '{"v":1}'


def test_create_tenant_requires_multi_tenant_enabled(tmp_path, monkeypatch):
    t = _reset_tenant_module(monkeypatch, tmp_path)

    try:
        t.create_tenant("acme")
        assert False, "Should have raised"
    except RuntimeError as e:
        assert "disabled" in str(e)


def test_create_and_list_tenants(tmp_path, monkeypatch):
    t = _reset_tenant_module(monkeypatch, tmp_path)
    t.enable_multi_tenant(skip_backup=True)

    t.create_tenant("acme", name="Acme Co")
    t.create_tenant("beta_corp", name="Beta Corp")

    tenants = t.list_tenants()
    ids = [x["id"] for x in tenants]
    assert "default" in ids
    assert "acme" in ids
    assert "beta_corp" in ids
    acme = next(x for x in tenants if x["id"] == "acme")
    assert acme["name"] == "Acme Co"


def test_create_tenant_sanitizes_id(tmp_path, monkeypatch):
    t = _reset_tenant_module(monkeypatch, tmp_path)
    t.enable_multi_tenant(skip_backup=True)

    r = t.create_tenant("Acme Co / Bad!")
    # 'Acme Co / Bad!' → "acmecobad" (spaces and punctuation stripped, lowercased)
    assert r["id"].isalnum() or "-" in r["id"] or "_" in r["id"]


def test_cannot_delete_default_tenant(tmp_path, monkeypatch):
    t = _reset_tenant_module(monkeypatch, tmp_path)
    t.enable_multi_tenant(skip_backup=True)

    r = t.delete_tenant("default")
    assert "error" in r


def test_delete_tenant_removes_from_registry(tmp_path, monkeypatch):
    t = _reset_tenant_module(monkeypatch, tmp_path)
    t.enable_multi_tenant(skip_backup=True)
    t.create_tenant("temp")

    assert any(x["id"] == "temp" for x in t.list_tenants())
    t.delete_tenant("temp")
    assert not any(x["id"] == "temp" for x in t.list_tenants())


def test_enable_creates_backup_by_default(tmp_path, monkeypatch):
    """Enabling multi-tenant must backup SKILL_DIR to .backup.<ts>/ first."""
    t = _reset_tenant_module(monkeypatch, tmp_path)

    # Seed some user data
    (tmp_path / "config.json").write_text('{"key":"value"}', encoding="utf-8")
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "d1.json").write_text('{}', encoding="utf-8")

    result = t.enable_multi_tenant()  # skip_backup=False by default
    assert "backup_path" in result
    assert result["backup_path"] is not None

    backup = __import__("pathlib").Path(result["backup_path"])
    assert backup.exists()
    # Backup contains the original files
    assert (backup / "config.json").exists()
    assert (backup / "drafts" / "d1.json").exists()
    assert (backup / "config.json").read_text(encoding="utf-8") == '{"key":"value"}'


def test_disable_creates_backup_by_default(tmp_path, monkeypatch):
    t = _reset_tenant_module(monkeypatch, tmp_path)

    (tmp_path / "config.json").write_text('{}', encoding="utf-8")
    t.enable_multi_tenant(skip_backup=True)  # enable first
    # Now disable with backup
    result = t.disable_multi_tenant()
    assert "backup_path" in result
    # Backup path points into tenants/default parent structure
    backup = __import__("pathlib").Path(result["backup_path"])
    assert backup.exists()


def test_tenant_dir_returns_per_tenant_path_when_flag_on(tmp_path, monkeypatch):
    t = _reset_tenant_module(monkeypatch, tmp_path)
    t.enable_multi_tenant(skip_backup=True)
    t.create_tenant("acme")

    # Default tenant
    assert t.tenant_dir() == tmp_path / "tenants" / "default"
    # Switch to acme
    t.set_current_tenant("acme")
    assert t.tenant_dir() == tmp_path / "tenants" / "acme"
    assert t.current_tenant_id() == "acme"
