"""Tests for viral_score — individual signals + aggregate scoring."""


def test_hook_word_scorer():
    from pipeline.viral_score import score_title_hook
    s_low, m = score_title_hook("A regular title about tech")
    s_high, m = score_title_hook("Shocking secret Apple never revealed!")
    assert s_low < 30
    assert s_high >= 50


def test_title_length_sweet_spot():
    from pipeline.viral_score import score_title_length
    assert score_title_length("short")[0] < 30
    # 40-60 = optimal
    s, m = score_title_length("NASA Just Launched the First Human Moon Mission")
    assert s == 100
    assert m["note"] == "optimal"
    assert score_title_length("x" * 150)[0] < 40


def test_emotion_scorer():
    from pipeline.viral_score import score_emotion
    assert score_emotion("Here is a thing")[0] == 0
    assert score_emotion("How do they do this?")[0] >= 40
    assert score_emotion("Why is this crazy?")[0] >= 80


def test_number_scorer_rewards_listicles():
    from pipeline.viral_score import score_number_in_title
    plain, _ = score_number_in_title("A great idea")
    with_num, _ = score_number_in_title("Tesla Model 3 review")
    listicle, _ = score_number_in_title("5 things nobody told you")
    assert plain == 0
    assert with_num == 60
    assert listicle == 100


def test_topic_saturation_penalizes_recent_duplicates(tmp_path, monkeypatch):
    from pipeline import viral_score, topic_memory
    monkeypatch.setattr(topic_memory, "DB_PATH", tmp_path / "topics.sqlite")

    # Fresh topic → high score
    s_fresh, _ = viral_score.score_topic_saturation("Brand new topic about quantum computers")
    assert s_fresh >= 80

    # Remember a topic, then test near-identical (forces similarity >= 0.5)
    topic_memory.remember("NASA Artemis 3 Moon mission launches")
    s_saturated, meta = viral_score.score_topic_saturation(
        "NASA Artemis 3 Moon mission launches today"
    )
    assert s_saturated < 80
    assert meta["recent_similar"] >= 1


def test_aggregate_score_without_llm(tmp_path, monkeypatch):
    from pipeline import viral_score, topic_memory
    monkeypatch.setattr(topic_memory, "DB_PATH", tmp_path / "topics.sqlite")

    result = viral_score.score(
        topic="NASA first crewed Moon mission",
        title="5 things nobody told you about NASA's shocking Moon mission",
        use_llm=False,
    )
    assert 0 <= result["score"] <= 100
    assert result["tier"] in ("low", "medium", "high", "viral")
    assert "breakdown" in result
    # No LLM → no llm_judgement key
    assert "llm_judgement" not in result["breakdown"]


def test_aggregate_score_with_stub_llm(tmp_path, monkeypatch):
    """Inject a fake LLM that always returns score=85."""
    from pipeline import viral_score, topic_memory
    monkeypatch.setattr(topic_memory, "DB_PATH", tmp_path / "topics.sqlite")

    # Stub the LLM call
    import sys, types
    fake = types.ModuleType("pipeline.draft")
    fake._call_script_ai = lambda prompt: (
        '{"score": 85, "reasoning": "Strong hook", '
        '"strengths": ["curiosity gap"], "weaknesses": []}'
    )
    sys.modules["pipeline.draft"] = fake
    try:
        result = viral_score.score(
            topic="Tesla robotaxi secret",
            title="Shocking secret about Tesla's new robotaxi — 5 hidden facts",
            use_llm=True,
        )
        assert "llm_judgement" in result["breakdown"]
        assert result["breakdown"]["llm_judgement"]["score"] == 85
    finally:
        # Restore real module
        import importlib
        sys.modules.pop("pipeline.draft", None)
        importlib.import_module("pipeline.draft")


def test_tier_thresholds():
    from pipeline import viral_score, topic_memory

    # Directly construct score outputs by running the function with tuned inputs
    # We just verify tier calculation by mocking weights indirectly:
    # A garbage title should be low-tier
    result = viral_score.score(topic="x", title="x", use_llm=False)
    assert result["tier"] in ("low", "medium")


def test_recommendations_generated_for_weak_signals():
    from pipeline import viral_score
    # Short bland title with no hooks, no numbers → should produce recommendations
    result = viral_score.score(
        topic="AI",
        title="AI news",
        use_llm=False,
    )
    assert len(result["recommendations"]) >= 1
    assert any("başlık" in r.lower() or "title" in r.lower() or "sayı" in r.lower()
               or "hook" in r.lower() or "listicle" in r.lower()
               for r in result["recommendations"])


def test_llm_failure_falls_back_gracefully(tmp_path, monkeypatch):
    """Even when LLM raises, score() must return a full result."""
    from pipeline import viral_score, topic_memory
    monkeypatch.setattr(topic_memory, "DB_PATH", tmp_path / "topics.sqlite")

    import sys, types
    fake = types.ModuleType("pipeline.draft")
    fake._call_script_ai = lambda prompt: (_ for _ in ()).throw(RuntimeError("API down"))
    sys.modules["pipeline.draft"] = fake
    try:
        result = viral_score.score(topic="Topic", title="Decent title here", use_llm=True)
        # Must not raise
        assert "score" in result
        # LLM signal degraded to neutral 50
        assert result["breakdown"]["llm_judgement"]["score"] == 50
    finally:
        import importlib
        sys.modules.pop("pipeline.draft", None)
        importlib.import_module("pipeline.draft")
