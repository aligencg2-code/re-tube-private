"""Tests for lora_training — DB, zip builder, poll lifecycle with fake Replicate."""

import io
import zipfile
from types import SimpleNamespace


def test_zip_builder_from_bytes():
    from pipeline.lora_training import build_training_zip

    fake_images = [b"\x89PNG\r\n\x1a\n" + b"\x00" * 100 for _ in range(3)]
    zip_bytes = build_training_zip(fake_images, caption="a photo of TOK person")

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert "img_000.png" in names
        assert "img_000.txt" in names
        assert "img_002.png" in names
        # Caption correctness
        caption = zf.read("img_000.txt").decode()
        assert "TOK person" in caption


def test_supported_base_models_has_flux_and_sdxl():
    from pipeline.lora_training import SUPPORTED_BASE_MODELS
    assert "flux-dev" in SUPPORTED_BASE_MODELS
    assert "sdxl" in SUPPORTED_BASE_MODELS


def test_start_training_rejects_unknown_base_model(tmp_path, monkeypatch):
    from pipeline import lora_training as lt
    monkeypatch.setattr(lt, "DB_PATH", tmp_path / "loras.sqlite")

    r = lt.start_training(
        name="Ayaz", trigger_word="AYAZ_V1",
        images=[], base_model="midjourney",
    )
    assert "error" in r
    assert "Unsupported" in r["error"]


def test_start_training_without_api_key_fails(tmp_path, monkeypatch):
    from pipeline import lora_training as lt
    monkeypatch.setattr(lt, "DB_PATH", tmp_path / "loras.sqlite")
    monkeypatch.setattr(lt, "_get_key", lambda k: "")

    r = lt.start_training(
        name="Test", trigger_word="T",
        images=[], base_model="flux-dev",
    )
    assert "error" in r


def test_start_training_with_fake_client_records_job(tmp_path, monkeypatch):
    from pipeline import lora_training as lt
    monkeypatch.setattr(lt, "DB_PATH", tmp_path / "loras.sqlite")

    # Fake Replicate client
    fake_training = SimpleNamespace(id="training_abc_123")
    fake_client = SimpleNamespace(
        trainings=SimpleNamespace(
            create=lambda **kwargs: fake_training,
            get=None,  # used later
        )
    )

    r = lt.start_training(
        name="Ayaz Character", trigger_word="AYAZ_V1",
        images=[b"\x89PNG" + b"\x00" * 50] * 2,
        base_model="flux-dev", steps=500,
        replicate_client=fake_client,
    )
    assert r.get("job_id")
    assert r["replicate_job_id"] == "training_abc_123"
    assert r["status"] == "running"

    # Persisted in DB
    jobs = lt.list_trainings()
    assert len(jobs) == 1
    j = jobs[0]
    assert j["name"] == "Ayaz Character"
    assert j["trigger_word"] == "AYAZ_V1"
    assert j["base_model"] == "flux-dev"
    assert j["image_count"] == 2
    assert j["status"] == "running"


def test_poll_training_on_success(tmp_path, monkeypatch):
    from pipeline import lora_training as lt
    monkeypatch.setattr(lt, "DB_PATH", tmp_path / "loras.sqlite")

    # Register a job
    fake_job = SimpleNamespace(id="training_xxx")
    start_client = SimpleNamespace(
        trainings=SimpleNamespace(
            create=lambda **kw: fake_job,
            get=None,
        )
    )
    r = lt.start_training(
        name="Ayaz", trigger_word="AYAZ", images=[b"x"],
        base_model="flux-dev", replicate_client=start_client,
    )
    job_id = r["job_id"]

    # Poll client returns succeeded with a weights URL
    succeeded = SimpleNamespace(
        status="succeeded",
        output={"weights": "https://replicate.delivery/lora/abc.safetensors"},
        metrics={"total_cost": 2.85},
    )
    poll_client = SimpleNamespace(
        trainings=SimpleNamespace(get=lambda _id: succeeded)
    )
    poll_r = lt.poll_training(job_id, replicate_client=poll_client)

    assert poll_r["status"] == "succeeded"
    assert "replicate.delivery" in poll_r["lora_url"]
    assert poll_r["cost_usd"] == 2.85

    # DB reflects terminal state
    jobs = lt.list_trainings()
    assert jobs[0]["status"] == "succeeded"
    assert jobs[0]["lora_url"] == "https://replicate.delivery/lora/abc.safetensors"
    assert jobs[0]["cost_usd"] == 2.85


def test_poll_training_on_failure(tmp_path, monkeypatch):
    from pipeline import lora_training as lt
    monkeypatch.setattr(lt, "DB_PATH", tmp_path / "loras.sqlite")

    fake_job = SimpleNamespace(id="fail_job_1")
    lt.start_training(
        name="Test", trigger_word="T", images=[b"x"],
        base_model="sdxl",
        replicate_client=SimpleNamespace(
            trainings=SimpleNamespace(create=lambda **kw: fake_job, get=None),
        ),
    )

    job_id = lt.list_trainings()[0]["id"]
    failed = SimpleNamespace(status="failed", error="OOM during training")
    poll_client = SimpleNamespace(
        trainings=SimpleNamespace(get=lambda _id: failed)
    )
    r = lt.poll_training(job_id, replicate_client=poll_client)
    assert r["status"] == "failed"
    assert "OOM" in r["error"]


def test_poll_already_terminal_noops(tmp_path, monkeypatch):
    """Once a job is terminal, polling returns cached result without calling Replicate."""
    from pipeline import lora_training as lt
    monkeypatch.setattr(lt, "DB_PATH", tmp_path / "loras.sqlite")
    import sqlite3
    lt._ensure_db()
    # Seed a terminal job directly
    conn = sqlite3.connect(str(lt.DB_PATH))
    conn.execute(
        "INSERT INTO training_jobs (name, trigger_word, base_model, "
        " replicate_job_id, status, started_at, completed_at, lora_url) "
        "VALUES (?, ?, ?, ?, 'succeeded', ?, ?, ?)",
        ("Old", "T", "flux-dev", "rep_xxx",
         "2026-04-19T10:00:00+00:00", "2026-04-19T11:00:00+00:00",
         "https://result/lora.safetensors"),
    )
    conn.commit()
    conn.close()

    # If poll calls replicate.trainings.get, we raise — but with cache it shouldn't
    def boom(_id):
        raise AssertionError("should not call Replicate")
    fake_client = SimpleNamespace(trainings=SimpleNamespace(get=boom))

    r = lt.poll_training(1, replicate_client=fake_client)
    assert r["status"] == "succeeded"
    assert "lora.safetensors" in r["lora_url"]


def test_poll_all_running_only_touches_running(tmp_path, monkeypatch):
    from pipeline import lora_training as lt
    monkeypatch.setattr(lt, "DB_PATH", tmp_path / "loras.sqlite")
    import sqlite3
    lt._ensure_db()

    # Two jobs: one running, one already succeeded
    now = "2026-04-20T10:00:00+00:00"
    conn = sqlite3.connect(str(lt.DB_PATH))
    conn.execute("INSERT INTO training_jobs (name, trigger_word, base_model, replicate_job_id, status, started_at) VALUES (?, ?, ?, ?, 'running', ?)",
                 ("Running", "R", "flux-dev", "rep_running", now))
    conn.execute("INSERT INTO training_jobs (name, trigger_word, base_model, replicate_job_id, status, started_at, completed_at, lora_url) VALUES (?, ?, ?, ?, 'succeeded', ?, ?, ?)",
                 ("Done", "D", "flux-dev", "rep_done", now, now,
                  "https://done/weights"))
    conn.commit()
    conn.close()

    calls = []
    def fake_get(_id):
        calls.append(_id)
        return SimpleNamespace(status="running")
    fake_client = SimpleNamespace(trainings=SimpleNamespace(get=fake_get))

    results = lt.poll_all_running(replicate_client=fake_client)
    assert len(results) == 1
    assert calls == ["rep_running"]


def test_get_lora_url_by_name(tmp_path, monkeypatch):
    from pipeline import lora_training as lt
    monkeypatch.setattr(lt, "DB_PATH", tmp_path / "loras.sqlite")
    import sqlite3
    lt._ensure_db()

    conn = sqlite3.connect(str(lt.DB_PATH))
    conn.execute(
        "INSERT INTO training_jobs (name, trigger_word, base_model, "
        " replicate_job_id, status, started_at, completed_at, lora_url) "
        "VALUES (?, ?, ?, ?, 'succeeded', ?, ?, ?)",
        ("BrandChar", "BRAND", "flux-dev", "rep_x",
         "2026-04-20T10:00:00+00:00", "2026-04-20T11:00:00+00:00",
         "https://r/brand.safetensors"),
    )
    conn.commit()
    conn.close()

    assert lt.get_lora_url_by_name("BrandChar") == "https://r/brand.safetensors"
    assert lt.get_lora_url_by_name("Nonexistent") is None
