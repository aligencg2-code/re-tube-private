"""YouTube API upload + thumbnail + captions."""

from pathlib import Path

from .config import get_youtube_token_path, write_secret_file
from .log import log
from .retry import with_retry


@with_retry(max_retries=2, base_delay=5.0)
def upload_to_youtube(
    video_path: Path,
    draft: dict,
    srt_path: Path = None,
    lang: str = "en",
    thumbnail_path: Path = None,
    token_path_override: str = None,
    publish_at: str | None = None,
    privacy_status: str = "private",
    playlist_id: str | None = None,
) -> str:
    """Upload video to YouTube with metadata, captions, and optional thumbnail.

    Scheduled publish: pass `publish_at` as ISO-8601 UTC string (e.g.
    "2026-04-21T09:00:00Z"). YouTube requires privacyStatus=private together
    with a publishAt in the future; YouTube flips it to public at that time.

    Immediate publish: set publish_at=None and privacy_status to one of
    "public", "unlisted", or "private".
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    if token_path_override and Path(token_path_override).exists():
        token_path = Path(token_path_override)
    else:
        token_path = get_youtube_token_path()
    creds = Credentials.from_authorized_user_file(str(token_path))
    if creds.expired:
        if creds.refresh_token:
            creds.refresh(Request())
            write_secret_file(token_path, creds.to_json())
        else:
            raise RuntimeError(
                "YouTube OAuth token is expired and has no refresh token.\n"
                "Re-run: python3 scripts/setup_youtube_oauth.py"
            )

    youtube = build("youtube", "v3", credentials=creds)
    log(f"Uploading {video_path.name}...")

    # Scheduled publish: YouTube requires privacy=private + publishAt in future
    if publish_at:
        status_block = {
            "privacyStatus": "private",
            "publishAt": publish_at,
            "selfDeclaredMadeForKids": False,
        }
        log(f"Scheduled for publish at {publish_at} (UTC)")
    else:
        status_block = {"privacyStatus": privacy_status, "selfDeclaredMadeForKids": False}

    body = {
        "snippet": {
            "title": draft.get("youtube_title", draft["news"])[:100],
            "description": draft.get("youtube_description", ""),
            "tags": draft.get("youtube_tags", "").split(","),
            "categoryId": "20",
            "defaultLanguage": lang,
            "defaultAudioLanguage": lang,
        },
        "status": status_block,
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            log(f"Upload progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    url = f"https://youtu.be/{video_id}"
    log(f"Uploaded: {url}")

    # Upload SRT if available
    if srt_path and srt_path.exists():
        try:
            youtube.captions().insert(
                part="snippet",
                body={
                    "snippet": {
                        "videoId": video_id,
                        "language": lang,
                        "name": lang.upper(),
                        "isDraft": False,
                    }
                },
                media_body=MediaFileUpload(str(srt_path), mimetype="application/octet-stream"),
            ).execute()
            log("Captions uploaded.")
        except Exception as e:
            log(f"Caption upload failed: {e}")

    # Upload thumbnail if available
    if thumbnail_path and thumbnail_path.exists():
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/png"),
            ).execute()
            log("Thumbnail uploaded.")
        except Exception as e:
            log(f"Thumbnail upload failed: {e}")

    # Auto-add to playlist if requested
    if playlist_id:
        try:
            youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id},
                    }
                },
            ).execute()
            log(f"Added to playlist {playlist_id}")
            try:
                from . import audit as _audit
                _audit.log("playlist_added", target=video_id,
                           details={"playlist_id": playlist_id})
            except Exception:
                pass
        except Exception as e:
            log(f"Playlist add failed: {e}")

    # Audit the upload itself
    try:
        from . import audit as _audit
        _audit.log(
            "video_scheduled" if publish_at else "video_uploaded",
            target=video_id,
            details={
                "url": url, "title": (draft.get("youtube_title") or "")[:80],
                "privacy": privacy_status if not publish_at else "scheduled",
                "publish_at": publish_at,
                "lang": lang,
            },
        )
    except Exception:
        pass

    return url
