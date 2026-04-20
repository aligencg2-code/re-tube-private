"""Tests for pipeline.cost — usage tracking, aggregation, time-windowed queries."""

import json
from datetime import datetime, timezone, timedelta


def test_record_appends_entry(tmp_path, monkeypatch):
    from pipeline import cost
    monkeypatch.setattr(cost, "USAGE_DIR", tmp_path)

    cost.record(job_id="q1", stage="voiceover", category="tts",
                provider_key="elevenlabs", amount_usd=0.12, units="60s")

    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1
    line = files[0].read_text(encoding="utf-8").strip()
    rec = json.loads(line)
    assert rec["job_id"] == "q1"
    assert rec["amount_usd"] == 0.12
    assert rec["category"] == "tts"
    assert rec["provider"] == "elevenlabs"


def test_estimated_cost_from_catalog():
    from pipeline import cost
    # elevenlabs cost_60s = 0.12
    assert cost.estimated_cost("tts", "elevenlabs", seconds=60) == 0.12
    assert cost.estimated_cost("tts", "elevenlabs", seconds=30) == 0.06
    assert cost.estimated_cost("tts", "edge_tts", seconds=60) == 0.0
    # Unknown provider returns 0
    assert cost.estimated_cost("tts", "nonexistent", seconds=60) == 0.0


def test_record_estimated_computes_and_records(tmp_path, monkeypatch):
    from pipeline import cost
    monkeypatch.setattr(cost, "USAGE_DIR", tmp_path)

    amt = cost.record_estimated(job_id="q1", stage="voiceover",
                                category="tts", provider_key="elevenlabs",
                                seconds=30)
    assert amt == 0.06

    rec = json.loads(list(tmp_path.glob("*.jsonl"))[0].read_text(encoding="utf-8").strip())
    assert rec["amount_usd"] == 0.06
    assert rec["units"] == "30.0s"


def test_summary_totals_and_breakdown(tmp_path, monkeypatch):
    from pipeline import cost
    monkeypatch.setattr(cost, "USAGE_DIR", tmp_path)

    cost.record(job_id="q1", stage="tts", category="tts",
                provider_key="elevenlabs", amount_usd=0.12)
    cost.record(job_id="q1", stage="image", category="image",
                provider_key="imagen4", amount_usd=0.24)
    cost.record(job_id="q2", stage="tts", category="tts",
                provider_key="elevenlabs", amount_usd=0.12)

    s = cost.summary(days=30)
    assert s["total_usd"] == round(0.12 + 0.24 + 0.12, 4)
    assert s["job_count"] == 2
    # Provider breakdown sorted desc
    assert list(s["by_provider"].keys())[0] == "elevenlabs"
    assert s["by_provider"]["elevenlabs"] == 0.24
    assert s["by_provider"]["imagen4"] == 0.24
    assert s["by_category"]["tts"] == 0.24
    assert s["by_category"]["image"] == 0.24


def test_summary_daily_series_zero_filled(tmp_path, monkeypatch):
    from pipeline import cost
    monkeypatch.setattr(cost, "USAGE_DIR", tmp_path)

    cost.record(job_id="q1", stage="tts", category="tts",
                provider_key="elevenlabs", amount_usd=0.50)

    s = cost.summary(days=7)
    assert len(s["daily_series"]) == 7
    # Today should have the 0.50; others 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_entry = next(d for d in s["daily_series"] if d["date"] == today)
    assert today_entry["usd"] == 0.5


def test_month_to_date_and_today(tmp_path, monkeypatch):
    from pipeline import cost
    monkeypatch.setattr(cost, "USAGE_DIR", tmp_path)

    cost.record(job_id="q1", stage="tts", category="tts",
                provider_key="elevenlabs", amount_usd=0.30)

    assert cost.today_usd() == 0.3
    assert cost.month_to_date_usd() >= 0.3


def test_corrupt_line_ignored(tmp_path, monkeypatch):
    from pipeline import cost
    monkeypatch.setattr(cost, "USAGE_DIR", tmp_path)

    # Write a valid record, then append a garbage line
    cost.record(job_id="q1", stage="tts", category="tts",
                provider_key="elevenlabs", amount_usd=0.15)
    mf = list(tmp_path.glob("*.jsonl"))[0]
    with open(mf, "a") as f:
        f.write("not-json\n{broken\n")

    s = cost.summary(days=30)
    assert s["total_usd"] == 0.15  # garbage skipped


def test_per_job_costs_aggregates(tmp_path, monkeypatch):
    from pipeline import cost
    monkeypatch.setattr(cost, "USAGE_DIR", tmp_path)

    cost.record(job_id="q_alpha", stage="tts", category="tts",
                provider_key="elevenlabs", amount_usd=0.12)
    cost.record(job_id="q_alpha", stage="image", category="image",
                provider_key="imagen4", amount_usd=0.24)
    cost.record(job_id="q_beta", stage="tts", category="tts",
                provider_key="elevenlabs", amount_usd=0.05)

    jobs = cost.per_job_costs(limit=10)
    alpha = next(j for j in jobs if j["job_id"] == "q_alpha")
    beta = next(j for j in jobs if j["job_id"] == "q_beta")
    assert alpha["total_usd"] == 0.36
    assert beta["total_usd"] == 0.05


def test_record_never_raises_on_disk_error(tmp_path, monkeypatch):
    """cost.record must be best-effort — pipeline MUST NOT crash on logging fail."""
    from pipeline import cost
    # Point to a non-writable path (e.g. a file not a dir). Should not raise.
    bad_path = tmp_path / "no-dir-will-be-file"
    bad_path.write_text("x")  # now it's a file, not a dir
    monkeypatch.setattr(cost, "USAGE_DIR", bad_path)

    # Must not raise
    cost.record(job_id="q", stage="tts", category="tts",
                provider_key="x", amount_usd=1.0)
