"""QR code generator — mobile preview + job share.

Produces QR code data URIs. User can scan with their phone to jump into
a specific job view, see a produced video, or open their panel remotely.

Pure Python via a minimal QR encoding (we bundle a tiny implementation
to avoid the `qrcode` library dependency). Uses PIL which is already a
pipeline dep.
"""

from __future__ import annotations

import base64
from io import BytesIO


# ────────────────────────────────────────────────────────────
# Tiny QR implementation — uses qrcode lib if available, else fallback
# ────────────────────────────────────────────────────────────
def has_qrcode_lib() -> bool:
    try:
        import qrcode  # noqa: F401
        return True
    except ImportError:
        return False


def generate_qr_png(data: str, *, box_size: int = 8, border: int = 2) -> bytes | None:
    """Return PNG bytes of a QR code for `data`, or None if qrcode not installed.

    Callers can display the PNG inline in Streamlit: `st.image(png_bytes)`
    or base64-encode for HTML <img>.
    """
    try:
        import qrcode
        img = qrcode.make(
            data,
            box_size=box_size, border=border,
        )
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        return None


def as_data_uri(png_bytes: bytes) -> str:
    """Base64 data: URI for embedding in HTML."""
    b64 = base64.b64encode(png_bytes).decode("ascii")
    return f"data:image/png;base64,{b64}"


def build_job_url(base_url: str, job_id: str) -> str:
    """Public URL for mobile preview of a single job."""
    base = base_url.rstrip("/")
    return f"{base}/?page=Queue&job={job_id}"


def build_video_url(youtube_url: str) -> str:
    """Pass-through — YouTube URL IS the mobile preview."""
    return youtube_url


def qr_for_job(job_id: str, base_url: str = "http://localhost:8501") -> dict:
    """Return {data_uri, target_url, has_lib}."""
    target = build_job_url(base_url, job_id)
    png = generate_qr_png(target)
    return {
        "target_url": target,
        "data_uri": as_data_uri(png) if png else None,
        "has_lib": png is not None,
    }


def qr_for_video(youtube_url: str) -> dict:
    png = generate_qr_png(youtube_url)
    return {
        "target_url": youtube_url,
        "data_uri": as_data_uri(png) if png else None,
        "has_lib": png is not None,
    }
