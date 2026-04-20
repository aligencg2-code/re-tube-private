"""Multi-tenant support — FEATURE FLAG OFF by default.

Backwards compatibility is the #1 priority here. When multi-tenant is
disabled (default), every call in this module returns values that make the
rest of the codebase behave EXACTLY like before — `tenant_dir()` returns
_skill_dir(), `current_tenant_id()` returns "default", etc.

When the admin turns multi-tenant ON via Settings:
    1. A one-shot migration moves _skill_dir()/* into _skill_dir()/tenants/default/*
       (drafts, media, channels, queue, config.json, YouTube tokens, ...)
    2. From then on, `tenant_dir()` returns the active tenant's directory.
    3. The panel shows a tenant switcher in the sidebar.
    4. Each tenant has an isolated config.json, channels/, drafts/, media/,
       queue/, cost/, audit/, etc.

YouTube OAuth tokens survive the migration — they're just files, we move
them to the new path. Google doesn't revoke tokens when you move a file,
so customers don't re-auth.

The feature flag lives in _skill_dir()/features.json:
    {"multi_tenant": false}
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import config as _cfg


def _skill_dir() -> Path:
    """Dynamic lookup so tests can monkeypatch config.SKILL_DIR."""
    return _cfg.SKILL_DIR


# These module-level Paths are convenient defaults but tests and migrations
# can override them. Production code reads them at call time via _skill_dir().
FEATURES_FILE = _cfg.SKILL_DIR / "features.json"
TENANTS_ROOT = _cfg.SKILL_DIR / "tenants"
TENANTS_INDEX = _cfg.SKILL_DIR / "tenants.json"

DEFAULT_TENANT = "default"

# Items under _skill_dir() that get migrated into tenants/<id>/ when enabling
# multi-tenant. Items NOT listed here stay at _skill_dir() root (shared across
# tenants): audit log, api_tokens.json, branding.json, features.json itself,
# tenants.json.
_MIGRATABLE_ITEMS = [
    "config.json",
    "youtube_token.json",
    "channels",
    "drafts",
    "media",
    "logs",
    "queue",
    "usage",
    "stats_cache",
    "topic_memory.sqlite",
    "thumbnail_tests.sqlite",
    "comments.sqlite",
    "default_preset.json",
]


# ────────────────────────────────────────────────────────────
# Feature flag
# ────────────────────────────────────────────────────────────
def _load_features() -> dict:
    if not FEATURES_FILE.exists():
        return {}
    try:
        return json.loads(FEATURES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_features(features: dict) -> None:
    FEATURES_FILE.parent.mkdir(parents=True, exist_ok=True)
    FEATURES_FILE.write_text(
        json.dumps(features, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def is_multi_tenant_enabled() -> bool:
    return bool(_load_features().get("multi_tenant"))


def _backup_before_migration() -> Path | None:
    """Create a timestamped full copy of SKILL_DIR before any destructive
    migration. Returns backup path on success, None on failure.

    Backups land under SKILL_DIR.parent as `.youtube-shorts-pipeline.backup.<ts>/`.
    This is the safety net the customer can manually restore from if
    anything goes wrong with a migration.
    """
    try:
        skill = _skill_dir()
        if not skill.exists():
            return None
        # Microsecond precision avoids collisions when enable + disable are
        # called in quick succession (e.g. tests, or an admin flipping fast)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        backup = skill.parent / f".youtube-shorts-pipeline.backup.{ts}"
        # Deep copy — preserves subdirs, file modes, OAuth tokens
        shutil.copytree(str(skill), str(backup), dirs_exist_ok=False)
        return backup
    except Exception as e:
        # If we can't back up, refuse to migrate
        return None


def enable_multi_tenant(*, skip_backup: bool = False) -> dict:
    """Turn on multi-tenant mode.

    Performs one-time migration of _skill_dir()/* → tenants/default/*. Idempotent
    — running again on an already-migrated setup is a no-op.

    **Safety**: Before touching any data, takes a full backup of SKILL_DIR
    to `<skill_dir>.backup.<timestamp>/`. If backup fails, migration is
    aborted so no data can be lost.
    """
    if is_multi_tenant_enabled():
        return {"already_enabled": True}

    # Safety: full backup before any file moves
    backup_path = None
    if not skip_backup:
        backup_path = _backup_before_migration()
        if backup_path is None:
            return {
                "error": "backup_failed",
                "reason": "Yedek alınamadı — migration iptal edildi. "
                          "Diskte yer olduğundan emin ol ve tekrar dene.",
            }

    TENANTS_ROOT.mkdir(parents=True, exist_ok=True)
    default_dir = TENANTS_ROOT / DEFAULT_TENANT
    default_dir.mkdir(exist_ok=True)

    moved = []
    for item in _MIGRATABLE_ITEMS:
        src = _skill_dir() / item
        if not src.exists():
            continue
        dst = default_dir / item
        if dst.exists():
            continue  # already migrated
        shutil.move(str(src), str(dst))
        moved.append(item)

    # Register default tenant
    _save_tenants_index({
        DEFAULT_TENANT: {
            "name": "Varsayılan",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_default": True,
        }
    })

    # Flip the flag
    features = _load_features()
    features["multi_tenant"] = True
    _save_features(features)

    try:
        from . import audit
        audit.log("tenant_created", target=DEFAULT_TENANT,
                  details={"migrated_items": moved,
                           "backup_path": str(backup_path) if backup_path else None})
    except Exception:
        pass
    return {
        "migrated": moved,
        "default_tenant_dir": str(default_dir),
        "backup_path": str(backup_path) if backup_path else None,
    }


def disable_multi_tenant(*, skip_backup: bool = False) -> dict:
    """Turn OFF multi-tenant. Moves tenants/default/* back to _skill_dir() root.

    Non-default tenants' data stays in tenants/<name>/ but becomes invisible
    to the panel (until re-enabled) — not deleted. Safer than a destructive
    merge.

    **Safety**: Full backup before moving files (same pattern as enable).
    """
    if not is_multi_tenant_enabled():
        return {"already_disabled": True}

    backup_path = None
    if not skip_backup:
        backup_path = _backup_before_migration()
        if backup_path is None:
            return {
                "error": "backup_failed",
                "reason": "Yedek alınamadı — disable iptal edildi.",
            }

    default_dir = TENANTS_ROOT / DEFAULT_TENANT
    moved_back = []
    if default_dir.exists():
        for item in _MIGRATABLE_ITEMS:
            src = default_dir / item
            dst = _skill_dir() / item
            if src.exists() and not dst.exists():
                shutil.move(str(src), str(dst))
                moved_back.append(item)

    features = _load_features()
    features["multi_tenant"] = False
    _save_features(features)
    return {"restored": moved_back,
            "note": "Non-default tenants preserved in tenants/ directory",
            "backup_path": str(backup_path) if backup_path else None}


# ────────────────────────────────────────────────────────────
# Tenant registry
# ────────────────────────────────────────────────────────────
def _load_tenants_index() -> dict:
    if not TENANTS_INDEX.exists():
        return {}
    try:
        return json.loads(TENANTS_INDEX.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_tenants_index(index: dict) -> None:
    TENANTS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    TENANTS_INDEX.write_text(
        json.dumps(index, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def list_tenants() -> list[dict]:
    """Return configured tenants. Empty list if multi-tenant is off."""
    if not is_multi_tenant_enabled():
        return []
    idx = _load_tenants_index()
    return [{"id": k, **v} for k, v in sorted(idx.items())]


def create_tenant(tenant_id: str, name: str | None = None) -> dict:
    """Create a new tenant directory + register it."""
    if not is_multi_tenant_enabled():
        raise RuntimeError("Multi-tenant mode is disabled. Enable it first.")
    safe_id = "".join(c for c in tenant_id if c.isalnum() or c in "-_").lower()
    if not safe_id:
        raise ValueError("Invalid tenant_id (alnum/-/_ only)")

    idx = _load_tenants_index()
    if safe_id in idx:
        return {"already_exists": True, "id": safe_id}

    tenant_dir_path = TENANTS_ROOT / safe_id
    tenant_dir_path.mkdir(parents=True, exist_ok=True)

    idx[safe_id] = {
        "name": name or safe_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_default": False,
    }
    _save_tenants_index(idx)
    try:
        from . import audit
        audit.log("tenant_created", target=safe_id, details={"name": name})
    except Exception:
        pass
    return {"id": safe_id, "path": str(tenant_dir_path)}


def delete_tenant(tenant_id: str, *, hard: bool = False) -> dict:
    """Remove a tenant from registry. hard=True also deletes data.

    Refuses to delete the default tenant.
    """
    if tenant_id == DEFAULT_TENANT:
        return {"error": "cannot delete default tenant"}
    idx = _load_tenants_index()
    if tenant_id not in idx:
        return {"error": "not_found"}
    del idx[tenant_id]
    _save_tenants_index(idx)

    if hard:
        tpath = TENANTS_ROOT / tenant_id
        if tpath.exists():
            shutil.rmtree(str(tpath))

    try:
        from . import audit
        audit.log("tenant_deleted", target=tenant_id, details={"hard": hard})
    except Exception:
        pass
    return {"deleted": tenant_id, "hard": hard}


# ────────────────────────────────────────────────────────────
# Current tenant (session-bound)
# ────────────────────────────────────────────────────────────
# Streamlit callers pass their session state into set_current_tenant(); the
# Python-process-level default is used by CLI/worker until someone sets it.
_process_current = DEFAULT_TENANT


def set_current_tenant(tenant_id: str) -> None:
    global _process_current
    _process_current = tenant_id


def current_tenant_id() -> str:
    """Return the active tenant. Always returns DEFAULT_TENANT when MT is off."""
    if not is_multi_tenant_enabled():
        return DEFAULT_TENANT
    return _process_current


def tenant_dir(tenant_id: str | None = None) -> Path:
    """Return the data directory for the given tenant (or current).

    **Backwards-compat guarantee:** When multi-tenant is disabled,
    this returns _skill_dir() (just like the pre-MT world).
    """
    if not is_multi_tenant_enabled():
        return _skill_dir()
    tid = tenant_id or current_tenant_id()
    return TENANTS_ROOT / tid
