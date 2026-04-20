"""Tests for Closing tier features — demo, scheduler, revenue, QR, SSE, telegram."""

import json
import time
from datetime import datetime, timezone, timedelta


# ────────────────────────────────────────────────────────────
# DEMO MODE (#25)
# ────────────────────────────────────────────────────────────
def test_demo_preset_is_safe():
    from pipeline import demo_mode
    r = demo_mode.is_demo_preset_safe()
    assert r["safe"] is True
    assert r["issues"] == []


def test_demo_picks_random_topic():
    from pipeline import demo_mode
    seen = set()
    for _ in range(20):
        seen.add(demo_mode.pick_random_topic("tr"))
    assert len(seen) > 1  # randomness works


def test_demo_start_creates_job(tmp_path, monkeypatch):
    from pipeline import demo_mode, queue as q
    monkeypatch.setattr(q, "QUEUE_DIR", tmp_path / "queue")

    r = demo_mode.start_demo(topic="Demo topic", lang="tr")
    assert r["job_id"]
    jobs = q.list_jobs()
    assert len(jobs) == 1
    assert jobs[0]["topic"] == "Demo topic"
    assert (jobs[0].get("extra") or {}).get("demo_mode") is True


# ────────────────────────────────────────────────────────────
# SCHEDULER (#27 gece modu)
# ────────────────────────────────────────────────────────────
def test_schedule_create_and_list(tmp_path, monkeypatch):
    from pipeline import scheduler
    monkeypatch.setattr(scheduler, "SCHEDULES_FILE", tmp_path / "schedules.json")

    s = scheduler.create_schedule(
        name="Sabah yayınları",
        kind="cron",
        topics=["Topic A", "Topic B"],
        hours_utc=["09:00", "12:00", "18:00"],
    )
    assert s["name"] == "Sabah yayınları"
    assert s["kind"] == "cron"
    assert scheduler.list_schedules()[0]["id"] == s["id"]


def test_schedule_cron_fires_at_target_hour(tmp_path, monkeypatch):
    from pipeline import scheduler, queue as q
    monkeypatch.setattr(scheduler, "SCHEDULES_FILE", tmp_path / "schedules.json")
    monkeypatch.setattr(q, "QUEUE_DIR", tmp_path / "queue")

    scheduler.create_schedule(
        name="Test", kind="cron",
        topics=["Morning topic"],
        hours_utc=["09:00"],
    )

    # At 09:00 UTC → fires
    t = datetime(2026, 4, 20, 9, 0, 0, tzinfo=timezone.utc)
    fired = scheduler.tick(now=t)
    assert len(fired) == 1
    assert len(q.list_jobs()) == 1

    # Same minute → does NOT fire again (anti-duplicate)
    fired2 = scheduler.tick(now=t)
    assert fired2 == []


def test_schedule_cron_skips_wrong_hour(tmp_path, monkeypatch):
    from pipeline import scheduler, queue as q
    monkeypatch.setattr(scheduler, "SCHEDULES_FILE", tmp_path / "schedules.json")
    monkeypatch.setattr(q, "QUEUE_DIR", tmp_path / "queue")

    scheduler.create_schedule(
        name="Test", kind="cron",
        topics=["T"], hours_utc=["09:00"],
    )
    # 10:00 — not a target hour
    t = datetime(2026, 4, 20, 10, 0, 0, tzinfo=timezone.utc)
    fired = scheduler.tick(now=t)
    assert fired == []


def test_schedule_burst_fires_multiple(tmp_path, monkeypatch):
    from pipeline import scheduler, queue as q
    monkeypatch.setattr(scheduler, "SCHEDULES_FILE", tmp_path / "schedules.json")
    monkeypatch.setattr(q, "QUEUE_DIR", tmp_path / "queue")

    s = scheduler.create_schedule(
        name="Gece modu",
        kind="burst",
        topics=["T1", "T2", "T3", "T4", "T5"],
        count_per_burst=3,
    )
    r = scheduler.run_burst(s["id"])
    assert len(r["queued"]) == 3
    assert len(q.list_jobs()) == 3


def test_schedule_toggle_disables(tmp_path, monkeypatch):
    from pipeline import scheduler
    monkeypatch.setattr(scheduler, "SCHEDULES_FILE", tmp_path / "schedules.json")

    s = scheduler.create_schedule(
        name="X", kind="cron", topics=["a"], hours_utc=["00:00"],
    )
    assert scheduler.toggle_schedule(s["id"], False)
    # Disabled → tick at the right hour does nothing
    t = datetime(2026, 4, 20, 0, 0, 0, tzinfo=timezone.utc)
    assert scheduler.tick(now=t) == []


def test_schedule_delete(tmp_path, monkeypatch):
    from pipeline import scheduler
    monkeypatch.setattr(scheduler, "SCHEDULES_FILE", tmp_path / "schedules.json")

    s = scheduler.create_schedule(
        name="X", kind="cron", topics=["a"], hours_utc=["00:00"],
    )
    assert scheduler.delete_schedule(s["id"]) is True
    assert scheduler.list_schedules() == []


def test_schedule_daily_rotates_topics(tmp_path, monkeypatch):
    from pipeline import scheduler, queue as q
    monkeypatch.setattr(scheduler, "SCHEDULES_FILE", tmp_path / "schedules.json")
    monkeypatch.setattr(q, "QUEUE_DIR", tmp_path / "queue")

    s = scheduler.create_schedule(
        name="Daily rotate",
        kind="daily_topic_pool",
        topics=["Day1", "Day2", "Day3"],
    )
    scheduler.run_burst(s["id"])
    scheduler.run_burst(s["id"])
    scheduler.run_burst(s["id"])

    # Three distinct topics should have been picked in rotation
    topics = [j["topic"] for j in q.list_jobs()]
    assert set(topics) == {"Day1", "Day2", "Day3"}


# ────────────────────────────────────────────────────────────
# REVENUE ESTIMATE (#29)
# ────────────────────────────────────────────────────────────
def test_revenue_basic_estimate():
    from pipeline import revenue_estimate as re
    r = re.estimate(views=100_000, niche="technology", country="US",
                     duration_sec=180)
    assert r["earnings_usd"] > 0
    # Tech US: ~$4.50 × 1.5 × 0.65 = ~$4.39 per 1000 monetized views
    # 100K views × 65% monetization × $4.39/1000 ≈ $285
    # (we use approximate bounds)
    assert 100 < r["earnings_usd"] < 500
    assert r["is_short"] is False


def test_revenue_shorts_penalty():
    from pipeline import revenue_estimate as re
    r_short = re.estimate(views=100_000, niche="technology",
                           country="US", duration_sec=45)
    r_long = re.estimate(views=100_000, niche="technology",
                          country="US", duration_sec=180)
    assert r_short["is_short"] is True
    assert r_long["is_short"] is False
    # Shorts should earn dramatically less
    assert r_short["earnings_usd"] < r_long["earnings_usd"] / 3


def test_revenue_country_multiplier():
    from pipeline import revenue_estimate as re
    us = re.estimate(views=100_000, country="US", duration_sec=180)
    tr = re.estimate(views=100_000, country="TR", duration_sec=180)
    # US pays way more than TR
    assert us["earnings_usd"] > tr["earnings_usd"] * 2


def test_revenue_monthly_forecast():
    from pipeline import revenue_estimate as re
    r = re.forecast_monthly(videos_per_month=30, avg_views_per_video=50_000,
                             niche="finance_crypto", country="US",
                             duration_sec=120)
    assert r["monthly_earnings_usd"] > 0
    assert r["annual_earnings_usd"] == round(r["monthly_earnings_usd"] * 12, 2)


def test_revenue_unknown_niche_falls_back_to_general():
    from pipeline import revenue_estimate as re
    r = re.estimate(views=10_000, niche="imaginary_niche",
                     country="default", duration_sec=120)
    assert r["earnings_usd"] > 0  # didn't crash, used general


# ────────────────────────────────────────────────────────────
# QR PREVIEW (#26)
# ────────────────────────────────────────────────────────────
def test_qr_build_job_url():
    from pipeline import qr_preview
    assert qr_preview.build_job_url("http://localhost:8501/", "q_abc") == \
        "http://localhost:8501/?page=Queue&job=q_abc"


def test_qr_generation_gracefully_handles_missing_lib():
    """If qrcode not installed, generate_qr_png returns None."""
    from pipeline import qr_preview
    # Test actual behavior — whether lib is installed or not, must return bytes or None
    result = qr_preview.generate_qr_png("https://test.com")
    assert result is None or isinstance(result, bytes)


def test_qr_data_uri_roundtrip():
    from pipeline.qr_preview import as_data_uri
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    uri = as_data_uri(png_bytes)
    assert uri.startswith("data:image/png;base64,")


# ────────────────────────────────────────────────────────────
# SSE REAL-TIME (#30)
# ────────────────────────────────────────────────────────────
def test_sse_subscribe_and_emit():
    from pipeline import sse_server

    sub_id, q = sse_server.subscribe()
    try:
        sse_server.emit("job.created", {"id": "q_xyz", "status": "pending"})

        # Event should land in the queue
        payload = q.get(timeout=1.0)
        assert payload["event"] == "job.created"
        assert payload["data"]["id"] == "q_xyz"
    finally:
        sse_server.unsubscribe(sub_id)


def test_sse_multiple_subscribers_receive_same_event():
    from pipeline import sse_server

    s1, q1 = sse_server.subscribe()
    s2, q2 = sse_server.subscribe()
    try:
        sse_server.emit("job.status_changed", {"id": "q", "status": "done"})
        p1 = q1.get(timeout=1.0)
        p2 = q2.get(timeout=1.0)
        assert p1["data"]["id"] == p2["data"]["id"] == "q"
    finally:
        sse_server.unsubscribe(s1)
        sse_server.unsubscribe(s2)


def test_sse_unsubscribe_removes():
    from pipeline import sse_server

    pre = sse_server.subscriber_count()
    sub_id, _ = sse_server.subscribe()
    assert sse_server.subscriber_count() == pre + 1
    sse_server.unsubscribe(sub_id)
    assert sse_server.subscriber_count() == pre


def test_sse_format_wire():
    from pipeline.sse_server import format_sse
    payload = {"event": "job.done", "data": {"id": "abc"}, "ts": 1.0}
    wire = format_sse(payload).decode("utf-8")
    assert "event: job.done" in wire
    assert '"id": "abc"' in wire
    # SSE events end with blank line
    assert wire.endswith("\n\n")


# ────────────────────────────────────────────────────────────
# TELEGRAM BOT (#28) — command handler unit-tested with fakes
# ────────────────────────────────────────────────────────────
def test_telegram_unauthorized_user_blocked(monkeypatch):
    from pipeline import telegram_bot
    sent = []
    monkeypatch.setattr(telegram_bot, "_send",
                         lambda token, chat, text, parse_mode=None: sent.append((chat, text)) or True)

    telegram_bot._handle_command(
        bot_token="FAKE", chat_id=111, user_id=999,
        text="/yap NASA", allowed_users=[123, 456],
    )
    assert sent
    assert "yetkin" in sent[0][1].lower()


def test_telegram_yap_enqueues_job(tmp_path, monkeypatch):
    from pipeline import telegram_bot, queue as q
    monkeypatch.setattr(q, "QUEUE_DIR", tmp_path / "queue")
    sent = []
    monkeypatch.setattr(telegram_bot, "_send",
                         lambda token, chat, text, parse_mode=None: sent.append(text) or True)

    telegram_bot._handle_command(
        bot_token="FAKE", chat_id=111, user_id=123,
        text="/yap Tesla robotaxi launch", allowed_users=None,
    )
    jobs = q.list_jobs()
    assert len(jobs) == 1
    assert "Tesla robotaxi launch" in jobs[0]["topic"]
    assert any("Kuyruğa eklendi" in s for s in sent)


def test_telegram_durum_returns_job_status(tmp_path, monkeypatch):
    from pipeline import telegram_bot, queue as q
    monkeypatch.setattr(q, "QUEUE_DIR", tmp_path / "queue")
    sent = []
    monkeypatch.setattr(telegram_bot, "_send",
                         lambda token, chat, text, parse_mode=None: sent.append(text) or True)

    job = q.enqueue(topic="Status test", lang="tr", mode="full")
    telegram_bot._handle_command(
        bot_token="FAKE", chat_id=111, user_id=123,
        text=f"/durum {job['id']}", allowed_users=None,
    )
    assert any("Status test" in s for s in sent)


def test_telegram_kuyruk_lists_jobs(tmp_path, monkeypatch):
    from pipeline import telegram_bot, queue as q
    monkeypatch.setattr(q, "QUEUE_DIR", tmp_path / "queue")
    sent = []
    monkeypatch.setattr(telegram_bot, "_send",
                         lambda token, chat, text, parse_mode=None: sent.append(text) or True)

    q.enqueue(topic="A", lang="tr", mode="full")
    q.enqueue(topic="B", lang="tr", mode="full")

    telegram_bot._handle_command(
        bot_token="FAKE", chat_id=111, user_id=123,
        text="/kuyruk", allowed_users=None,
    )
    # Both topics should appear in the response
    full = "\n".join(sent)
    assert "A" in full and "B" in full
