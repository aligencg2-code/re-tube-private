"""White-label branding — let customers rebrand the panel.

Reseller / agency buyers want to ship this product as their own: custom
logo, custom product name, custom accent color, optional custom domain.
We don't touch source code — only a branding.json in SKILL_DIR.

Usage from the UI:
    from pipeline import branding
    b = branding.load()
    st.markdown(f"## {b['product_name']}")
    logo_bytes = branding.logo_bytes()   # bytes | None

Schema:
    {
        "product_name": "RE-Tube",           # panel title
        "short_name":   "RT",                # favicon / tab
        "tagline":      "YouTube Otomasyon", # under the title
        "accent":       "#C9A96E",           # primary color
        "accent_dim":   "rgba(201,169,110,0.10)",
        "bg_deep":      "#0F0D0A",           # optional full theme override
        "logo_path":    "/opt/branding/logo.png",   # optional
        "favicon_path": "/opt/branding/favicon.ico",
        "hide_retube_credit": false,         # reseller toggle
        "support_email": "support@example.com",
        "support_url":   "https://example.com/support",
    }
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import SKILL_DIR


BRANDING_FILE = SKILL_DIR / "branding.json"

DEFAULTS: dict[str, Any] = {
    "product_name":      "RE-Tube",
    "short_name":        "RT",
    "tagline":           "YouTube Otomasyon",
    "accent":            "#C9A96E",
    "accent_dim":        "rgba(201, 169, 110, 0.10)",
    "bg_deep":           "#0F0D0A",
    "logo_path":         "",
    "favicon_path":      "",
    "hide_retube_credit": False,
    "support_email":     "",
    "support_url":       "",
}


def load() -> dict:
    """Return the active brand. Missing fields are filled from DEFAULTS so
    callers always see every key."""
    if not BRANDING_FILE.exists():
        return dict(DEFAULTS)
    try:
        raw = json.loads(BRANDING_FILE.read_text(encoding="utf-8"))
        out = dict(DEFAULTS)
        out.update({k: v for k, v in raw.items() if v not in (None, "")})
        return out
    except Exception:
        return dict(DEFAULTS)


def save(brand: dict) -> None:
    BRANDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    # Merge with existing so partial updates don't wipe fields
    current = load()
    current.update({k: v for k, v in brand.items() if v is not None})
    BRANDING_FILE.write_text(
        json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def reset() -> None:
    """Revert to defaults by removing the file."""
    if BRANDING_FILE.exists():
        BRANDING_FILE.unlink()


def logo_bytes() -> bytes | None:
    """Return logo file bytes if configured and readable, else None."""
    b = load()
    p = b.get("logo_path")
    if not p:
        return None
    try:
        return Path(p).read_bytes()
    except Exception:
        return None


def is_branded() -> bool:
    """True if the user has customized at least one visible field."""
    b = load()
    for k in ("product_name", "tagline", "accent"):
        if b.get(k) != DEFAULTS[k]:
            return True
    return bool(b.get("logo_path"))


def css_override() -> str:
    """Return a CSS snippet that overrides accent color + bg_deep.

    Injected at top of app.py styles so rebranding takes effect without
    editing source.
    """
    b = load()
    # Build an inline :root override
    return (
        ":root {"
        f"  --accent-primary: {b.get('accent', DEFAULTS['accent'])};"
        f"  --accent-primary-dim: {b.get('accent_dim', DEFAULTS['accent_dim'])};"
        f"  --bg-deep: {b.get('bg_deep', DEFAULTS['bg_deep'])};"
        "}"
    )
