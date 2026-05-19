"""B-roll generation — supports Veo, Imagen 4, Gemini Imagen, DALL-E 3, GPT Image 1,
Stability SD3/SDXL, Flux (BFL + fal.ai), Ideogram, Recraft, Leonardo, Replicate,
plus Pexels stock and a solid-colour fallback as last resort.
"""

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


@with_retry(max_retries=2, base_delay=2.0)
def _generate_image_imagen4(prompt: str, output_path: Path, api_key: str,
                            model: str = "imagen-4.0-generate-001"):
    """Generate image via Imagen 4 predict API."""
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict",
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        json={
            "instances": [{"prompt": prompt}],
            "parameters": {"sampleCount": 1, "aspectRatio": "9:16"},
        },
        timeout=90,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Imagen 4 {r.status_code}: {r.text[:200]}")
    predictions = r.json().get("predictions", [])
    if not predictions:
        raise RuntimeError("Imagen 4: no image returned")
    img_b64 = predictions[0].get("bytesBase64Encoded", "")
    if not img_b64:
        raise RuntimeError("Imagen 4: empty image data")
    output_path.write_bytes(base64.b64decode(img_b64))


@with_retry(max_retries=2, base_delay=2.0)
def _generate_image_dalle(prompt: str, output_path: Path, api_key: str, hd: bool = False):
    """Generate image via OpenAI DALL-E 3."""
    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1792" if hd else "1024x1024",
            "quality": "hd" if hd else "standard",
        },
        timeout=90,
    )
    if r.status_code != 200:
        raise RuntimeError(f"DALL-E {r.status_code}: {r.text[:200]}")

    img_url = r.json()["data"][0]["url"]
    img_data = requests.get(img_url, timeout=60).content
    output_path.write_bytes(img_data)


@with_retry(max_retries=2, base_delay=2.0)
def _generate_image_gpt_image_1(prompt: str, output_path: Path, api_key: str,
                                portrait: bool = True):
    """Generate image via OpenAI GPT Image 1 (returns base64 directly)."""
    size = "1024x1536" if portrait else "1024x1024"
    r = requests.post(
        "https://api.openai.com/v1/images/generations",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "gpt-image-1",
            "prompt": prompt,
            "n": 1,
            "size": size,
        },
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(f"GPT Image 1 {r.status_code}: {r.text[:200]}")

    data = r.json().get("data", [])
    if not data:
        raise RuntimeError("GPT Image 1: empty response")

    entry = data[0]
    if "b64_json" in entry and entry["b64_json"]:
        output_path.write_bytes(base64.b64decode(entry["b64_json"]))
    elif "url" in entry and entry["url"]:
        img_data = requests.get(entry["url"], timeout=60).content
        output_path.write_bytes(img_data)
    else:
        raise RuntimeError("GPT Image 1: no image data in response")


@with_retry(max_retries=2, base_delay=2.0)
def _generate_image_stability_sd3(prompt: str, output_path: Path, api_key: str,
                                  model: str = "sd3-large", aspect: str = "9:16"):
    """Generate image via Stability AI Stable Diffusion 3 v2beta API."""
    r = requests.post(
        "https://api.stability.ai/v2beta/stable-image/generate/sd3",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "image/*",
        },
        files={"none": ""},
        data={
            "prompt": prompt,
            "model": model,
            "aspect_ratio": aspect,
            "output_format": "png",
        },
        timeout=120,
    )
    if r.status_code != 200:
        detail = r.text[:200] if r.text else "no body"
        raise RuntimeError(f"Stability SD3 {r.status_code}: {detail}")
    output_path.write_bytes(r.content)


@with_retry(max_retries=2, base_delay=2.0)
def _generate_image_stability_sdxl(prompt: str, output_path: Path, api_key: str,
                                   width: int = 832, height: int = 1216):
    """Generate image via Stability AI SDXL v1 API."""
    r = requests.post(
        "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "text_prompts": [{"text": prompt, "weight": 1.0}],
            "cfg_scale": 7,
            "height": height,
            "width": width,
            "samples": 1,
            "steps": 30,
        },
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Stability SDXL {r.status_code}: {r.text[:200]}")
    artifacts = r.json().get("artifacts", [])
    if not artifacts:
        raise RuntimeError("Stability SDXL: empty response")
    output_path.write_bytes(base64.b64decode(artifacts[0]["base64"]))


def _generate_image_flux_bfl(prompt: str, output_path: Path, api_key: str,
                             model: str = "flux-pro-1.1",
                             width: int = 768, height: int = 1344):
    """Generate image via Black Forest Labs Flux API (async: submit → poll → download)."""
    # Map provider key → BFL endpoint slug
    endpoint = "flux-pro-1.1-ultra" if model.endswith("ultra") else "flux-pro-1.1"
    submit = requests.post(
        f"https://api.bfl.ml/v1/{endpoint}",
        headers={
            "x-key": api_key,
            "Content-Type": "application/json",
            "accept": "application/json",
        },
        json={
            "prompt": prompt,
            "width": width,
            "height": height,
            "safety_tolerance": 2,
            "output_format": "png",
        },
        timeout=30,
    )
    if submit.status_code not in (200, 201):
        raise RuntimeError(f"Flux BFL submit {submit.status_code}: {submit.text[:200]}")
    task_id = submit.json().get("id")
    if not task_id:
        raise RuntimeError("Flux BFL: no task id returned")

    for _ in range(40):  # 40 * 3s = 120s max
        time.sleep(3)
        poll = requests.get(
            "https://api.bfl.ml/v1/get_result",
            headers={"x-key": api_key, "accept": "application/json"},
            params={"id": task_id},
            timeout=15,
        )
        if poll.status_code != 200:
            continue
        body = poll.json()
        status = body.get("status", "")
        if status == "Ready":
            sample_url = body.get("result", {}).get("sample")
            if not sample_url:
                raise RuntimeError("Flux BFL: ready but no sample URL")
            img = requests.get(sample_url, timeout=60)
            if img.status_code != 200:
                raise RuntimeError(f"Flux BFL download {img.status_code}")
            output_path.write_bytes(img.content)
            return
        if status in ("Error", "Request Moderated", "Content Moderated"):
            raise RuntimeError(f"Flux BFL: {status}")
    raise RuntimeError("Flux BFL: timeout after 120s")


@with_retry(max_retries=2, base_delay=2.0)
def _generate_image_flux_fal(prompt: str, output_path: Path, api_key: str,
                             model: str = "flux/dev"):
    """Generate image via fal.ai Flux (sync via fal.run)."""
    slug = "fal-ai/flux/schnell" if model.endswith("schnell") else "fal-ai/flux/dev"
    r = requests.post(
        f"https://fal.run/{slug}",
        headers={
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "prompt": prompt,
            "image_size": "portrait_16_9",
            "num_images": 1,
            "enable_safety_checker": True,
        },
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Flux fal.ai {r.status_code}: {r.text[:200]}")
    images = r.json().get("images", [])
    if not images:
        raise RuntimeError("Flux fal.ai: empty response")
    img_url = images[0].get("url")
    if not img_url:
        raise RuntimeError("Flux fal.ai: no image URL")
    img = requests.get(img_url, timeout=60)
    if img.status_code != 200:
        raise RuntimeError(f"Flux fal.ai download {img.status_code}")
    output_path.write_bytes(img.content)


@with_retry(max_retries=2, base_delay=2.0)
def _generate_image_ideogram(prompt: str, output_path: Path, api_key: str,
                             turbo: bool = False, aspect: str = "ASPECT_9_16"):
    """Generate image via Ideogram V2."""
    r = requests.post(
        "https://api.ideogram.ai/generate",
        headers={"Api-Key": api_key, "Content-Type": "application/json"},
        json={
            "image_request": {
                "prompt": prompt,
                "model": "V_2_TURBO" if turbo else "V_2",
                "aspect_ratio": aspect,
                "magic_prompt_option": "AUTO",
            }
        },
        timeout=90,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Ideogram {r.status_code}: {r.text[:200]}")
    data = r.json().get("data", [])
    if not data:
        raise RuntimeError("Ideogram: empty response")
    img_url = data[0].get("url")
    if not img_url:
        raise RuntimeError("Ideogram: no image URL")
    img = requests.get(img_url, timeout=60)
    if img.status_code != 200:
        raise RuntimeError(f"Ideogram download {img.status_code}")
    output_path.write_bytes(img.content)


@with_retry(max_retries=2, base_delay=2.0)
def _generate_image_recraft(prompt: str, output_path: Path, api_key: str,
                            size: str = "1024x1820"):
    """Generate image via Recraft V3 (OpenAI-style API)."""
    r = requests.post(
        "https://external.api.recraft.ai/v1/images/generations",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"prompt": prompt, "model": "recraftv3", "size": size, "n": 1},
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Recraft {r.status_code}: {r.text[:200]}")
    data = r.json().get("data", [])
    if not data:
        raise RuntimeError("Recraft: empty response")
    img_url = data[0].get("url")
    if not img_url:
        raise RuntimeError("Recraft: no image URL")
    img = requests.get(img_url, timeout=60)
    if img.status_code != 200:
        raise RuntimeError(f"Recraft download {img.status_code}")
    output_path.write_bytes(img.content)


def _generate_image_leonardo(prompt: str, output_path: Path, api_key: str,
                             model_id: str = "6b645e3a-d64f-4341-a6d8-7a3690fbf042",
                             width: int = 832, height: int = 1472):
    """Generate image via Leonardo Phoenix (async: submit → poll → download)."""
    submit = requests.post(
        "https://cloud.leonardo.ai/api/rest/v1/generations",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "prompt": prompt,
            "modelId": model_id,
            "width": width,
            "height": height,
            "num_images": 1,
            "alchemy": False,
        },
        timeout=30,
    )
    if submit.status_code not in (200, 201):
        raise RuntimeError(f"Leonardo submit {submit.status_code}: {submit.text[:200]}")
    gen_id = submit.json().get("sdGenerationJob", {}).get("generationId")
    if not gen_id:
        raise RuntimeError("Leonardo: no generation id")

    for _ in range(40):  # 40 * 3s = 120s max
        time.sleep(3)
        poll = requests.get(
            f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}",
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            timeout=15,
        )
        if poll.status_code != 200:
            continue
        gen = poll.json().get("generations_by_pk", {})
        if gen.get("status") == "COMPLETE":
            imgs = gen.get("generated_images", [])
            if not imgs:
                raise RuntimeError("Leonardo: complete but no images")
            img_url = imgs[0].get("url")
            if not img_url:
                raise RuntimeError("Leonardo: no image URL")
            img = requests.get(img_url, timeout=60)
            if img.status_code != 200:
                raise RuntimeError(f"Leonardo download {img.status_code}")
            output_path.write_bytes(img.content)
            return
        if gen.get("status") == "FAILED":
            raise RuntimeError("Leonardo: generation failed")
    raise RuntimeError("Leonardo: timeout after 120s")


def _generate_image_replicate(prompt: str, output_path: Path, api_key: str,
                              model: str = "black-forest-labs/flux-schnell"):
    """Generate image via Replicate (sync via Prefer: wait header)."""
    r = requests.post(
        f"https://api.replicate.com/v1/models/{model}/predictions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Prefer": "wait=120",
        },
        json={
            "input": {
                "prompt": prompt,
                "aspect_ratio": "9:16",
                "output_format": "png",
                "num_outputs": 1,
            }
        },
        timeout=180,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Replicate {r.status_code}: {r.text[:200]}")
    body = r.json()
    output = body.get("output")
    # Output can be a string URL or a list of URLs
    if isinstance(output, list):
        img_url = output[0] if output else None
    else:
        img_url = output
    if not img_url:
        raise RuntimeError("Replicate: no output URL")
    img = requests.get(img_url, timeout=60)
    if img.status_code != 200:
        raise RuntimeError(f"Replicate download {img.status_code}")
    output_path.write_bytes(img.content)


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

    Supported providers:
    - veo_*: Google Veo AI video clips (returns .mp4 files)
    - imagen4 / imagen4_fast / imagen4_ultra: Google Imagen 4
    - gemini_imagen / gemini_flash_img: Gemini native image generation
    - dalle3 / dalle3_hd: OpenAI DALL-E 3
    - gpt_image_1: OpenAI GPT Image 1
    - sd3_large / sd3_medium / sdxl: Stability AI
    - flux_pro / flux_pro_ultra: Black Forest Labs Flux (BFL API)
    - flux_dev / flux_schnell: Flux via fal.ai
    - ideogram_v2 / ideogram_turbo: Ideogram
    - recraft_v3: Recraft V3
    - leonardo_phoenix: Leonardo Phoenix
    - replicate: Replicate (defaults to Flux Schnell)
    - pexels / pixabay / unsplash: stock photos

    If the selected provider's API key is missing or the call fails, we
    log a clear warning and fall back to Pexels (if its key is set), and
    finally to a solid-colour frame so the pipeline never aborts.

    When veo_* is selected, returns .mp4 files — assemble.py handles
    both image and video inputs.
    """
    from .config import load_config, PROVIDERS

    config = load_config()
    image_provider = config.get("providers", {}).get("image", "pexels")
    provider_info = PROVIDERS.get("image", {}).get(image_provider, {})
    model = provider_info.get("model")
    provider_name = provider_info.get("name", image_provider)
    needs_key = provider_info.get("needs_key")

    # Resolve every API key once up front
    gemini_key = get_gemini_key()
    openai_key = _get_key("OPENAI_API_KEY")
    pexels_key = _get_key("PEXELS_API_KEY")
    stability_key = _get_key("STABILITY_API_KEY")
    bfl_key = _get_key("BFL_API_KEY")
    fal_key = _get_key("FAL_API_KEY")
    ideogram_key = _get_key("IDEOGRAM_API_KEY")
    recraft_key = _get_key("RECRAFT_API_KEY")
    leonardo_key = _get_key("LEONARDO_API_KEY")
    replicate_key = _get_key("REPLICATE_API_KEY")

    # Up-front warning: paid provider selected but its key is missing.
    # This avoids the "OpenAI is selected but it uses Pexels" surprise.
    key_lookup = {
        "OPENAI_API_KEY": openai_key,
        "GEMINI_API_KEY": gemini_key,
        "STABILITY_API_KEY": stability_key,
        "BFL_API_KEY": bfl_key,
        "FAL_API_KEY": fal_key,
        "IDEOGRAM_API_KEY": ideogram_key,
        "RECRAFT_API_KEY": recraft_key,
        "LEONARDO_API_KEY": leonardo_key,
        "REPLICATE_API_KEY": replicate_key,
        "PEXELS_API_KEY": pexels_key,
        "PIXABAY_API_KEY": _get_key("PIXABAY_API_KEY"),
        "UNSPLASH_API_KEY": _get_key("UNSPLASH_API_KEY"),
    }
    if needs_key and not key_lookup.get(needs_key):
        log(
            f"[broll] WARNING: selected provider '{provider_name}' "
            f"({image_provider}) needs {needs_key} but it is not set. "
            "Falling back to Pexels/solid-colour. Add the key in Settings → API Keys."
        )

    orientation = "portrait" if height > width else "landscape"
    frames = []
    # Track how many frames the SELECTED paid provider actually produced
    # (so cost.py doesn't bill the user for Pexels fallbacks).
    paid_provider_frames = 0

    for i, prompt in enumerate(prompts):
        success = False

        # Provider: Veo (AI video generation)
        if image_provider.startswith("veo") and gemini_key:
            out_path = out_dir / f"broll_{i}.mp4"
            try:
                veo_model = model or "veo-2.0-generate-001"
                log(f"Generating b-roll video {i+1}/{len(prompts)} via {provider_name}...")
                _generate_video_veo(prompt, out_path, gemini_key, duration=5, aspect=aspect, model=veo_model)
                frames.append(out_path)
                success = True
            except Exception as e:
                log(f"Veo failed for clip {i+1}: {e}")

        # Provider: Imagen 4 (predict API)
        if not success and image_provider.startswith("imagen4") and gemini_key:
            out_path = out_dir / f"broll_{i}.png"
            try:
                imagen_model = model or "imagen-4.0-generate-001"
                log(f"Generating b-roll image {i+1}/{len(prompts)} via {provider_name}...")
                _generate_image_imagen4(prompt, out_path, gemini_key, model=imagen_model)
                _resize_to_format(out_path, width, height)
                frames.append(out_path)
                success = True
            except Exception as e:
                log(f"Imagen 4 failed for frame {i+1}: {e}")

        # Provider: Gemini Imagen (native image generation)
        if not success and image_provider.startswith("gemini") and gemini_key:
            out_path = out_dir / f"broll_{i}.png"
            try:
                log(f"Generating b-roll image {i+1}/{len(prompts)} via {provider_name}...")
                _generate_image_gemini(prompt, out_path, gemini_key)
                _resize_to_format(out_path, width, height)
                frames.append(out_path)
                success = True
            except Exception as e:
                log(f"Gemini Imagen failed for frame {i+1}: {e}")

        # Provider: DALL-E 3
        if not success and image_provider.startswith("dalle") and openai_key:
            out_path = out_dir / f"broll_{i}.png"
            try:
                hd = image_provider == "dalle3_hd"
                log(f"Generating b-roll image {i+1}/{len(prompts)} via {provider_name}...")
                _generate_image_dalle(prompt, out_path, openai_key, hd=hd)
                _resize_to_format(out_path, width, height)
                frames.append(out_path)
                success = True
            except Exception as e:
                log(f"DALL-E failed for frame {i+1}: {e}")

        # Provider: OpenAI GPT Image 1
        if not success and image_provider == "gpt_image_1" and openai_key:
            out_path = out_dir / f"broll_{i}.png"
            try:
                log(f"Generating b-roll image {i+1}/{len(prompts)} via {provider_name}...")
                _generate_image_gpt_image_1(prompt, out_path, openai_key,
                                            portrait=(height > width))
                _resize_to_format(out_path, width, height)
                frames.append(out_path)
                success = True
            except Exception as e:
                log(f"GPT Image 1 failed for frame {i+1}: {e}")

        # Provider: Stability AI SD3 family
        if not success and image_provider in ("sd3_large", "sd3_medium") and stability_key:
            out_path = out_dir / f"broll_{i}.png"
            try:
                sd_model = "sd3-large" if image_provider == "sd3_large" else "sd3-medium"
                log(f"Generating b-roll image {i+1}/{len(prompts)} via {provider_name}...")
                _generate_image_stability_sd3(prompt, out_path, stability_key,
                                              model=sd_model, aspect=aspect)
                _resize_to_format(out_path, width, height)
                frames.append(out_path)
                success = True
            except Exception as e:
                log(f"Stability SD3 failed for frame {i+1}: {e}")

        # Provider: Stability SDXL
        if not success and image_provider == "sdxl" and stability_key:
            out_path = out_dir / f"broll_{i}.png"
            try:
                log(f"Generating b-roll image {i+1}/{len(prompts)} via {provider_name}...")
                # SDXL only accepts dimensions in 64px steps; portrait 832x1216.
                _generate_image_stability_sdxl(prompt, out_path, stability_key,
                                               width=832, height=1216)
                _resize_to_format(out_path, width, height)
                frames.append(out_path)
                success = True
            except Exception as e:
                log(f"Stability SDXL failed for frame {i+1}: {e}")

        # Provider: Flux (Black Forest Labs)
        if not success and image_provider in ("flux_pro", "flux_pro_ultra") and bfl_key:
            out_path = out_dir / f"broll_{i}.png"
            try:
                bfl_model = "flux-pro-1.1-ultra" if image_provider == "flux_pro_ultra" else "flux-pro-1.1"
                log(f"Generating b-roll image {i+1}/{len(prompts)} via {provider_name}...")
                _generate_image_flux_bfl(prompt, out_path, bfl_key, model=bfl_model)
                _resize_to_format(out_path, width, height)
                frames.append(out_path)
                success = True
            except Exception as e:
                log(f"Flux BFL failed for frame {i+1}: {e}")

        # Provider: Flux (fal.ai dev/schnell)
        if not success and image_provider in ("flux_dev", "flux_schnell") and fal_key:
            out_path = out_dir / f"broll_{i}.png"
            try:
                fal_model = "flux/schnell" if image_provider == "flux_schnell" else "flux/dev"
                log(f"Generating b-roll image {i+1}/{len(prompts)} via {provider_name}...")
                _generate_image_flux_fal(prompt, out_path, fal_key, model=fal_model)
                _resize_to_format(out_path, width, height)
                frames.append(out_path)
                success = True
            except Exception as e:
                log(f"Flux fal.ai failed for frame {i+1}: {e}")

        # Provider: Ideogram
        if not success and image_provider in ("ideogram_v2", "ideogram_turbo") and ideogram_key:
            out_path = out_dir / f"broll_{i}.png"
            try:
                aspect_tag = "ASPECT_9_16" if height > width else "ASPECT_16_9"
                log(f"Generating b-roll image {i+1}/{len(prompts)} via {provider_name}...")
                _generate_image_ideogram(
                    prompt, out_path, ideogram_key,
                    turbo=(image_provider == "ideogram_turbo"),
                    aspect=aspect_tag,
                )
                _resize_to_format(out_path, width, height)
                frames.append(out_path)
                success = True
            except Exception as e:
                log(f"Ideogram failed for frame {i+1}: {e}")

        # Provider: Recraft V3
        if not success and image_provider == "recraft_v3" and recraft_key:
            out_path = out_dir / f"broll_{i}.png"
            try:
                size = "1024x1820" if height > width else "1820x1024"
                log(f"Generating b-roll image {i+1}/{len(prompts)} via {provider_name}...")
                _generate_image_recraft(prompt, out_path, recraft_key, size=size)
                _resize_to_format(out_path, width, height)
                frames.append(out_path)
                success = True
            except Exception as e:
                log(f"Recraft failed for frame {i+1}: {e}")

        # Provider: Leonardo Phoenix
        if not success and image_provider == "leonardo_phoenix" and leonardo_key:
            out_path = out_dir / f"broll_{i}.png"
            try:
                log(f"Generating b-roll image {i+1}/{len(prompts)} via {provider_name}...")
                _generate_image_leonardo(prompt, out_path, leonardo_key)
                _resize_to_format(out_path, width, height)
                frames.append(out_path)
                success = True
            except Exception as e:
                log(f"Leonardo failed for frame {i+1}: {e}")

        # Provider: Replicate gateway
        if not success and image_provider == "replicate" and replicate_key:
            out_path = out_dir / f"broll_{i}.png"
            try:
                log(f"Generating b-roll image {i+1}/{len(prompts)} via {provider_name}...")
                _generate_image_replicate(prompt, out_path, replicate_key)
                _resize_to_format(out_path, width, height)
                frames.append(out_path)
                success = True
            except Exception as e:
                log(f"Replicate failed for frame {i+1}: {e}")

        # Anything that succeeded above came from the selected paid/free provider.
        # Track it so we only charge for frames the selected provider actually made.
        if success:
            paid_provider_frames += 1

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

    # Cost tracking — only bill the user for frames the selected paid
    # provider actually produced. Pexels fallbacks and solid-colour
    # fallbacks must NOT be billed as if the paid provider ran.
    try:
        from . import cost as _cost
        is_stock = image_provider in ("pexels", "pixabay", "unsplash")
        if not is_stock and paid_provider_frames > 0:
            # cost_60s in PROVIDERS catalog is "per 60s of final video" —
            # assume ~10s of video per Ken-Burns frame.
            video_seconds = paid_provider_frames * 10
            _cost.record_estimated(
                job_id=None, stage="broll",
                category=("video" if image_provider.startswith("veo") else "image"),
                provider_key=image_provider, seconds=video_seconds, model=model,
                extra={
                    "frames": paid_provider_frames,
                    "total_requested": len(prompts),
                    "aspect": aspect,
                },
            )
        if not is_stock and paid_provider_frames < len(prompts):
            # Surface partial-fallback so the customer knows why some
            # frames look like stock photos.
            fallback_count = len(prompts) - paid_provider_frames
            log(
                f"[broll] {fallback_count}/{len(prompts)} frame(s) fell back to "
                f"Pexels/solid-colour because '{provider_name}' could not produce them. "
                "Check API key, quota, or content policy."
            )
    except Exception:
        pass

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
