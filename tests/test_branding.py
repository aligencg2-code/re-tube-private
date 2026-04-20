"""Tests for white-label branding storage + defaults + CSS override."""


def test_load_without_file_returns_defaults(tmp_path, monkeypatch):
    from pipeline import branding
    monkeypatch.setattr(branding, "BRANDING_FILE", tmp_path / "branding.json")

    b = branding.load()
    assert b["product_name"] == "RE-Tube"
    assert b["accent"] == "#C9A96E"
    assert b["hide_retube_credit"] is False


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    from pipeline import branding
    monkeypatch.setattr(branding, "BRANDING_FILE", tmp_path / "branding.json")

    branding.save({
        "product_name": "Acme Studio",
        "accent": "#FF0055",
        "tagline": "Video factory",
    })
    b = branding.load()
    assert b["product_name"] == "Acme Studio"
    assert b["accent"] == "#FF0055"
    assert b["tagline"] == "Video factory"
    # Unset fields still return defaults
    assert b["short_name"] == "RT"
    assert b["bg_deep"] == "#0F0D0A"


def test_save_merges_partial_updates(tmp_path, monkeypatch):
    from pipeline import branding
    monkeypatch.setattr(branding, "BRANDING_FILE", tmp_path / "branding.json")

    branding.save({"product_name": "Acme", "accent": "#FF0055"})
    # Partial update — should not wipe product_name
    branding.save({"tagline": "New tagline"})

    b = branding.load()
    assert b["product_name"] == "Acme"
    assert b["accent"] == "#FF0055"
    assert b["tagline"] == "New tagline"


def test_reset_removes_file(tmp_path, monkeypatch):
    from pipeline import branding
    monkeypatch.setattr(branding, "BRANDING_FILE", tmp_path / "branding.json")

    branding.save({"product_name": "Custom"})
    assert branding.load()["product_name"] == "Custom"

    branding.reset()
    assert branding.load()["product_name"] == "RE-Tube"


def test_is_branded_detects_customization(tmp_path, monkeypatch):
    from pipeline import branding
    monkeypatch.setattr(branding, "BRANDING_FILE", tmp_path / "branding.json")

    assert branding.is_branded() is False  # Just defaults
    branding.save({"product_name": "Acme"})
    assert branding.is_branded() is True


def test_css_override_includes_accent_and_bg(tmp_path, monkeypatch):
    from pipeline import branding
    monkeypatch.setattr(branding, "BRANDING_FILE", tmp_path / "branding.json")

    branding.save({"accent": "#FF0055", "bg_deep": "#111111"})
    css = branding.css_override()
    assert "--accent-primary: #FF0055" in css
    assert "--bg-deep: #111111" in css


def test_corrupt_file_returns_defaults(tmp_path, monkeypatch):
    from pipeline import branding
    f = tmp_path / "branding.json"
    f.write_text("not valid json", encoding="utf-8")
    monkeypatch.setattr(branding, "BRANDING_FILE", f)

    b = branding.load()
    assert b["product_name"] == "RE-Tube"  # fell back to defaults


def test_logo_bytes_returns_none_when_unset(tmp_path, monkeypatch):
    from pipeline import branding
    monkeypatch.setattr(branding, "BRANDING_FILE", tmp_path / "branding.json")
    assert branding.logo_bytes() is None


def test_logo_bytes_reads_file_when_configured(tmp_path, monkeypatch):
    from pipeline import branding
    monkeypatch.setattr(branding, "BRANDING_FILE", tmp_path / "branding.json")

    # Create a fake logo
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"\x89PNG fake")
    branding.save({"logo_path": str(logo)})

    data = branding.logo_bytes()
    assert data == b"\x89PNG fake"


def test_logo_bytes_returns_none_on_missing_file(tmp_path, monkeypatch):
    from pipeline import branding
    monkeypatch.setattr(branding, "BRANDING_FILE", tmp_path / "branding.json")

    branding.save({"logo_path": str(tmp_path / "nonexistent.png")})
    assert branding.logo_bytes() is None
