"""Tests for comment_moderator — classification + storage + filtering."""


def test_heuristic_detects_spam_urls():
    from pipeline.comment_moderator import classify_heuristic
    cat, conf = classify_heuristic("Check out https://spam.example.com for free crypto!")
    assert cat == "spam"
    assert conf > 0.5


def test_heuristic_detects_spam_sub4sub():
    from pipeline.comment_moderator import classify_heuristic
    assert classify_heuristic("Sub4Sub please!")[0] == "spam"
    assert classify_heuristic("kanalıma gel abone ol")[0] == "spam"


def test_heuristic_detects_questions():
    from pipeline.comment_moderator import classify_heuristic
    assert classify_heuristic("How did you make this?")[0] == "question"
    assert classify_heuristic("Bu nasıl yapıldı")[0] == "question"
    assert classify_heuristic("What's your setup?")[0] == "question"


def test_heuristic_detects_thanks():
    from pipeline.comment_moderator import classify_heuristic
    assert classify_heuristic("Thanks for the video!")[0] == "thanks"
    assert classify_heuristic("Teşekkürler ❤❤")[0] == "thanks"


def test_heuristic_discussion_fallback():
    from pipeline.comment_moderator import classify_heuristic
    cat, _ = classify_heuristic("I disagree — this point is weak.")
    assert cat == "discussion"


def test_process_new_stores_classifies_and_dedupes(tmp_path, monkeypatch):
    from pipeline import comment_moderator as cm
    monkeypatch.setattr(cm, "DB_PATH", tmp_path / "comments.sqlite")

    fake_comments = [
        {"id": "c1", "video_id": "v1", "author": "A", "text": "How does this work?", "published_at": "2026-04-20T10:00:00Z"},
        {"id": "c2", "video_id": "v1", "author": "B", "text": "Thanks!", "published_at": "2026-04-20T11:00:00Z"},
        {"id": "c3", "video_id": "v1", "author": "C", "text": "Sub4Sub", "published_at": "2026-04-20T12:00:00Z"},
    ]
    monkeypatch.setattr(cm, "fetch_recent_comments", lambda **_: fake_comments)

    result = cm.process_new(token_path="/t", use_llm=False)
    assert result["new"] == 3
    assert result["skipped"] == 0

    # Dedup — second call with same IDs should skip all
    result2 = cm.process_new(token_path="/t", use_llm=False)
    assert result2["new"] == 0
    assert result2["skipped"] == 3

    # Counts reflect classifications
    c = cm.counts(days=30)
    assert c["question"] == 1
    assert c["thanks"] == 1
    assert c["spam"] == 1


def test_inbox_filters_by_category(tmp_path, monkeypatch):
    from pipeline import comment_moderator as cm
    monkeypatch.setattr(cm, "DB_PATH", tmp_path / "comments.sqlite")

    monkeypatch.setattr(cm, "fetch_recent_comments", lambda **_: [
        {"id": "c1", "video_id": "v1", "author": "A", "text": "How?", "published_at": "2026-04-20T10:00:00Z"},
        {"id": "c2", "video_id": "v1", "author": "B", "text": "Thanks", "published_at": "2026-04-20T11:00:00Z"},
    ])
    cm.process_new(token_path="/t", use_llm=False)

    questions = cm.inbox(category="question")
    assert len(questions) == 1
    assert questions[0]["text"] == "How?"

    thanks = cm.inbox(category="thanks")
    assert len(thanks) == 1


def test_inbox_filters_by_channel(tmp_path, monkeypatch):
    from pipeline import comment_moderator as cm
    monkeypatch.setattr(cm, "DB_PATH", tmp_path / "comments.sqlite")

    monkeypatch.setattr(cm, "fetch_recent_comments", lambda **_: [
        {"id": "c1", "video_id": "v1", "author": "A", "text": "How?",  "published_at": "2026-04-20T10:00:00Z"},
    ])
    cm.process_new(token_path="/t", channel="ayaz", use_llm=False)

    monkeypatch.setattr(cm, "fetch_recent_comments", lambda **_: [
        {"id": "c2", "video_id": "v2", "author": "B", "text": "What?", "published_at": "2026-04-20T11:00:00Z"},
    ])
    cm.process_new(token_path="/t", channel="ikinci", use_llm=False)

    ayaz_inbox = cm.inbox(channel="ayaz")
    ikinci_inbox = cm.inbox(channel="ikinci")
    assert len(ayaz_inbox) == 1 and ayaz_inbox[0]["channel"] == "ayaz"
    assert len(ikinci_inbox) == 1 and ikinci_inbox[0]["channel"] == "ikinci"


def test_mark_handled(tmp_path, monkeypatch):
    from pipeline import comment_moderator as cm
    monkeypatch.setattr(cm, "DB_PATH", tmp_path / "comments.sqlite")

    monkeypatch.setattr(cm, "fetch_recent_comments", lambda **_: [
        {"id": "c1", "video_id": "v1", "author": "A", "text": "How?", "published_at": "2026-04-20T10:00:00Z"},
    ])
    cm.process_new(token_path="/t", use_llm=False)

    cm.mark_handled("c1")
    items = cm.inbox()
    assert items[0]["action"] == "handled"


def test_llm_classifier_falls_back_to_heuristic(monkeypatch):
    """If the LLM call raises, classify_llm should fall back to heuristic."""
    from pipeline import comment_moderator as cm

    def boom(prompt):
        raise RuntimeError("no network")
    monkeypatch.setattr("pipeline.draft._call_script_ai", boom, raising=False)
    # Also monkeypatch the import path used inside the function
    import sys
    fake_draft = type(sys)("pipeline.draft_test_stub")
    fake_draft._call_script_ai = boom
    sys.modules["pipeline.draft"] = fake_draft

    try:
        cat, conf = cm.classify_llm("Thanks for the video!")
        # Heuristic picked up "thanks"
        assert cat == "thanks"
    finally:
        # Restore original
        import importlib
        sys.modules.pop("pipeline.draft", None)
        importlib.import_module("pipeline.draft")
