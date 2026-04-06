"""B-roll generation — Veo video > Gemini Imagen > Pexels stock > fallback."""

import base64
import re
import time
from pathlib import Path

import requests
from PIL import Image

from .config import VIDEO_WIDTH, VIDEO_HEIGHT, get_gemini_key, _get_key, run_cmd, extract_keywords
from .log import log
from .retry import with_retry


@with_retry(max_retries=3, base_delay=2.0)
def _generate_image_gemini(prompt: str, output_path: Path, api_key: str):
    """Generate image via Gemini native image generation."""
    url = (
        "https://generativelanguage.googleapis.com/v1beta"
        "/models/gemini-3-pro-image-preview:generateContent"
    )
    body = {
        "contents": [{"parts": [{"text": f"Generate an image: {prompt}"}]}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
    }
    r = requests.post(
        url, json=body, timeout=90,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
    )
    if r.status_code != 200:
        try:
            detail = r.json().get("error", {}).get("message", r.text[:200])
        except Exception:
            detail = r.text[:200]
        raise RuntimeError(f"Gemini API {r.status_code}: {detail}")
    data = r.json()
    for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        if "inlineData" in part:
            img_b64 = part["inlineData"]["data"]
            output_path.write_bytes(base64.b64decode(img_b64))
            return
    raise RuntimeError("No image in Gemini response")


def _generate_video_veo(prompt: str, output_path: Path, api_key: str,
                        duration: int = 5, aspect: str = "9:16",
                        model: str = "veo-2.0-generate-001") -> Path:
    """Generate a video clip via Google Veo (async: create -> poll -> download)."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta"
        f"/models/{model}:predictLongRunning"
    )

    body = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": aspect,
            "durationSeconds": duration,
        },
    }

    # Start operation
    r = requests.post(
        url, json=body, timeout=30,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
    )
    if r.status_code != 200:
        try:
            detail = r.json().get("error", {}).get("message", r.text[:200])
        except Exception:
            detail = r.text[:200]
        raise RuntimeError(f"Veo API {r.status_code}: {detail}")

    operation_name = r.json().get("name")
    if not operation_name:
        raise RuntimeError("Veo: no operation name returned")

    log(f"Veo operation started: {operation_name}")

    # Poll until done (max 5 minutes)
    poll_url = f"https://generativelanguage.googleapis.com/v1beta/{operation_name}"
    for attempt in range(60):  # 60 * 5s = 5 min max
        time.sleep(5)
        poll_r = requests.get(
            poll_url,
            headers={"x-goog-api-key": api_key},
            timeout=15,
        )
        if poll_r.status_code != 200:
            continue

        poll_data = poll_r.json()
        if poll_data.get("done"):
            # Extract video URI
            response = poll_data.get("response", {})
            samples = response.get("generateVideoResponse", {}).get("generatedSamples", [])
            if not samples:
                raise RuntimeError("Veo: no video in response")

            video_uri = samples[0].get("video", {}).get("uri", "")
            if not video_uri:
                raise RuntimeError("Veo: no video URI")

            # Download
            dl_url = f"{video_uri}&key={api_key}" if "?" in video_uri else f"{video_uri}?key={api_key}"
            dl_r = requests.get(dl_url, timeout=120)
            if dl_r.status_code != 200:
                raise RuntimeError(f"Veo download failed: {dl_r.status_code}")

            output_path.write_bytes(dl_r.content)
            log(f"Veo video saved: {output_path.name} ({len(dl_r.content) / 1024:.0f}KB)")
            return output_path

        # Log progress
        if attempt % 6 == 0:
            log(f"Veo: still generating... ({attempt * 5}s)")

    raise RuntimeError("Veo: timeout after 5 minutes")


def _search_pexels(query: str, output_path: Path, api_key: str, orientation: str = "portrait"):
    """Download a stock photo from Pexels API (free, high quality)."""
    r = requests.get(
        "https://api.pexels.com/v1/search",
        params={"query": query, "per_page": 5, "orientation": orientation},
        headers={"Authorization": api_key},
        timeout=15,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Pexels API {r.status_code}: {r.text[:200]}")

    photos = r.json().get("photos", [])
    if not photos:
        raise RuntimeError(f"No Pexels results for: {query}")

    # Pick a random photo from top results
    import random
    photo = random.choice(photos[:3])
    img_url = photo["src"]["portrait"]  # 800x1200 portrait

    img_r = requests.get(img_url, timeout=30)
    if img_r.status_code != 200:
        raise RuntimeError(f"Pexels download failed: {img_r.status_code}")

    output_path.write_bytes(img_r.content)
    log(f"Pexels photo: {photo.get('photographer', 'unknown')} — {photo['src']['portrait'][:60]}")


def _fallback_frame(i: int, out_dir: Path, width: int = VIDEO_WIDTH, height: int = VIDEO_HEIGHT) -> Path:
    """Solid colour fallback frame if all image sources fail."""
    colors = [(20, 20, 60), (40, 10, 40), (10, 30, 50)]
    img = Image.new("RGB", (width, height), colors[i % len(colors)])
    path = out_dir / f"broll_{i}.png"
    img.save(path)
    return path


def _extract_search_terms(prompt: str) -> str:
    """Extract useful search terms from an AI image prompt for stock photo search."""
    noise = {
        "cinematic", "dramatic", "stunning", "breathtaking", "awe-inspiring",
        "slow-motion", "wide", "shot", "close-up", "lens", "flare", "golden",
        "hour", "deep", "black", "high", "quality", "photorealistic", "4k", "8k",
        "epic", "scale", "detailed", "illustration", "style", "painting",
        "scene", "background", "lighting", "view", "angle", "heroic",
        "massive", "intense", "visible", "below", "above", "reflecting",
        "historical", "image", "photo", "video", "generate", "create",
    }
    # Clean punctuation and filter
    words = []
    for w in prompt.lower().replace(",", " ").replace(".", " ").split():
        w = w.strip("\"'()[]")
        if w and w not in noise and len(w) > 2 and not w.startswith("-"):
            words.append(w)
    # Take the most meaningful 4-5 words
    return " ".join(words[:5])


def _resize_to_format(img_path: Path, width: int = VIDEO_WIDTH, height: int = VIDEO_HEIGHT):
    """Resize/crop image to target dimensions."""
    img = Image.open(img_path).convert("RGB")
    target_w, target_h = width, height
    orig_w, orig_h = img.size
    scale = max(target_w / orig_w, target_h / orig_h)
    new_w, new_h = int(orig_w * scale), int(orig_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))
    img.save(img_path)


def generate_broll(prompts: list, out_dir: Path, aspect: str = "9:16",
                   width: int = 1080, height: int = 1920) -> list[Path]:
    """Generate b-roll based on config provider selection.

    Providers:
    - veo: Generate AI video clips via Google Veo (returns .mp4 files)
    - gemini_imagen: Generate AI images via Gemini (returns .png files)
    - pexels: Stock photos from Pexels (returns .png files)

    When veo is selected, returns .mp4 files directly — assemble.py
    should handle both image and video inputs.
    """
    from .config import load_config

    config = load_config()
    image_provider = config.get("providers", {}).get("image", "pexels")
    gemini_key = get_gemini_key()
    pexels_key = _get_key("PEXELS_API_KEY")
    orientation = "portrait" if height > width else "landscape"
    frames = []

    for i, prompt in enumerate(prompts):
        success = False

        # Provider: Veo (AI video generation)
        if image_provider == "veo" and gemini_key:
            out_path = out_dir / f"broll_{i}.mp4"
            try:
                log(f"Generating b-roll video {i+1}/{len(prompts)} via Veo...")
                _generate_video_veo(prompt, out_path, gemini_key, duration=5, aspect=aspect)
                frames.append(out_path)
                success = True
            except Exception as e:
                log(f"Veo failed for clip {i+1}: {e}")

        # Provider: Gemini Imagen (AI images)
        if not success and image_provider in ("gemini_imagen", "veo") and gemini_key:
            out_path = out_dir / f"broll_{i}.png"
            try:
                log(f"Generating b-roll image {i+1}/{len(prompts)} via Gemini Imagen...")
                _generate_image_gemini(prompt, out_path, gemini_key)
                _resize_to_format(out_path, width, height)
                frames.append(out_path)
                success = True
            except Exception as e:
                log(f"Gemini Imagen failed for frame {i+1}: {e}")

        # Provider: Pexels (stock photos — default or fallback)
        if not success and pexels_key:
            out_path = out_dir / f"broll_{i}.png"
            try:
                search_terms = _extract_search_terms(prompt)
                log(f"Fetching b-roll {i+1}/{len(prompts)} from Pexels: '{search_terms}'...")
                _search_pexels(search_terms, out_path, pexels_key, orientation=orientation)
                _resize_to_format(out_path, width, height)
                frames.append(out_path)
                success = True
            except Exception as e:
                log(f"Pexels failed for frame {i+1}: {e}")
                try:
                    broad_terms = " ".join(search_terms.split()[:2])
                    log(f"Retrying broader: '{broad_terms}'...")
                    _search_pexels(broad_terms, out_path, pexels_key, orientation=orientation)
                    _resize_to_format(out_path, width, height)
                    frames.append(out_path)
                    success = True
                except Exception:
                    pass

        # Final fallback
        if not success:
            out_path = out_dir / f"broll_{i}.png"
            log(f"Frame {i+1}: using color fallback")
            frames.append(_fallback_frame(i, out_dir, width, height))

    return frames


def animate_frame(img_path: Path, out_path: Path, duration: float, effect: str = "zoom_in",
                  width: int = VIDEO_WIDTH, height: int = VIDEO_HEIGHT):
    """Ken Burns animation on a single frame."""
    fps = 30
    frames = int(duration * fps)
    w, h = width, height

    if effect == "zoom_in":
        vf = (
            f"scale={int(w * 1.12)}:{int(h * 1.12)},"
            f"zoompan=z='1.12-0.12*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={w}x{h}:fps={fps}"
        )
    elif effect == "pan_right":
        vf = (
            f"scale={int(w * 1.15)}:{int(h * 1.15)},"
            f"zoompan=z=1.15:x='0.15*iw*on/{frames}':y='ih*0.075'"
            f":d={frames}:s={w}x{h}:fps={fps}"
        )
    else:  # zoom_out
        vf = (
            f"scale={int(w * 1.12)}:{int(h * 1.12)},"
            f"zoompan=z='1.0+0.12*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s={w}x{h}:fps={fps}"
        )

    run_cmd([
        "ffmpeg", "-loop", "1", "-i", str(img_path),
        "-vf", vf, "-t", str(duration), "-r", str(fps),
        "-pix_fmt", "yuv420p", str(out_path), "-y", "-loglevel", "quiet",
    ])
