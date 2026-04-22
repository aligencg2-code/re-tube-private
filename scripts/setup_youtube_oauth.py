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
  python3 scripts/setup_youtube_oauth.py --channel ayaz
  python3 scripts/setup_youtube_oauth.py --channel ayaz /path/to/client_secret.json
"""

import json
import os
import re
import stat
import sys
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",  # needed for captions; narrower than full youtube scope
]

SKILL_DIR  = Path.home() / ".youtube-shorts-pipeline"
TOKEN_PATH = SKILL_DIR / "youtube_token.json"

# Kanal ismi validator — sadece alnum, tire, altcizgi, bosluk kabul
_VALID_CHANNEL_NAME = re.compile(r"^[A-Za-z0-9_\- ]{1,40}$")


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


def validate_channel_name(name: str) -> tuple[bool, str]:
    """Validate channel name — reject path-like inputs.

    Returns (ok, error_message_or_empty).
    """
    if not name:
        return (False, "Kanal adi bos olamaz")
    # Windows path separators or drive letters
    if "\\" in name or "/" in name or ":" in name:
        return (False, (
            f"Kanal adi bir DOSYA YOLU olamaz!\n\n"
            f"  Girilen deger: {name}\n\n"
            f"Dogru kullanim:\n"
            f"  --channel ayaz          (sadece isim)\n"
            f"  --channel \"ana kanal\"   (boslukla)\n"
            f"  --channel muhammet_tv   (altcizgi ile)\n\n"
            f"YANLIS kullanimlar:\n"
            f"  --channel C:\\Users\\...   (dosya yolu)\n"
            f"  --channel /home/user/..  (Unix yolu)\n\n"
            f"IPUCU: Terminal'e dosya SURUKLEYEREK bir sey birakmayin.\n"
            f"       Sadece kanal icin basit bir isim yazin."
        ))
    # Reject anything weird
    if not _VALID_CHANNEL_NAME.match(name):
        return (False, (
            f"Kanal adi gecersiz karakter iceriyor: {name}\n\n"
            f"Kabul edilen karakterler: harf, rakam, tire, altcizgi, bosluk\n"
            f"Uzunluk: 1-40 karakter"
        ))
    return (True, "")


def validate_client_secret(path: str) -> tuple[bool, str]:
    """Validate client_secret path — must be an existing .json file."""
    p = Path(path)
    if not p.exists():
        return (False, f"Dosya bulunamadi: {path}")
    if p.is_dir():
        return (False, (
            f"Bu bir KLASOR, dosya degil: {path}\n\n"
            f"client_secret.json Google Cloud Console'dan indirilen bir\n"
            f".json dosyasi olmalidir. Dogrudan dosyanin yolunu girin."
        ))
    if p.suffix.lower() != ".json":
        return (False, f"Dosya .json uzantili olmali: {path}")
    # Basic JSON validity check
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not (isinstance(data, dict) and
                ("installed" in data or "web" in data)):
            return (False, (
                f"Bu dosya gecerli bir OAuth client_secret.json degil.\n"
                f"Google Cloud Console > Credentials > OAuth 2.0 Client ID\n"
                f"(Desktop app) -> DOWNLOAD JSON ile indirin."
            ))
    except json.JSONDecodeError:
        return (False, f"JSON dosyasi okunamadi / bozuk: {path}")
    except Exception as e:
        return (False, f"Dosya okuma hatasi: {e}")
    return (True, "")


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("[HATA] Eksik paket. Yuklemek icin:")
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

    # --- CHANNEL NAME VALIDATION ---
    if channel_name:
        ok, err = validate_channel_name(channel_name)
        if not ok:
            print()
            print("=" * 60)
            print("  [HATA] Kanal adi gecersiz!")
            print("=" * 60)
            print()
            print(err)
            print()
            sys.exit(1)

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
        print(f"Kanal: {channel_name}")

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
            print("client_secret.json dosyasi gerekli (Google Cloud'dan).")
            print("Adimlar:")
            print("  1. https://console.cloud.google.com")
            print("  2. APIs & Services -> Credentials")
            print("  3. Create Credentials -> OAuth 2.0 Client ID -> Desktop app")
            print("  4. DOWNLOAD JSON butonuyla indir")
            print()
            try:
                client_secrets = input("client_secret.json dosyasinin yolu: ").strip()
            except EOFError:
                print("[HATA] Input okunamadi ve client_secret*.json bulunamadi.")
                sys.exit(1)

    # Handle quoted paths (Windows drag-drop often wraps in double quotes)
    client_secrets = client_secrets.strip('"').strip("'")
    client_secrets = str(Path(client_secrets).expanduser())

    # --- CLIENT SECRET VALIDATION ---
    ok, err = validate_client_secret(client_secrets)
    if not ok:
        print()
        print("=" * 60)
        print("  [HATA] client_secret dosyasi problemi")
        print("=" * 60)
        print()
        print(err)
        print()
        sys.exit(1)

    print("\nTarayici aciliyor Google girisi icin...")
    print("(Acilmazsa asagidaki URL'yi kopyalayip manuel yapistirin)\n")
    try:
        flow = InstalledAppFlow.from_client_secrets_file(client_secrets, SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True)
    except Exception as e:
        print(f"\n[HATA] OAuth akisi basarisiz: {e}")
        print("\nOlasi sebepler:")
        print("  - client_secret.json bozuk veya wrong type (Desktop app olmali)")
        print("  - Google Cloud projeninde YouTube Data API v3 aktif degil")
        print("  - Tarayici acilmadi, URL kopyalamadiniz")
        sys.exit(1)

    # Token yazarken OneDrive klasorune denk gelirse daha net hata ver
    try:
        fd = os.open(str(token_save_path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(creds.to_json())
    except PermissionError as e:
        print(f"\n[HATA] Token kaydedilemedi: {e}")
        if "OneDrive" in str(token_save_path):
            print("\nSEBEP: OneDrive senkronize edilen klasorler bazi dosya")
            print("       islemlerini engelleyebiliyor.")
            print("\nCOZUM:")
            print("  1. Program klasorunu OneDrive DISINDA bir yere tasiyin")
            print("     (ornek: C:\\RE-Tube\\ veya D:\\RE-Tube\\)")
            print("  2. KURULUM.bat'i oradan calistirin")
            print("  3. Bu komutu tekrar deneyin")
        else:
            print("\nSEBEP: Dosyaya yazma izni yok.")
            print("\nCOZUM: Antivirus / Windows Defender engelliyor olabilir.")
            print("       Gecici olarak devre disi birakip tekrar deneyin.")
        sys.exit(1)
    except IsADirectoryError:
        print(f"\n[HATA] Hedef bir KLASOR, dosya degil: {token_save_path}")
        print("Bu genelde kanal adina yanlislikla dosya yolu koyuldugunda olur.")
        sys.exit(1)

    print(f"\n[OK] Token kaydedildi: {token_save_path}")
    print("\nBasarili! RE-Tube.bat ile paneli baslatip video uretebilirsin.")


if __name__ == "__main__":
    main()
