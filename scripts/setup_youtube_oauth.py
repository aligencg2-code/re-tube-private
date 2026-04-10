#!/usr/bin/env python3
"""
YouTube OAuth Setup
===================
Run once to authorise YouTube API access. Opens a browser window for
Google sign-in and saves the OAuth token to ~/.youtube-shorts-pipeline/youtube_token.json.

Prerequisites:
  1. Go to https://console.cloud.google.com
  2. Create a project (or use an existing one)
  3. Enable the YouTube Data API v3
  4. Create OAuth 2.0 credentials (Desktop app type)
  5. Download the client_secret.json file

Usage:
  python3 scripts/setup_youtube_oauth.py
"""

import json
import os
import stat
import sys
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",  # needed for captions; narrower than full youtube scope
]

SKILL_DIR  = Path.home() / ".youtube-shorts-pipeline"
TOKEN_PATH = SKILL_DIR / "youtube_token.json"


def find_client_secret() -> str | None:
    """Auto-detect client_secret*.json in project directory."""
    project_dir = Path(__file__).resolve().parent.parent
    candidates = list(project_dir.glob("client_secret*.json"))
    if candidates:
        return str(candidates[0])
    # Also check SKILL_DIR
    candidates = list(SKILL_DIR.glob("client_secret*.json"))
    if candidates:
        return str(candidates[0])
    return None


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Missing dependency. Install it with:")
        print("   pip install google-auth-oauthlib google-api-python-client")
        sys.exit(1)

    # Parse arguments - support both old style and new --channel style
    channel_name = None
    client_secret_arg = None

    # Check for --channel flag
    remaining_args = []
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--channel" and i + 1 < len(sys.argv):
            channel_name = sys.argv[i + 1]
            i += 2
        else:
            remaining_args.append(sys.argv[i])
            i += 1

    if remaining_args:
        client_secret_arg = remaining_args[0]

    # Determine token save path
    if channel_name:
        channel_dir = SKILL_DIR / "channels" / channel_name
        channel_dir.mkdir(parents=True, exist_ok=True)
        token_save_path = channel_dir / "youtube_token.json"
    else:
        token_save_path = TOKEN_PATH

    SKILL_DIR.mkdir(parents=True, exist_ok=True)

    print("YouTube OAuth Setup")
    print("=" * 50)
    if channel_name:
        print(f"Channel: {channel_name}")

    # Find client_secret.json
    client_secrets = None
    if client_secret_arg:
        client_secrets = client_secret_arg
    else:
        client_secrets = find_client_secret()
        if client_secrets:
            print(f"\n  Auto-detected: {client_secrets}")
        else:
            print()
            print("You need a client_secret.json from Google Cloud Console.")
            print("Steps:")
            print("  1. Go to https://console.cloud.google.com")
            print("  2. APIs & Services -> Credentials")
            print("  3. Create Credentials -> OAuth 2.0 Client ID -> Desktop app")
            print("  4. Download the JSON file")
            print()
            try:
                client_secrets = input("Path to your client_secret.json: ").strip()
            except EOFError:
                print("No input available and no client_secret*.json found.")
                sys.exit(1)

    client_secrets = str(Path(client_secrets).expanduser())

    if not Path(client_secrets).exists():
        print(f"[ERROR] File not found: {client_secrets}")
        sys.exit(1)

    print("\nOpening browser for Google sign-in...")
    print("(If the browser does not open, copy the URL from below and paste it manually)\n")
    flow = InstalledAppFlow.from_client_secrets_file(client_secrets, SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True)

    fd = os.open(str(token_save_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(creds.to_json())
    print(f"\n[OK] Token saved to {token_save_path}")
    print("\nYou're all set! You can now run the pipeline and upload videos.")


if __name__ == "__main__":
    main()
