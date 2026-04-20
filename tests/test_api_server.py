"""Tests for api_server — token management + HTTP endpoints via raw sockets."""

import json
import socket
import time
import urllib.request
import urllib.error


def test_issue_token_creates_persistent_record(tmp_path, monkeypatch):
    from pipeline import api_server as api
    monkeypatch.setattr(api, "TOKENS_FILE", tmp_path / "tokens.json")

    tok = api.issue_token("Customer A", scopes=["jobs:write"])
    assert tok.startswith("rt_")
    assert len(tok) > 20

    # Verified
    ok, name = api._verify_token(f"Bearer {tok}")
    assert ok is True
    assert name == "Customer A"


def test_revoked_token_fails_verification(tmp_path, monkeypatch):
    from pipeline import api_server as api
    monkeypatch.setattr(api, "TOKENS_FILE", tmp_path / "tokens.json")

    tok = api.issue_token("Customer B")
    api.revoke_token(tok)

    ok, name = api._verify_token(f"Bearer {tok}")
    assert ok is False
    assert name is None


def test_unknown_token_fails(tmp_path, monkeypatch):
    from pipeline import api_server as api
    monkeypatch.setattr(api, "TOKENS_FILE", tmp_path / "tokens.json")

    ok, _ = api._verify_token("Bearer rt_fake_12345")
    assert ok is False


def test_missing_bearer_prefix_fails(tmp_path, monkeypatch):
    from pipeline import api_server as api
    monkeypatch.setattr(api, "TOKENS_FILE", tmp_path / "tokens.json")

    tok = api.issue_token("X")
    # Without "Bearer " prefix → rejected
    ok, _ = api._verify_token(tok)
    assert ok is False


def test_list_tokens_hides_raw_secret(tmp_path, monkeypatch):
    from pipeline import api_server as api
    monkeypatch.setattr(api, "TOKENS_FILE", tmp_path / "tokens.json")

    tok = api.issue_token("Safe")
    metas = api.list_tokens()
    assert len(metas) == 1
    # The full token must not appear in the listing
    for m in metas:
        assert tok not in m["token_preview"]
        assert m["token_preview"].endswith("…")


def _get_free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _http(method, url, body=None, headers=None):
    req = urllib.request.Request(url, method=method, data=body,
                                  headers=headers or {})
    try:
        resp = urllib.request.urlopen(req, timeout=5)
        return (resp.status, json.loads(resp.read().decode()))
    except urllib.error.HTTPError as e:
        try:
            return (e.code, json.loads(e.read().decode()))
        except Exception:
            return (e.code, {})


def test_server_endpoints_end_to_end(tmp_path, monkeypatch):
    """Full round-trip against a live server on a free port."""
    from pipeline import api_server as api
    from pipeline import queue as qmod
    monkeypatch.setattr(api, "TOKENS_FILE", tmp_path / "tokens.json")
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path / "queue")

    port = _get_free_port()
    tok = api.issue_token("Tester")
    api.start(port=port, host="127.0.0.1")
    try:
        time.sleep(0.3)  # server start

        base = f"http://127.0.0.1:{port}"

        # Health — no auth needed
        status, body = _http("GET", f"{base}/v1/health")
        assert status == 200
        assert body["ok"] is True

        # Missing auth on protected route
        status, body = _http("GET", f"{base}/v1/jobs")
        assert status == 401

        # With auth
        headers = {"Authorization": f"Bearer {tok}"}
        status, body = _http("GET", f"{base}/v1/jobs", headers=headers)
        assert status == 200
        assert "jobs" in body
        assert body["jobs"] == []

        # Create job
        payload = json.dumps({
            "topic": "API e2e test topic",
            "lang": "tr", "mode": "full",
        }).encode("utf-8")
        status, body = _http("POST", f"{base}/v1/jobs", body=payload,
                             headers={**headers, "Content-Type": "application/json"})
        assert status == 201
        assert body["status"] == "pending"
        assert body["id"].startswith("q")
        job_id = body["id"]

        # Fetch individual job
        status, body = _http("GET", f"{base}/v1/jobs/{job_id}", headers=headers)
        assert status == 200
        assert body["id"] == job_id
        assert body["topic"] == "API e2e test topic"

        # Stats
        status, body = _http("GET", f"{base}/v1/stats", headers=headers)
        assert status == 200
        assert "queue" in body

        # Cancel
        status, body = _http("POST", f"{base}/v1/jobs/{job_id}/cancel",
                             headers=headers, body=b"")
        assert status == 200
        assert body["status"] == "cancelled"

        # Unknown route
        status, _ = _http("GET", f"{base}/v1/nonsense", headers=headers)
        assert status == 404

    finally:
        api.stop()


def test_create_job_without_topic_returns_400(tmp_path, monkeypatch):
    from pipeline import api_server as api
    from pipeline import queue as qmod
    monkeypatch.setattr(api, "TOKENS_FILE", tmp_path / "tokens.json")
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path / "queue")

    port = _get_free_port()
    tok = api.issue_token("Tester")
    api.start(port=port, host="127.0.0.1")
    try:
        time.sleep(0.3)
        status, body = _http(
            "POST", f"http://127.0.0.1:{port}/v1/jobs",
            body=json.dumps({"lang": "tr"}).encode(),
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        )
        assert status == 400
        assert body["error"] == "missing_field"
    finally:
        api.stop()
