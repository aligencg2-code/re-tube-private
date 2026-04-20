"""Tests for batch CSV parsing logic.

Extracted from app.py's inline _parse_csv_rows so we can test in isolation.
Keep this function in sync with the one in app.py (both small and stable).
"""

import csv
import io


def _parse_csv_rows(text: str) -> list[dict]:
    text = text.strip()
    if not text:
        return []
    first = text.splitlines()[0].lower()
    has_header = "topic" in first and "," in first
    if has_header:
        reader = csv.DictReader(io.StringIO(text))
        return [{k.strip(): (v or "").strip() for k, v in row.items() if k} for row in reader if any(row.values())]
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",", 1)]
        out.append({"topic": parts[0], "context": parts[1] if len(parts) > 1 else ""})
    return out


def test_empty_returns_empty():
    assert _parse_csv_rows("") == []
    assert _parse_csv_rows("   \n  \n") == []


def test_plain_lines_one_topic_per_line():
    out = _parse_csv_rows("NASA launch\nAI news\nTesla robotaxi")
    assert len(out) == 3
    assert out[0] == {"topic": "NASA launch", "context": ""}
    assert out[2]["topic"] == "Tesla robotaxi"


def test_compact_topic_comma_context():
    out = _parse_csv_rows("NASA launch,Tech channel\nAI news,AI focused")
    assert out[0] == {"topic": "NASA launch", "context": "Tech channel"}
    assert out[1]["context"] == "AI focused"


def test_full_csv_header():
    csv_text = (
        "topic,context,lang,format,duration,mode\n"
        "NASA launch,Tech,tr,shorts,short,full\n"
        "AI regulation,,en,video,3min,video"
    )
    out = _parse_csv_rows(csv_text)
    assert len(out) == 2
    assert out[0] == {"topic": "NASA launch", "context": "Tech", "lang": "tr",
                      "format": "shorts", "duration": "short", "mode": "full"}
    assert out[1]["context"] == ""
    assert out[1]["format"] == "video"


def test_comments_ignored():
    out = _parse_csv_rows("# my topics\nNASA launch\n# another comment\nAI news")
    assert len(out) == 2
    assert out[0]["topic"] == "NASA launch"


def test_mixed_whitespace_tolerated():
    out = _parse_csv_rows("   NASA launch  \n\n\n  AI news  \n")
    assert len(out) == 2
    assert out[0]["topic"] == "NASA launch"
    assert out[1]["topic"] == "AI news"


def test_blank_csv_rows_skipped():
    csv_text = "topic,context\nNASA,Tech\n,\nAI,\n"
    out = _parse_csv_rows(csv_text)
    assert len(out) == 2
    topics = [r["topic"] for r in out]
    assert "NASA" in topics and "AI" in topics


def test_unicode_turkish_topic_preserved():
    out = _parse_csv_rows("Yapay zeka şirketleri çöktü,Teknoloji")
    assert out[0]["topic"] == "Yapay zeka şirketleri çöktü"
    assert out[0]["context"] == "Teknoloji"
