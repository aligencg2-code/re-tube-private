"""Tests for auto-translation fan-out."""

import json
import sys
import types


def test_supported_langs_includes_core():
    from pipeline.auto_translate import SUPPORTED_LANGS
    for lang in ["en", "tr", "de", "hi", "es", "fr"]:
        assert lang in SUPPORTED_LANGS


def test_translate_fields_falls_back_on_llm_failure(tmp_path, monkeypatch):
    from pipeline import auto_translate as at

    # Stub draft module to raise
    fake = types.ModuleType("pipeline.draft")
    fake._call_script_ai = lambda prompt: (_ for _ in ()).throw(RuntimeError("No API"))
    monkeypatch.setitem(sys.modules, "pipeline.draft", fake)
    try:
        out = at._translate_fields(
            source_lang="en", target_lang="tr",
            fields={"script": "Hello world", "youtube_title": "Title"},
        )
        # Returns original unchanged
        assert out["script"] == "Hello world"
        assert out["youtube_title"] == "Title"
    finally:
        sys.modules.pop("pipeline.draft", None)
        import importlib
        importlib.import_module("pipeline.draft")


def test_translate_fields_parses_llm_json(monkeypatch):
    from pipeline import auto_translate as at

    fake = types.ModuleType("pipeline.draft")
    fake._call_script_ai = lambda prompt: (
        '{"script": "Merhaba dünya", "youtube_title": "Başlık", '
        '"youtube_description": "Açıklama"}'
    )
    monkeypatch.setitem(sys.modules, "pipeline.draft", fake)
    try:
        out = at._translate_fields(
            source_lang="en", target_lang="tr",
            fields={
                "script": "Hello world",
                "youtube_title": "Title",
                "youtube_description": "Desc",
            },
        )
        assert out["script"] == "Merhaba dünya"
        assert out["youtube_title"] == "Başlık"
    finally:
        sys.modules.pop("pipeline.draft", None)
        import importlib
        importlib.import_module("pipeline.draft")


def test_translate_fields_handles_markdown_fences(monkeypatch):
    from pipeline import auto_translate as at

    fake = types.ModuleType("pipeline.draft")
    fake._call_script_ai = lambda prompt: (
        '```json\n{"script": "Hola mundo", "youtube_title": "Título"}\n```'
    )
    monkeypatch.setitem(sys.modules, "pipeline.draft", fake)
    try:
        out = at._translate_fields(
            source_lang="en", target_lang="es",
            fields={"script": "Hello world", "youtube_title": "Title"},
        )
        assert "Hola" in out["script"]
    finally:
        sys.modules.pop("pipeline.draft", None)
        import importlib
        importlib.import_module("pipeline.draft")


def test_fan_out_missing_source_returns_error(tmp_path, monkeypatch):
    from pipeline import auto_translate as at, config as cfg
    monkeypatch.setattr(cfg, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(at, "DRAFTS_DIR", tmp_path / "drafts")

    r = at.fan_out(source_draft_path=str(tmp_path / "nonexistent.json"),
                    target_langs=["tr"])
    assert "error" in r


def test_fan_out_skips_same_language(tmp_path, monkeypatch):
    """If source is 'tr' and we ask to translate to 'tr', that target is skipped."""
    from pipeline import auto_translate as at, config as cfg, queue as qmod
    monkeypatch.setattr(cfg, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(at, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path / "queue")
    monkeypatch.setattr(at, "TRANSLATIONS_LOG", tmp_path / "translog.jsonl")

    (tmp_path / "drafts").mkdir()
    src = tmp_path / "drafts" / "src.json"
    src.write_text(json.dumps({
        "job_id": "src", "lang": "tr",
        "script": "Merhaba",
        "youtube_title": "Başlık",
        "youtube_description": "Açıklama",
        "news": "Test",
        "_pipeline_state": {"research": {"status": "done"},
                             "draft": {"status": "done"}},
    }), encoding="utf-8")

    # Stub LLM to avoid real call
    fake = types.ModuleType("pipeline.draft")
    fake._call_script_ai = lambda p: '{"script":"X","youtube_title":"X","youtube_description":"X"}'
    monkeypatch.setitem(sys.modules, "pipeline.draft", fake)

    try:
        r = at.fan_out(
            source_draft_path=str(src),
            target_langs=["tr", "en"],  # tr should be skipped
        )
        assert len(r["created_drafts"]) == 1
        assert len(r["queued_jobs"]) == 1

        # The single created draft is for 'en' (source was 'tr')
        new_draft = json.loads(open(r["created_drafts"][0], encoding="utf-8").read())
        assert new_draft["lang"] == "en"
        assert new_draft["translation_source"] == "src"
    finally:
        sys.modules.pop("pipeline.draft", None)
        import importlib
        importlib.import_module("pipeline.draft")


def test_fan_out_applies_lang_channel_map(tmp_path, monkeypatch):
    from pipeline import auto_translate as at, config as cfg, queue as qmod
    monkeypatch.setattr(cfg, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(at, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path / "queue")
    monkeypatch.setattr(at, "TRANSLATIONS_LOG", tmp_path / "translog.jsonl")

    (tmp_path / "drafts").mkdir()
    src = tmp_path / "drafts" / "src.json"
    src.write_text(json.dumps({
        "job_id": "src", "lang": "tr",
        "script": "Merhaba", "youtube_title": "T",
        "youtube_description": "D", "news": "X",
    }), encoding="utf-8")

    fake = types.ModuleType("pipeline.draft")
    fake._call_script_ai = lambda p: '{"script":"S","youtube_title":"T","youtube_description":"D"}'
    monkeypatch.setitem(sys.modules, "pipeline.draft", fake)

    try:
        r = at.fan_out(
            source_draft_path=str(src),
            target_langs=["en", "de"],
            lang_channel_map={"en": "channel_en", "de": "channel_de"},
        )
        assert len(r["queued_jobs"]) == 2

        # Verify channel IDs on the jobs
        from pipeline import queue as qmod
        jobs = qmod.list_jobs()
        by_lang = {j["lang"]: j for j in jobs}
        assert by_lang["en"]["channel"] == "channel_en"
        assert by_lang["de"]["channel"] == "channel_de"
    finally:
        sys.modules.pop("pipeline.draft", None)
        import importlib
        importlib.import_module("pipeline.draft")


def test_fan_out_resets_downstream_stages(tmp_path, monkeypatch):
    """New draft must have research/draft marked done but voice/caption cleared."""
    from pipeline import auto_translate as at, config as cfg, queue as qmod
    monkeypatch.setattr(cfg, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(at, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(qmod, "QUEUE_DIR", tmp_path / "queue")
    monkeypatch.setattr(at, "TRANSLATIONS_LOG", tmp_path / "translog.jsonl")

    (tmp_path / "drafts").mkdir()
    src = tmp_path / "drafts" / "src.json"
    src.write_text(json.dumps({
        "job_id": "src", "lang": "tr",
        "script": "Merhaba", "youtube_title": "T",
        "youtube_description": "D", "news": "X",
        "_pipeline_state": {s: {"status": "done"} for s in
                             ["research", "draft", "broll", "voiceover",
                              "captions", "music", "assemble", "upload"]},
    }), encoding="utf-8")

    fake = types.ModuleType("pipeline.draft")
    fake._call_script_ai = lambda p: '{"script":"S","youtube_title":"T","youtube_description":"D"}'
    monkeypatch.setitem(sys.modules, "pipeline.draft", fake)

    try:
        r = at.fan_out(source_draft_path=str(src), target_langs=["en"])
        new_draft = json.loads(open(r["created_drafts"][0], encoding="utf-8").read())
        ps = new_draft["_pipeline_state"]

        # research + draft still done (we don't need to redo those)
        assert ps["research"]["status"] == "done"
        assert ps["draft"]["status"] == "done"
        # voice/caption/upload CLEARED (script changed)
        assert "voiceover" not in ps
        assert "captions" not in ps
        assert "upload" not in ps
    finally:
        sys.modules.pop("pipeline.draft", None)
        import importlib
        importlib.import_module("pipeline.draft")


def test_fan_out_rejects_unsupported_language(tmp_path, monkeypatch):
    from pipeline import auto_translate as at, config as cfg
    monkeypatch.setattr(cfg, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(at, "DRAFTS_DIR", tmp_path / "drafts")
    monkeypatch.setattr(at, "TRANSLATIONS_LOG", tmp_path / "translog.jsonl")

    (tmp_path / "drafts").mkdir()
    src = tmp_path / "drafts" / "src.json"
    src.write_text(json.dumps({
        "job_id": "src", "lang": "en",
        "script": "Hi", "youtube_title": "T",
        "youtube_description": "D", "news": "X",
    }), encoding="utf-8")

    r = at.fan_out(source_draft_path=str(src), target_langs=["klingon"])
    assert any("Unsupported" in e for e in r["errors"])


def test_history_returns_most_recent(tmp_path, monkeypatch):
    from pipeline import auto_translate as at
    monkeypatch.setattr(at, "TRANSLATIONS_LOG", tmp_path / "translog.jsonl")

    # Write some entries
    with open(at.TRANSLATIONS_LOG, "w", encoding="utf-8") as f:
        f.write('{"ts":"2026-04-18","source_lang":"tr","target_langs":["en"]}\n')
        f.write('{"ts":"2026-04-19","source_lang":"tr","target_langs":["de"]}\n')
        f.write('{"ts":"2026-04-20","source_lang":"tr","target_langs":["fr"]}\n')

    h = at.history(limit=5)
    assert len(h) == 3
    # Most recent first
    assert h[0]["target_langs"] == ["fr"]
    assert h[-1]["target_langs"] == ["en"]
