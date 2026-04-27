# Changelog

## [2.0.3] — 2026-04-22 · GUNCELLE.bat Self-Repair

### Düzeltildi
- **GUNCELLE.bat self-repair eklendi.** Eğer `.git` klasörü var ama remote
  tanımlı değilse (önceki yarım kalan `git init` yüzünden), script
  otomatik tespit edip `repair_repo` block'una atlar — remote'u sıfırdan ekler,
  fetch yapar, hard reset atar. Müşterinin manuel müdahalesi gerekmez.
- **`git pull` fail durumunda otomatik recovery.** Önceki sürümde "yerel
  değişiklikler var" diye yanlış teşhis koyup hard reset onayı isteniyordu.
  Şimdi otomatik remote add + fetch + reset yapıyor.
- **ASCII safety:** GUNCELLE.bat'ten son kalan Türkçe `ç` karakteri (`birkaç`
  → `birkac`) temizlendi. Tüm bat dosyaları artık saf ASCII.

### Etki
v2.0.2 müşterilerinden GUNCELLE.bat çalıştırmaya çalışıp "fatal: 'origin'
does not appear to be a git repository" hatası alanlar bu sürümle düzelir.
Yeni GUNCELLE.bat'i mevcut klasöre kopyalayıp tek tık çalıştırmak yeterli.

---

## [2.0.2] — 2026-04-22 · Upload Bug Hotfix

Üretim tamam, upload "draft yok" diyor şikayetinin acil yaması.

### Düzeltildi
- **🔴 KRİTİK:** Worker'ın `process_one()` fonksiyonu produce → upload geçişinde
  stale local job dict kullanıyordu. `_run_produce` draft_path'i veritabanına
  yazıyordu ama lokal değişkene yansıtmıyordu, dolayısıyla `_run_upload(job)`
  çağrısı `draft_path=None` ile geçip "Upload icin draft yok" hatası veriyordu.
  Mode="full" job'lar her seferinde produce sonrası upload aşamasında düşüyordu.
  - Fix 1: `_run_produce` sonunda local `job["draft_path"]` da güncelleniyor
  - Fix 2: `process_one` upload öncesi `qmod.load_job()` ile diskten reload
  - Regression test: `tests/test_worker_upload_flow.py` (4 test)

### Etki
Bu bug v2.0.0'dan beri vardı. v2.0.0 ve v2.0.1'de "full" modda video üreten
ama upload alamayan tüm müşteriler bu yamadan etkilenir. Üretilmiş ama
yüklenmemiş videolar `~/.youtube-shorts-pipeline/media/` içinde duruyor —
GUNCELLE.bat sonrası Kuyruk sayfasından "Tekrar Dene" ile upload yapılabilir.

---

## [2.0.1] — 2026-04-21 · Kurulum Stabilite Yamasi

Kritik kurulum sorunlarını düzelten hotfix. Mevcut müşteriler `GUNCELLE.bat`
ile yükseltebilir. Yeni müşterilerde sorunsuz kurulum garantisi.

### Düzeltildi
- **`openai-whisper` kurulumu kaldırıldı** (requirements'tan). Paket ~2 GB
  torch dependency'si çekiyordu ve Python 3.14/3.15'te pip install hatası
  veriyordu. Artık altyazı 4 farklı provider üzerinden alınıyor:
  1. Lokal Whisper (install edilmişse, `pip install openai-whisper`)
  2. **Groq Whisper API** — ÜCRETSİZ tier, `GROQ_API_KEY`
  3. OpenAI Whisper API — `OPENAI_API_KEY`
  4. Deepgram Nova-3 — `DEEPGRAM_API_KEY`
  Hiçbiri yoksa video altyazısız üretilir (upload çalışmaya devam eder).
- **KURULUM.bat** — ASCII encoding (Türkçe özel karakterler Windows cmd
  codepage'inde bozuluyordu), Unicode kutu karakterleri kaldırıldı.
- **RE-Tube.bat** — Unix-style `/dev/null` yerine Windows `nul` redirect.
- **Python sürüm kontrolü** — 3.14/3.15 algılanırsa açık uyarı + çözüm rehberi.
- **Pip install verbose** — `--quiet` kaldırıldı, hatalar artık görünür.
- **GUNCELLE.bat** — `.git` klasörü yoksa (ZIP ile kurulmuşsa) otomatik
  `git init + remote add + fetch + reset` yapıyor. Artık ZIP kullanıcıları
  da güncelleyebiliyor.

### Eklendi
- **references/GOOGLE_OAUTH_ERISIM_HATASI.md** — OAuth "Access blocked" hatası
  için adım adım çözüm (Test User ekleme rehberi).
- **pyproject.toml** — `requires-python = ">=3.10,<3.14"` kısıtlaması eklendi.
- **pyproject.toml** — `whisper_local` opsiyonel extras olarak eklendi
  (`pip install -e .[whisper_local]`).

### Geri uyumluluk
✅ Mevcut `config.json`, `drafts/`, `media/`, `channels/`, `youtube_token.json` değişmez
✅ Daha önce `openai-whisper` yüklediysen yine çalışır (otomatik algılanır)
✅ `GUNCELLE.bat` + ZIP ile kurulum senaryoları ikisi de destekleniyor

### Performans
- Kurulum süresi: ~5 dk → **~30 sn** (whisper/torch kaldırıldı)
- Disk kullanımı: ~3 GB → **~500 MB**
- İlk çalıştırma: torch model indirme yok → anında başlar

---

## [2.0.0] — 2026-04-20 · Enterprise Pack

Büyük sürüm. 30 yeni özellik, 6000+ satır yeni kod, 301 otomatik test.
Geriye uyumlu — mevcut müşteri verisi (drafts, media, channels, tokens)
hiç değişmez; yeni özellikler opt-in.

### Tier 1 — Starter (üretkenlik)
- **Çoklu video kuyruğu** — arkaplanda üretim, FIFO sıralı upload, çoklu iş paralel
- **Çökme kurtarma** — worker/power-cut sonrası iş kaldığı yerden devam eder
- **Batch CSV upload** — 50 konu tek seferde kuyruğa, opsiyonel staggered enqueue
- **Scheduled publish** — video private yüklenir, belirtilen UTC saatinde YouTube otomatik public yapar
- **Retry UI** — failed job'lar için stage-seviye tekrar (sadece upload, sadece voice'tan itibaren, vb.)
- **Cost dashboard** — günlük/aylık harcama, provider breakdown, son 30 gün grafiği

### Tier 2 — Pro (kalite & büyüme)
- **Kanal başına preset** — dil, ses, format, müzik, playlist ID, ton per kanal
- **Thumbnail A/B test** — 3 varyant, 24 saatte bir rotasyon, views/hour ile kazanan auto-pick
- **Playlist otomatik ekleme** — upload sonrası preset'teki playlist'e otomatik
- **Topic memory** — SQLite + TF benzerlik, tekrar konu yakalama (paraphrase seviye)
- **Yorum moderatörü** — Claude ile spam/soru/teşekkür/tartışma sınıflandırma, spam gizle
- **Canlı kanal stats widget** — Dashboard'ta aboneler, izlenme, son 10 video (10 dk cache)
- **AI Script Editor** — draft'ı düzenle, voice/caption otomatik invalidate, Claude ile regenerate

### Tier 3 — Agency (satış ve ölçeklenme)
- **Multi-tenant mode** (OPT-IN, default OFF) — tek panel, birden fazla müşteri; **otomatik backup** ile güvenli migration; YouTube OAuth token'lar korunur
- **White-label / rebrand** — logo, ürün adı, slogan, accent rengi; CSS injection
- **Stripe billing layer** — 5 plan (Free/Starter/Pro/Agency/Enterprise), quota enforcement, webhook handler
- **REST API + webhooks** — Bearer token auth, `/v1/jobs` POST, `/v1/stream` SSE (gelecek), per-job webhook_url
- **Audit log** — her kritik aksiyonun JSONL kaydı, filtered query, CSV export

### Tier 4 — Enterprise (rekabetçi avantaj)
- **Viral potansiyel skoru** — 6 sinyalli heuristic + Claude LLM (başlık hook, uzunluk, duygu, sayı, saturation, model)
- **Rakip kanal takibi** — YouTube Data API ile kanal izleme, top performers, topic gap analizi
- **Haber watcher** — RSS feed, anahtar kelime filtresi, Telegram/webhook bildirimi, auto-queue
- **Sesli klon** — ElevenLabs Instant Voice Cloning, 30-90sn sample → özel voice_id
- **LoRA fine-tuning** — Replicate + Flux/SDXL, karakter tutarlılığı için özel model
- **Otomatik çeviri fan-out** — 1 TR video → 10 dil → 10 kanal (Claude ile script/title/description çevrilir)
- **Watermark / reupload tespiti** — audio fingerprint (chromaprint + fallback), Hamming distance ile kopya yakalama

### Closing — Demo & Delivery
- **1-dakika live demo** — tek tık, random konu, ucuz provider stack
- **Mobil QR preview** — iş/video/URL için QR kod üret, telefonda aç
- **Zamanlayıcı** — cron benzeri, gece modu burst, günlük topic pool rotation
- **Telegram bot** — `/yap konu`, `/durum`, `/kuyruk`, `/stat` komutları
- **Gelir tahmini** — niche + country CPM ile AdSense projeksiyonu, Shorts penalty
- **SSE real-time** — job status değişikliklerini real-time stream

### Sağlayıcı kataloğu
97 sağlayıcı:
- **Script AI** (25): Claude, GPT-4o, Gemini, Groq Llama, DeepSeek, Mistral, xAI Grok, Perplexity, OpenRouter, Together, Fireworks, Qwen
- **Görsel** (23): Pexels, Pixabay, Unsplash, Imagen 4, DALL-E, SD3, SDXL, Flux (Pro/Dev/Schnell), Ideogram, Recraft, Leonardo, Replicate
- **Video** (14): Veo 3.1, Runway Gen-3, Luma Ray 2, Kling V2, Minimax Hailuo, Pika 2.0, Sora 2
- **TTS** (23): Edge, OpenAI, ElevenLabs (Flash/v2/Turbo), **Voixor (TR)**, PlayHT, Cartesia, Deepgram, Azure, Murf, Resemble, Fish Audio, Coqui, Piper
- **Müzik** (6): Bundled, Suno v4, Udio, Stable Audio, Mubert, Soundraw
- **Caption** (6): Whisper (local/API), Deepgram Nova-3, AssemblyAI, Speechmatics, Groq Whisper

### Güvenlik
- Multi-tenant açma/kapama **otomatik yedek** alır (`.youtube-shorts-pipeline.backup.<timestamp>/`)
- API token'lar tek seferlik gösterilir, hash preview ile listelenir
- Audit log her destructive aksiyonu kaydeder
- YouTube OAuth token'lar migration sırasında bit-bit korunur
- Tüm modüllerde fail-safe: cost/audit/SSE çağrıları try/except ile sarılı, ana pipeline'ı asla düşürmez

### Teknik
- 301 otomatik test, 26 yeni modül
- Yeni bağımlılıklar: streamlit, edge-tts, qrcode[pil], pandas
- Python 3.10+ (3.12 test edildi)
- Backward compatible: mevcut config.json, drafts/, media/, channels/, youtube_token.json olduğu gibi çalışır
- pyproject.toml + version.json → 2.0.0

### Bilinen limitler
- Tier 4 modüllerinin bazıları (LoRA, voice clone) **3rd party API key gerektirir** (Replicate, ElevenLabs Pro) — key yoksa graceful degrade
- Tier 3 Stripe billing sadece abstraction layer — gerçek Stripe bağlantısı için müşteri kendi webhook secret'ını girmeli
- Watermark chromaprint için ffmpeg'in chromaprint filtresi gerek — yoksa audio digest fallback'i kullanır (düşük hassasiyet)

---

## [2.1.0] — 2026-02-27 (eski — artık 2.0 olarak yeniden isimlendirildi)

Security audit fixes ported to v2 modular architecture.

### Security
- TOCTOU race fix for credential file writes via `os.open()` with `0o600`
- ffmpeg concat file paths properly escaped
- All dependency versions pinned with compatible-release bounds

### Fixed
- Clear error on expired OAuth token without refresh token

### Added
- Security section in README.md
- CHANGELOG.md

## [2.0.0-beta] — 2026-02-27 (önceki 2.0.0)

İlk modüler yeniden yapılanma.

### Added
- Burned-in captions (word-by-word, ASS subtitles + Whisper timestamps)
- Background music (bundled royalty-free + voice-ducking)
- Topic engine (Reddit/RSS/Google Trends/Twitter/TikTok)
- Thumbnail generation (Gemini Imagen + Pillow overlay)
- Resume capability (state tracked per stage)
- Retry logic (exponential backoff on all API calls)
- Structured logging
- Claude Max support via CLI
- 78 test

## [1.0.0] — 2026-02-27

İlk sürüm. Tek dosya pipeline: draft → produce → upload.
