# RE-Tube · Yol Haritası (v2.2+)

Bu dokümanda bu session'da tamamlananlar + yakın vadede eklenebilecek özellikler listelendi. Önceliklendirme tartışmaya açık — müşteri geri bildirimine göre güncellenir.

## ✅ Bu session'da eklendi

### 1. Paralel üretim kuyruğu (çoklu video)
- `pipeline/queue.py` — JSON job store, PID-lock, cancel flag, FIFO sıralama.
- `pipeline/worker.py` — Tek worker drain loop. Üretim → yükleme zinciri. Upload'lar submission sırasında.
- Admin panelde **Kuyruk** sayfası — canlı ilerleme, progress bar, log kuyruğu, iptal/silme.
- **"Kuyruğa Ekle (Arka Planda Üret)"** butonu varsayılan; eski canlı mod yan buton olarak korunur.
- Worker, Streamlit'ten ilk job ekleme anında detached olarak başlar (Windows: CREATE_NO_WINDOW). İdle 6 dakika sonra kendini kapatır; yeni job gelince UI yeniden başlatır.

### 2. Voixor TTS entegrasyonu
- `pipeline/voiceover.py` → `_call_voixor()` + seçici zincir. ElevenLabs-compatible voice ID.
- `POST https://voixor.com/api.php` · `Authorization: Bearer …` · `{text, voice_id}` → audio/mpeg 128kbps.
- 5 karakter minimum (guard eklendi), retry + fallback Edge TTS.
- PROVIDERS kataloğunda `tts.voixor` olarak listelendi.

### 3. PROVIDERS katalog genişletme — **97 sağlayıcı**
| Kategori | Sayı | Öne çıkanlar |
|---|---|---|
| script_ai | 25 | Claude (CLI/Sonnet/Haiku/Opus), Gemini, GPT-4o, **Groq** (Llama 3.3 70B, Mixtral), **DeepSeek**, Mistral, **xAI Grok**, Perplexity, OpenRouter, Together, Fireworks, Qwen |
| image | 23 | Imagen 4 (Fast/Std/Ultra), DALL-E 3, GPT-Image-1, **SD3**, SDXL, **Flux** (Pro/Ultra/Dev/Schnell), Ideogram, Recraft, Leonardo, Replicate, Pixabay, Unsplash |
| video | 14 | Veo 3.1 (Lite/Fast/Std), Veo 2.0, **Runway Gen-3**, **Luma Ray 2**, **Kling V2**, **Minimax Hailuo**, Pika 2.0, **Sora 2** |
| tts | 23 | Edge TTS, OpenAI, Google Chirp 3, ElevenLabs (Flash/v2/Turbo), **Voixor**, PlayHT, Cartesia Sonic, Deepgram Aura, Azure Neural, Murf, Resemble, Speechify, Fish Audio, Coqui XTTS, Piper |
| music | 6 | Bundled, **Suno v4**, Udio, Stable Audio, Mubert, Soundraw |
| captions | 6 | Whisper Local/API, Deepgram Nova-3, AssemblyAI, Speechmatics, Groq Whisper |

- Admin panelde **Ayarlar → Ek Sağlayıcılar** expander'ı (LLM/Image/Video/TTS/Müzik). Müşteri kendi key'ini girer, boş bırakılabilir.

---

## 🔜 Yakın vadede eklenebilir (öncelik sırası önerisi)

### Öncelik 1 — Üretim kalitesi ve üretkenlik
1. **Batch/script upload** — CSV/TXT yükle, 50 konuyu tek seferde kuyruğa at. Scheduler ile yayın saati belirleme (08:00, 12:00, 18:00 gibi cron'lı upload).
2. **Retry UI** — Failed jobs için "Tekrar dene" butonu + force stage seçimi (sadece upload'ı tekrarla, sadece voiceover'ı yenile, vb.).
3. **Provider router** — Birden fazla LLM/TTS key varsa round-robin veya cost-based routing. Rate-limit yemeden daha fazla üretim.
4. **Voice library** — Voixor/ElevenLabs/Azure seslerini panel içinden önizleme (5 sn sample) + favori işaretleme. Her kanal için farklı varsayılan ses.
5. **Template preset'leri** — "Teknoloji haberi (3dk)", "Motivasyon Shorts", "Belgesel tarzı 5dk" gibi hazır preset'ler (script AI + görsel + TTS + müzik kombinasyonları).

### Öncelik 2 — YouTube entegrasyonu
6. **Scheduled publish** — Upload'ı "private" yap, X saatlik scheduler ile "public"a çevir (youtube.videos.update).
7. **Playlist otomatik ekleme** — Kanal-playlist eşlemesi; her video kendi playlist'ine gider.
8. **End screen / cards** — Son 20 saniyeye başka video veya abone butonu yerleştir.
9. **A/B thumbnail testing** — 2-3 thumbnail varyantı üret, 48 saat sonra tıklama oranı en iyisini bırak.
10. **Comment moderator** — Yeni yorumları Gemini/Claude ile sınıflandır; spam/reklam otomatik gizle, gerçek soruları panelde biriktir.

### Öncelik 3 — İçerik zekası
11. **Topic memory** — Daha önce yapılan videoları vektör DB'ye (pgvector/Chroma) gömerek tekrar konu tespiti. "Bu konuyu 2 hafta önce yaptın" uyarısı.
12. **Kaynak doğrulama guard'ı** — Script'te geçen iddia ve isimleri DuckDuckGo/Perplexity üzerinden 2. tur doğrulama. Halüsinasyon varsa üretim durur.
13. **Rekabet analizi** — YouTube Data API ile kanalın niş'indeki trend videoları çek, başlık/açıklama paternlerini Claude'a özetlet.
14. **Thumbnail metin AI kuralları** — Stok imge + yüz + kontrast text overlay. Ideogram V2 (metin render'ı güçlü) default.
15. **Auto B-roll seçici** — Script'teki cümleye göre stok (Pexels/Pixabay) + AI karışık görsel. Pahalı AI'yı sadece anahtar sahnede kullan.

### Öncelik 4 — Maliyet ve operasyon
16. **Cost dashboard** — Günlük/haftalık/aylık harcama grafiği, sağlayıcı bazlı breakdown, limit alarmı.
17. **Free-first waterfall** — Varsayılan sağlayıcı sırası `Edge TTS → OpenAI mini → ElevenLabs`. Key yoksa/yetersizse otomatik düşer.
18. **Self-host option** — Whisper, Coqui XTTS, Piper, SDXL için lokal GPU fallback. Ollama ile Llama 3.1 8B self-hosted LLM.
19. **Webhook & event bus** — Job lifecycle eventleri (`job.queued`, `job.done`, `job.failed`) Discord/Slack/email'e gönder.
20. **Multi-user auth** — Tek panel üzerinden birden fazla müşteri kendi kanalını/kuyruğunu görsün (basit user dir + oturum).

### Öncelik 5 — Kullanıcı deneyimi
21. **Dry-run pricing** — Üretim başlatmadan önce "Bu video tahminen $0.38'e mal olur, onaylıyor musun?" modal.
22. **Live preview** — Üretim sırasında her stage tamamlanınca thumbnail + ilk 5 saniye önizleme.
23. **Script editor** — Claude ürettikten sonra panelde inline düzeltme, "üret" basınca düzeltilmiş metinle devam.
24. **Karakter sayacı** — Voixor/ElevenLabs kredilerini real-time göster, videonun kaç karakter harcayacağını üretim öncesi söyle.
25. **Language pack genişletme** — Arapça, İspanyolca, Fransızca, Almanca, Portekizce voiceover voice ID önerileri.

---

## Teknik borç / cleanup

- `pipeline/__main__.py` içindeki queue/worker altkomutları test coverage'ı düşük → `tests/test_queue.py` + `tests/test_worker.py` (mock subprocess) eklenmeli.
- Worker 6 dk idle sonrası kapanıyor — UI job eklerken otomatik restart var ama edge case: UI offline'ken job enqueue edilirse worker uyanmaz. Cron ya da systemd-timer benzeri bir watchdog eklenebilir.
- Config key proliferation — 30+ API key var. Setup wizard'ı (`pipeline/config.py::run_setup`) sadece core key'leri soruyor, extended key'leri panel içinden alıyor. Bu doğru tasarım ama CLI-only kullanıcılar için de `yt-shorts keys set GROQ_API_KEY …` gibi bir komut eklenmeli.
- `PROVIDERS` kataloğunun fiyatları elle güncel tutulmalı — Q2 2026 itibariyle doğru, fakat fiyatlar hızlı değişiyor. Public pricing scrape'iyle aylık audit scripti yazılabilir.

---

## Komut özeti

```bash
# Queue
python -m pipeline queue add --news "konu" --lang tr --mode full
python -m pipeline queue list
python -m pipeline queue status
python -m pipeline queue cancel --id <id>
python -m pipeline queue clear

# Worker (Streamlit'ten otomatik başlar, manuel de başlatılabilir)
python -m pipeline worker           # drain loop
python -m pipeline worker --once    # tek job sonra çık
```
