# -*- coding: utf-8 -*-
"""RE-Tube Auto-Updater — GitHub Private Repo based update system."""

import json
import subprocess
import sys
import os
import io
import shutil
from pathlib import Path
from datetime import datetime

# Fix Windows encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_DIR = Path(__file__).resolve().parent
VERSION_FILE = PROJECT_DIR / "version.json"
UPDATE_LOG = PROJECT_DIR / "update_log.txt"

# ─── Default config ─────────────────────────────────
DEFAULT_UPDATE_CONFIG = {
    "repo_url": "",  # e.g. "https://github.com/username/re-tube.git"
    "branch": "main",
    "auto_check": True,
    "last_check": "",
    "last_update": "",
    "current_version": "1.0.0",
}


def load_version_info() -> dict:
    if VERSION_FILE.exists():
        try:
            return json.loads(VERSION_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return DEFAULT_UPDATE_CONFIG.copy()


def save_version_info(info: dict):
    VERSION_FILE.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")


def log_update(message: str):
    """Append to update log."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(UPDATE_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def has_git() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True, timeout=5)
        return True
    except Exception:
        return False


def is_git_repo() -> bool:
    return (PROJECT_DIR / ".git").exists()


def init_repo(repo_url: str, branch: str = "main") -> tuple[bool, str]:
    """Initialize git repo if not exists, set remote."""
    try:
        if not is_git_repo():
            subprocess.run(
                ["git", "init"], cwd=str(PROJECT_DIR),
                capture_output=True, text=True, encoding="utf-8",
            )
            subprocess.run(
                ["git", "remote", "add", "origin", repo_url],
                cwd=str(PROJECT_DIR),
                capture_output=True, text=True, encoding="utf-8",
            )
            log_update(f"Git repo initialized with remote: {repo_url}")
        else:
            # Update remote URL if changed
            subprocess.run(
                ["git", "remote", "set-url", "origin", repo_url],
                cwd=str(PROJECT_DIR),
                capture_output=True, text=True, encoding="utf-8",
            )

        return True, "OK"
    except Exception as e:
        return False, str(e)


def check_for_updates(repo_url: str, branch: str = "main") -> tuple[bool, str, str]:
    """Check if there are updates available.

    Returns: (has_updates, local_commit, remote_commit)
    """
    try:
        # Fetch latest
        r = subprocess.run(
            ["git", "fetch", "origin", branch],
            cwd=str(PROJECT_DIR),
            capture_output=True, text=True, encoding="utf-8",
            timeout=30,
        )

        # Get local HEAD
        local = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(PROJECT_DIR),
            capture_output=True, text=True, encoding="utf-8",
        )
        local_hash = local.stdout.strip()[:8] if local.returncode == 0 else "unknown"

        # Get remote HEAD
        remote = subprocess.run(
            ["git", "rev-parse", f"origin/{branch}"],
            cwd=str(PROJECT_DIR),
            capture_output=True, text=True, encoding="utf-8",
        )
        remote_hash = remote.stdout.strip()[:8] if remote.returncode == 0 else "unknown"

        has_updates = local_hash != remote_hash
        return has_updates, local_hash, remote_hash

    except Exception as e:
        return False, "error", str(e)


def get_update_changelog(branch: str = "main") -> str:
    """Get commit messages between local and remote."""
    try:
        r = subprocess.run(
            ["git", "log", f"HEAD..origin/{branch}", "--oneline", "--no-decorate"],
            cwd=str(PROJECT_DIR),
            capture_output=True, text=True, encoding="utf-8",
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def apply_update(branch: str = "main") -> tuple[bool, str]:
    """Pull latest changes from remote.

    Preserves: config.json, youtube_token.json, drafts/, media/
    (These are in ~/.youtube-shorts-pipeline/, not in project dir, so safe)
    """
    try:
        # Stash any local changes
        subprocess.run(
            ["git", "stash"],
            cwd=str(PROJECT_DIR),
            capture_output=True, text=True, encoding="utf-8",
        )

        # Pull latest
        r = subprocess.run(
            ["git", "pull", "origin", branch, "--rebase"],
            cwd=str(PROJECT_DIR),
            capture_output=True, text=True, encoding="utf-8",
            timeout=120,
        )

        if r.returncode != 0:
            # Try force reset if rebase fails
            subprocess.run(
                ["git", "rebase", "--abort"],
                cwd=str(PROJECT_DIR),
                capture_output=True, text=True, encoding="utf-8",
            )
            r = subprocess.run(
                ["git", "reset", "--hard", f"origin/{branch}"],
                cwd=str(PROJECT_DIR),
                capture_output=True, text=True, encoding="utf-8",
            )

        # Install any new dependencies
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"],
            cwd=str(PROJECT_DIR),
            capture_output=True, text=True, encoding="utf-8",
            timeout=120,
        )

        # Update version info
        info = load_version_info()
        info["last_update"] = datetime.now().isoformat()
        save_version_info(info)

        log_update(f"Update applied from {branch}")
        return True, "Güncelleme başarılı!"

    except Exception as e:
        log_update(f"Update failed: {e}")
        return False, f"Güncelleme hatası: {e}"


# ─── CLI interface ───────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="RE-Tube Updater")
    parser.add_argument("action", choices=["check", "update", "init", "version"],
                        help="check=check for updates, update=apply updates, init=setup repo, version=show version")
    parser.add_argument("--repo", help="GitHub repo URL")
    parser.add_argument("--branch", default="main", help="Branch name")

    args = parser.parse_args()
    info = load_version_info()

    if args.action == "version":
        print(f"RE-Tube v{info.get('current_version', '1.0.0')}")
        print(f"Last update: {info.get('last_update', 'Never')}")

    elif args.action == "init":
        repo = args.repo or info.get("repo_url", "")
        if not repo:
            print("Repo URL gerekli: --repo https://github.com/user/repo.git")
            sys.exit(1)
        ok, msg = init_repo(repo, args.branch)
        info["repo_url"] = repo
        info["branch"] = args.branch
        save_version_info(info)
        print(f"{'OK' if ok else 'HATA'}: {msg}")

    elif args.action == "check":
        repo = args.repo or info.get("repo_url", "")
        if not repo:
            print("Repo URL ayarlanmamis. Once 'init' calistirin.")
            sys.exit(1)
        has, local, remote = check_for_updates(repo, args.branch)
        info["last_check"] = datetime.now().isoformat()
        save_version_info(info)
        if has:
            changelog = get_update_changelog(args.branch)
            print(f"Guncelleme mevcut! ({local} -> {remote})")
            if changelog:
                print(f"Degisiklikler:\n{changelog}")
        else:
            print(f"Guncel ({local})")

    elif args.action == "update":
        repo = args.repo or info.get("repo_url", "")
        if not repo:
            print("Repo URL ayarlanmamis. Once 'init' calistirin.")
            sys.exit(1)
        init_repo(repo, args.branch)
        ok, msg = apply_update(args.branch)
        print(msg)
