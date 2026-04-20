"""Tiny REST API server for programmatic access.

Runs alongside the Streamlit panel on a separate port (default 8502).
Single dependency: stdlib `http.server` — no FastAPI/Flask needed.

Endpoints (all require `Authorization: Bearer <token>`):
    POST /v1/jobs              → create a job in the queue
    GET  /v1/jobs              → list recent jobs
    GET  /v1/jobs/{id}         → get single job status
    POST /v1/jobs/{id}/cancel  → cancel a queued job
    GET  /v1/health            → liveness probe (no auth)
    GET  /v1/stats             → queue counts + cost summary

API tokens are stored in SKILL_DIR/api_tokens.json as a dict
{token_string: {"name": "customer A", "created_at": "...", "scopes": [...]}}.

Webhook: if a job is submitted with `webhook_url`, the worker POSTs job
status updates to that URL on every status transition.
"""

from __future__ import annotations

import json
import secrets
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .config import SKILL_DIR


TOKENS_FILE = SKILL_DIR / "api_tokens.json"
DEFAULT_PORT = 8502


# ────────────────────────────────────────────────────────────
# Token storage
# ────────────────────────────────────────────────────────────
def _load_tokens() -> dict:
    if not TOKENS_FILE.exists():
        return {}
    try:
        return json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_tokens(tokens: dict) -> None:
    TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKENS_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


def issue_token(name: str, scopes: list[str] | None = None) -> str:
    """Mint a new API token, persist it, return the raw string."""
    token = "rt_" + secrets.token_urlsafe(32)
    tokens = _load_tokens()
    tokens[token] = {
        "name": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scopes": scopes or ["jobs:read", "jobs:write"],
        "revoked": False,
    }
    _save_tokens(tokens)
    try:
        from . import audit
        audit.log("apikey_added", target=name, details={"scopes": scopes})
    except Exception:
        pass
    return token


def revoke_token(token: str) -> bool:
    tokens = _load_tokens()
    if token not in tokens:
        return False
    tokens[token]["revoked"] = True
    _save_tokens(tokens)
    try:
        from . import audit
        audit.log("apikey_removed", target=tokens[token].get("name", ""))
    except Exception:
        pass
    return True


def list_tokens() -> list[dict]:
    """Return token metadata — NEVER the token string itself for existing ones."""
    out = []
    for tok, meta in _load_tokens().items():
        out.append({
            "token_preview": tok[:8] + "…",  # never show the raw token
            "name": meta.get("name"),
            "created_at": meta.get("created_at"),
            "scopes": meta.get("scopes", []),
            "revoked": meta.get("revoked", False),
        })
    return out


def _verify_token(auth_header: str | None) -> tuple[bool, str | None]:
    """Return (valid, token_name_or_none)."""
    if not auth_header or not auth_header.startswith("Bearer "):
        return (False, None)
    tok = auth_header[len("Bearer "):].strip()
    tokens = _load_tokens()
    meta = tokens.get(tok)
    if not meta or meta.get("revoked"):
        return (False, None)
    return (True, meta.get("name", "unknown"))


# ────────────────────────────────────────────────────────────
# Webhook sender (called from worker)
# ────────────────────────────────────────────────────────────
def send_webhook(url: str, payload: dict, *, timeout: float = 5.0) -> bool:
    """Fire-and-forget POST. Returns True on 2xx."""
    try:
        import requests
        r = requests.post(url, json=payload, timeout=timeout)
        return r.ok
    except Exception:
        return False


# ────────────────────────────────────────────────────────────
# HTTP handler
# ────────────────────────────────────────────────────────────
class _APIHandler(BaseHTTPRequestHandler):
    """Stdlib-only request dispatcher. Thread-safe via ThreadingHTTPServer."""

    def log_message(self, format, *args):
        # Silence default stderr spam; real logging goes via audit if needed
        return

    # ---- helpers ----
    def _json(self, status: int, body: dict) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _read_body(self) -> dict:
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n == 0:
                return {}
            raw = self.rfile.read(n).decode("utf-8", errors="replace")
            return json.loads(raw) if raw else {}
        except Exception:
            return {}

    def _require_auth(self) -> str | None:
        ok, name = _verify_token(self.headers.get("Authorization"))
        if not ok:
            self._json(401, {"error": "unauthorized",
                             "message": "valid Bearer token required"})
            return None
        return name

    # ---- routes ----
    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        if path == "/v1/health":
            self._json(200, {"ok": True, "ts": datetime.now(timezone.utc).isoformat()})
            return

        name = self._require_auth()
        if not name:
            return

        if path == "/v1/jobs":
            from . import queue as qmod
            jobs = qmod.list_jobs()
            self._json(200, {"jobs": [self._strip(j) for j in jobs[-100:]]})
            return

        if path == "/v1/stats":
            from . import queue as qmod, cost as cmod
            self._json(200, {
                "queue": qmod.counts(),
                "cost_last_30d_usd": cmod.summary(days=30)["total_usd"],
                "cost_today_usd": cmod.today_usd(),
                "cost_mtd_usd": cmod.month_to_date_usd(),
            })
            return

        if path.startswith("/v1/jobs/"):
            job_id = path[len("/v1/jobs/"):]
            from . import queue as qmod
            job = qmod.load_job(job_id)
            if not job:
                self._json(404, {"error": "not_found"})
                return
            self._json(200, self._strip(job))
            return

        self._json(404, {"error": "unknown_route", "path": path})

    def do_POST(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        name = self._require_auth()
        if not name:
            return

        body = self._read_body()

        if path == "/v1/jobs":
            topic = (body.get("topic") or "").strip()
            if not topic:
                self._json(400, {"error": "missing_field", "field": "topic"})
                return
            from . import queue as qmod
            job = qmod.enqueue(
                topic=topic,
                context=body.get("context", ""),
                lang=body.get("lang", "tr"),
                mode=body.get("mode", "full"),
                video_format=body.get("format", "shorts"),
                duration=body.get("duration", "short"),
                channel=body.get("channel"),
                publish_at=body.get("publish_at"),
                privacy_status=body.get("privacy", "private"),
                extra={"webhook_url": body.get("webhook_url"),
                       "api_creator": name},
            )
            try:
                from . import audit
                audit.log("job_queued", target=job["id"], actor=f"api:{name}",
                          details={"topic": topic[:60], "via": "api"})
            except Exception:
                pass
            self._json(201, {"id": job["id"], "status": "pending",
                             "created_at": job["created_at"]})
            return

        if path.startswith("/v1/jobs/") and path.endswith("/cancel"):
            job_id = path[len("/v1/jobs/"):-len("/cancel")]
            from . import queue as qmod
            result = qmod.cancel_job(job_id)
            if not result:
                self._json(404, {"error": "not_found"})
                return
            self._json(200, {"id": job_id, "status": result["status"]})
            return

        self._json(404, {"error": "unknown_route", "path": path})

    def do_OPTIONS(self):
        # CORS preflight
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    @staticmethod
    def _strip(job: dict) -> dict:
        """Return a trimmed job dict safe to expose over API."""
        return {
            "id": job.get("id"),
            "status": job.get("status"),
            "topic": job.get("topic"),
            "lang": job.get("lang"),
            "format": job.get("format"),
            "duration": job.get("duration"),
            "mode": job.get("mode"),
            "progress_pct": job.get("progress_pct", 0),
            "stage": job.get("stage"),
            "created_at": job.get("created_at"),
            "updated_at": job.get("updated_at"),
            "error": job.get("error"),
        }


# ────────────────────────────────────────────────────────────
# Server lifecycle — start/stop in a background thread
# ────────────────────────────────────────────────────────────
_server_instance: ThreadingHTTPServer | None = None
_server_thread: threading.Thread | None = None


def start(port: int = DEFAULT_PORT, host: str = "0.0.0.0") -> dict:
    """Start the API server in a background thread. Idempotent."""
    global _server_instance, _server_thread
    if _server_instance is not None:
        return {"running": True, "port": _server_instance.server_address[1],
                "already_running": True}
    _server_instance = ThreadingHTTPServer((host, port), _APIHandler)
    _server_thread = threading.Thread(
        target=_server_instance.serve_forever, name="retube-api",
        daemon=True,
    )
    _server_thread.start()
    return {"running": True, "port": port, "already_running": False}


def stop() -> bool:
    global _server_instance, _server_thread
    if _server_instance is None:
        return False
    _server_instance.shutdown()
    _server_instance.server_close()
    _server_instance = None
    _server_thread = None
    return True


def is_running() -> bool:
    return _server_instance is not None


def port() -> int | None:
    if _server_instance is None:
        return None
    return _server_instance.server_address[1]
