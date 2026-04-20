"""CLI entry point — python -m pipeline."""

import argparse
import io
import sys
import time
from pathlib import Path

# Fix Windows console encoding for non-ASCII output (Turkish, Hindi, etc.)
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from .config import CONFIG_FILE, DRAFTS_DIR, MEDIA_DIR, FORMATS, DURATIONS, run_setup
from .log import log, set_verbose


def cmd_draft(args):
    from .draft import generate_draft
    from .state import PipelineState
    from . import topic_memory
    import json

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    job_id = str(int(time.time()))

    print(f"\n  Drafting: {args.news}\n")
    draft = generate_draft(args.news, getattr(args, "context", ""), getattr(args, "lang", "en"),
                           getattr(args, "format", "shorts"), getattr(args, "duration", "short"))
    draft["job_id"] = job_id

    out_path = DRAFTS_DIR / f"{job_id}.json"
    state = PipelineState(draft)
    state.complete_stage("research")
    state.complete_stage("draft")
    state.save(out_path)

    # Topic memory — record the finished draft so future enqueues can warn about duplicates
    try:
        topic_memory.remember(
            args.news, job_id=job_id,
            channel=getattr(args, "channel", None),
        )
    except Exception:
        pass  # memory failures never break the pipeline

    print(f"\n  Draft saved: {out_path}")
    print(f"\n  Script:\n{draft['script']}")
    print(f"\n  Title: {draft.get('youtube_title', '')}")
    print(f"\n  B-roll prompts:")
    for i, p in enumerate(draft.get("broll_prompts", [])):
        print(f"  {i+1}. {p}")

    return out_path


def cmd_produce(args):
    from .broll import generate_broll
    from .voiceover import generate_voiceover
    from .captions import generate_captions
    from .music import select_and_prepare_music
    from .assemble import assemble_video
    from .state import PipelineState
    import json
    import shutil

    draft_path = Path(args.draft)
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    job_id = draft["job_id"]
    lang = args.lang
    state = PipelineState(draft)

    # Resolve format and duration from draft (or defaults)
    fmt = draft.get("format", "shorts")
    dur = draft.get("duration", "short")
    fmt_cfg = FORMATS.get(fmt, FORMATS["shorts"])
    vid_w, vid_h = fmt_cfg["width"], fmt_cfg["height"]
    aspect = fmt_cfg["aspect"]

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    work_dir = MEDIA_DIR / f"work_{job_id}_{lang}"
    work_dir.mkdir(exist_ok=True)

    force = getattr(args, "force", False)
    script = getattr(args, "script", None) or (
        draft.get("script_hi") if lang == "hi" else draft.get("script")
    )

    print(f"\n  Producing {lang.upper()} video for job {job_id}")

    # B-roll
    if force or not state.is_done("broll"):
        frames = generate_broll(draft.get("broll_prompts", ["Cinematic landscape"] * 3), work_dir,
                               aspect=aspect, width=vid_w, height=vid_h)
        state.complete_stage("broll", {"frames": [str(f) for f in frames]})
    else:
        log("Skipping b-roll (already done)")
        frames = [Path(f) for f in state.get_artifact("broll", "frames", [])]

    # Voiceover
    if force or not state.is_done("voiceover"):
        vo_path = generate_voiceover(script, work_dir, lang)
        state.complete_stage("voiceover", {"path": str(vo_path)})
    else:
        log("Skipping voiceover (already done)")
        vo_path = Path(state.get_artifact("voiceover", "path"))

    # Whisper + Captions
    if force or not state.is_done("captions"):
        captions_result = generate_captions(vo_path, work_dir, lang)
        state.complete_stage("captions", {
            "srt_path": str(captions_result.get("srt_path", "")),
            "ass_path": str(captions_result.get("ass_path", "")),
        })
    else:
        log("Skipping captions (already done)")
        captions_result = {
            "srt_path": state.get_artifact("captions", "srt_path", ""),
            "ass_path": state.get_artifact("captions", "ass_path", ""),
        }

    # Music
    if force or not state.is_done("music"):
        music_result = select_and_prepare_music(vo_path, work_dir)
        state.complete_stage("music", {
            "track_path": str(music_result.get("track_path", "")),
            "duck_filter": music_result.get("duck_filter", ""),
        })
    else:
        log("Skipping music (already done)")
        music_result = {
            "track_path": state.get_artifact("music", "track_path", ""),
            "duck_filter": state.get_artifact("music", "duck_filter", ""),
        }

    # Assemble
    if force or not state.is_done("assemble"):
        video_path = assemble_video(
            frames=frames,
            voiceover=vo_path,
            out_dir=work_dir,
            job_id=job_id,
            lang=lang,
            ass_path=captions_result.get("ass_path"),
            music_path=music_result.get("track_path"),
            duck_filter=music_result.get("duck_filter"),
            video_width=vid_w,
            video_height=vid_h,
        )
        state.complete_stage("assemble", {"video_path": str(video_path)})
    else:
        log("Skipping assembly (already done)")
        video_path = Path(state.get_artifact("assemble", "video_path"))

    # Save SRT to media dir
    srt_path = captions_result.get("srt_path")
    if srt_path and Path(srt_path).exists():
        final_srt = MEDIA_DIR / f"pipeline_{job_id}_{lang}.srt"
        shutil.copy(srt_path, final_srt)
        draft[f"srt_{lang}"] = str(final_srt)

    draft[f"video_{lang}"] = str(video_path)
    state.save(draft_path)

    print(f"\n  Video: {video_path}")
    return video_path


def cmd_upload(args):
    from .upload import upload_to_youtube
    from .thumbnail import generate_thumbnail
    from .state import PipelineState
    from .config import get_youtube_token_path
    import json

    draft_path = Path(args.draft)
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    lang = args.lang
    state = PipelineState(draft)
    force = getattr(args, "force", False)

    video_path = Path(draft.get(f"video_{lang}", ""))
    srt_path_str = draft.get(f"srt_{lang}")
    srt_path = Path(srt_path_str) if srt_path_str else None

    if not video_path.exists():
        print(f"  No produced video found for lang={lang}. Run produce first.")
        sys.exit(1)

    # Thumbnail — single or A/B variants depending on draft flag
    thumb_path = None
    thumb_variants: list[dict] = []
    enable_ab = bool(draft.get("enable_ab") or draft.get("thumbnail_ab"))

    if force or not state.is_done("thumbnail"):
        try:
            if enable_ab:
                from .thumbnail import generate_thumbnail_variants
                thumb_variants = generate_thumbnail_variants(draft, MEDIA_DIR, count=3)
                if thumb_variants:
                    thumb_path = Path(thumb_variants[0]["path"])
                    state.complete_stage("thumbnail", {
                        "path": str(thumb_path),
                        "variants": thumb_variants,
                    })
            if not thumb_path:
                thumb_path = generate_thumbnail(draft, MEDIA_DIR)
                state.complete_stage("thumbnail", {"path": str(thumb_path)})
        except Exception as e:
            log(f"Thumbnail generation failed: {e} — uploading without thumbnail")
    else:
        thumb_p = state.get_artifact("thumbnail", "path", "")
        if thumb_p and Path(thumb_p).exists():
            thumb_path = Path(thumb_p)
        cached_variants = state.get_artifact("thumbnail", "variants", [])
        if cached_variants:
            thumb_variants = cached_variants

    # Upload
    if force or not state.is_done("upload"):
        token_override = getattr(args, "token_path", None)
        # Scheduled publish — either from CLI arg or from the draft itself (queue job may set it)
        publish_at = getattr(args, "publish_at", None) or draft.get("publish_at")
        privacy_status = getattr(args, "privacy", None) or draft.get("privacy_status") or "private"
        playlist_id = getattr(args, "playlist_id", None) or draft.get("playlist_id")
        url = upload_to_youtube(
            video_path, draft, srt_path, lang, thumb_path, token_override,
            publish_at=publish_at, privacy_status=privacy_status,
            playlist_id=playlist_id,
        )
        state.complete_stage("upload", {"url": url, "publish_at": publish_at,
                                          "privacy": privacy_status, "playlist_id": playlist_id})

        # A/B enrollment — if we have >1 variant, register the test
        if len(thumb_variants) > 1 and url:
            try:
                from . import thumbnail_ab
                video_id = url.rsplit("/", 1)[-1].split("?")[0]
                token_used = token_override or str(get_youtube_token_path())
                channel_hint = draft.get("channel")
                test_id = thumbnail_ab.create_test(
                    video_id=video_id,
                    variants=thumb_variants,
                    token_path=token_used,
                    channel=channel_hint,
                    rotation_hours=draft.get("ab_rotation_hours", 24),
                )
                log(f"A/B test registered (id={test_id}) with {len(thumb_variants)} variants")
            except Exception as e:
                log(f"A/B enrollment failed (ignored): {e}")
    else:
        url = state.get_artifact("upload", "url", "")
        log(f"Skipping upload (already done): {url}")

    draft[f"youtube_url_{lang}"] = url
    state.save(draft_path)
    print(f"\n  Live: {url}")
    return url


def cmd_run(args):
    draft_path = cmd_draft(args)
    if args.dry_run:
        print("  Dry run — skipping produce + upload")
        return

    # Monkey-patch args for produce/upload
    class ProduceArgs:
        draft = str(draft_path)
        lang = args.lang
        script = None
        force = False
        format = getattr(args, "format", "shorts")
        duration = getattr(args, "duration", "short")

    video_path = cmd_produce(ProduceArgs())

    class UploadArgs:
        draft = str(draft_path)
        lang = args.lang
        force = False
        token_path = getattr(args, "token_path", None)

    url = cmd_upload(UploadArgs())
    print(f"\n  Done! {url}")


def cmd_topics(args):
    region = getattr(args, "region", None)
    limit = getattr(args, "limit", 15)

    if region:
        # Direct Google Trends RSS for specific country
        from .topics.google_trends import GoogleTrendsSource
        source = GoogleTrendsSource({"geo": region})
        candidates = source.fetch_topics(limit=limit, geo=region)
    else:
        # Full multi-source discovery
        from .topics import TopicEngine
        engine = TopicEngine()
        candidates = engine.discover(limit=limit)

    if not candidates:
        print("  No topics found.")
        return

    region_label = f" ({region})" if region else ""
    print(f"\n  Trending topics{region_label} ({len(candidates)} found):\n")
    for i, topic in enumerate(candidates, 1):
        print(f"  {i:2d}. {topic.title}")
        if topic.summary:
            print(f"      {topic.summary[:100]}")


def main():
    if not CONFIG_FILE.exists():
        print("  First run detected. Running setup...")
        run_setup()

    parser = argparse.ArgumentParser(
        description="YouTube Shorts Pipeline v2 — AI-Native Content Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(dest="cmd")

    # draft
    p_draft = sub.add_parser("draft", help="Generate script + metadata")
    p_draft.add_argument("--news", required=False, help="Topic/news headline")
    p_draft.add_argument("--context", default="", help="Channel context")
    p_draft.add_argument("--discover", action="store_true", help="Use topic engine instead of --news")
    p_draft.add_argument("--auto-pick", action="store_true", help="Let Claude pick the best topic")
    p_draft.add_argument("--lang", default="en", choices=["en", "de", "hi", "tr"])
    p_draft.add_argument("--dry-run", action="store_true", help="Draft only, skip produce")
    p_draft.add_argument("--format", choices=["shorts", "video"], default="shorts", help="Video format: shorts (9:16) or video (16:9)")
    p_draft.add_argument("--duration", choices=["short", "3min", "5min", "10min"], default="short", help="Video duration preset")

    # produce
    p_produce = sub.add_parser("produce", help="Generate video from draft")
    p_produce.add_argument("--draft", required=True)
    p_produce.add_argument("--lang", default="en", choices=["en", "de", "hi", "tr"])
    p_produce.add_argument("--script", default=None, help="Override script text")
    p_produce.add_argument("--force", action="store_true", help="Redo all stages")
    p_produce.add_argument("--format", choices=["shorts", "video"], default="shorts", help="Video format (overrides draft)")
    p_produce.add_argument("--duration", choices=["short", "3min", "5min", "10min"], default="short", help="Video duration (overrides draft)")

    # upload
    p_upload = sub.add_parser("upload", help="Upload to YouTube")
    p_upload.add_argument("--draft", required=True)
    p_upload.add_argument("--lang", default="en", choices=["en", "de", "hi", "tr"])
    p_upload.add_argument("--force", action="store_true", help="Re-upload even if done")
    p_upload.add_argument("--token-path", default=None, help="Path to YouTube OAuth token")
    p_upload.add_argument("--publish-at", default=None, dest="publish_at",
                          help="ISO-8601 UTC timestamp to auto-publish (e.g. 2026-04-21T09:00:00Z). Video stays private until then.")
    p_upload.add_argument("--privacy", default=None, choices=["private", "unlisted", "public"],
                          help="Privacy when not scheduled (default: private)")
    p_upload.add_argument("--playlist-id", default=None, dest="playlist_id",
                          help="YouTube playlist ID to auto-add the video to")

    # run (full pipeline)
    p_run = sub.add_parser("run", help="Full pipeline: draft -> produce -> upload")
    p_run.add_argument("--news", required=False, help="Topic/news headline")
    p_run.add_argument("--lang", default="en", choices=["en", "de", "hi", "tr"])
    p_run.add_argument("--dry-run", action="store_true")
    p_run.add_argument("--context", default="")
    p_run.add_argument("--discover", action="store_true")
    p_run.add_argument("--auto-pick", action="store_true")
    p_run.add_argument("--format", choices=["shorts", "video"], default="shorts", help="Video format: shorts (9:16) or video (16:9)")
    p_run.add_argument("--duration", choices=["short", "3min", "5min", "10min"], default="short", help="Video duration preset")
    p_run.add_argument("--token-path", default=None, help="Path to YouTube OAuth token for channel selection")

    # topics
    p_topics = sub.add_parser("topics", help="Discover trending topics")
    p_topics.add_argument("--limit", type=int, default=15, help="Max topics to show")
    p_topics.add_argument("--region", default=None, help="Country code: TR, DE, GB, US, ES, IT")

    # queue
    p_queue = sub.add_parser("queue", help="Queue operations (add/list/cancel/clear)")
    p_queue.add_argument("action", choices=["add", "list", "cancel", "clear", "status"])
    p_queue.add_argument("--news", default=None)
    p_queue.add_argument("--context", default="")
    p_queue.add_argument("--lang", default="tr", choices=["en", "de", "hi", "tr"])
    p_queue.add_argument("--mode", default="full", choices=["full", "video", "draft"])
    p_queue.add_argument("--format", dest="video_format", default="shorts", choices=["shorts", "video"])
    p_queue.add_argument("--duration", default="short", choices=["short", "3min", "5min", "10min"])
    p_queue.add_argument("--channel", default=None)
    p_queue.add_argument("--id", default=None, help="Job id for cancel")

    # worker
    p_worker = sub.add_parser("worker", help="Start background queue worker (single instance)")
    p_worker.add_argument("--once", action="store_true", help="Process one job then exit")

    args = parser.parse_args()

    if args.verbose:
        set_verbose(True)

    if not args.cmd:
        parser.print_help()
        return

    # Handle --discover flag for draft/run
    if args.cmd in ("draft", "run") and getattr(args, "discover", False):
        from .topics import TopicEngine
        engine = TopicEngine()
        candidates = engine.discover(limit=15)
        if not candidates:
            print("  No trending topics found. Use --news instead.")
            sys.exit(1)

        if getattr(args, "auto_pick", False):
            args.news = engine.auto_pick(candidates)
            print(f"  Auto-picked: {args.news}")
        else:
            print("\n  Trending topics:\n")
            for i, t in enumerate(candidates, 1):
                print(f"  {i:2d}. [{t.source}] {t.title}")
            choice = input("\n  Pick a number (or enter custom topic): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(candidates):
                args.news = candidates[int(choice) - 1].title
            else:
                args.news = choice
    elif args.cmd in ("draft", "run") and not getattr(args, "news", None):
        print("  Error: --news or --discover required")
        sys.exit(1)

    if args.cmd == "draft":
        cmd_draft(args)
    elif args.cmd == "produce":
        cmd_produce(args)
    elif args.cmd == "upload":
        cmd_upload(args)
    elif args.cmd == "run":
        cmd_run(args)
    elif args.cmd == "topics":
        cmd_topics(args)
    elif args.cmd == "queue":
        cmd_queue(args)
    elif args.cmd == "worker":
        cmd_worker(args)


def cmd_queue(args):
    from . import queue as qmod
    act = args.action
    if act == "add":
        if not args.news:
            print("  Error: --news required for queue add")
            sys.exit(1)
        job = qmod.enqueue(
            topic=args.news,
            context=args.context,
            lang=args.lang,
            mode=args.mode,
            video_format=args.video_format,
            duration=args.duration,
            channel=args.channel,
        )
        print(f"  Queued: {job['id']}  [{job['topic']}]")
        print(f"  Status: {job['status']}")
    elif act == "list":
        jobs = qmod.list_jobs()
        if not jobs:
            print("  Queue empty.")
            return
        for j in jobs:
            print(f"  {j['id']}  {j['status']:<10} {j.get('progress_pct', 0):3d}%  {j['topic'][:60]}")
    elif act == "cancel":
        if not args.id:
            print("  Error: --id required")
            sys.exit(1)
        qmod.cancel_job(args.id)
        print(f"  Cancel signalled: {args.id}")
    elif act == "clear":
        import json
        for j in qmod.list_jobs(statuses=("done", "failed", "cancelled")):
            qmod.delete_job(j["id"])
        print("  Cleared finished jobs.")
    elif act == "status":
        import json as _json
        print(_json.dumps(qmod.counts(), indent=2))


def cmd_worker(args):
    from . import worker as wmod
    from . import queue as qmod
    if args.once:
        job = qmod.next_pending() or qmod.next_produced()
        if not job:
            print("  Queue empty.")
            return
        if not qmod.acquire_worker_lock():
            print("  Another worker is running.")
            return
        try:
            if job["status"] == "produced":
                wmod._run_upload_job(job)
            else:
                wmod.process_one(job)
        finally:
            qmod.release_worker_lock()
    else:
        wmod.drain_loop()


if __name__ == "__main__":
    main()
