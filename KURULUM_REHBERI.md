# RE-Tube Kurulum Rehberi

> YouTube Shorts & Video Otomasyon Pipeline — API Ayarları ve Kurulum

---

## 1. Sistem Gereksinimleri

| Gereksinim | Açıklama |
|------------|----------|
| **Python** | 3.10 veya üzeri |
| **FFmpeg** | Video birleştirme için gerekli |
| **Node.js** | Claude CLI için gerekli (opsiyonel) |

### Python Kurulumu
https://www.python.org/downloads/ adresinden indirin.
Kurulumda **"Add to PATH"** kutusunu işaretleyin.

### FFmpeg Kurulumu
- **Windows:** https://www.gyan.dev/ffmpeg/builds/ adresinden indirin, `C:\ffmpeg\bin` klasörüne çıkarın ve PATH'e ekleyin
- **macOS:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg`

Kontrol:
```bash
ffmpeg -version
```

---

## 2. Python Bağımlılıklarını Yükleyin

```bash
cd youtube-shorts-pipeline-main
pip install -r requirements.txt
pip install streamlit edge-tts
```

---

## 3. API Anahtarları

Programın çalışması için aşağıdaki servislere kayıt olup API anahtarı almanız gerekiyor.
Tüm anahtarlar `~/.youtube-shorts-pipeline/config.json` dosyasında saklanır.

### 3.1 — Google Gemini API (Zorunlu)

Görsel üretimi (Gemini Imagen) ve video üretimi (Veo) için kullanılır.

1. https://aistudio.google.com/apikey adresine gidin
2. Google hesabınızla giriş yapın
3. **"Create API Key"** butonuna tıklayın
4. Proje seçin veya yeni oluşturun
5. API anahtarını kopyalayın

> **Not:** Gemini Imagen ile görsel üretimi için Google Cloud'da faturalandırma (billing) aktif olmalıdır.
> Ücretsiz kotada görsel üretimi limiti 0'dır. Faturalandırma aktif edilmezse Pexels stok fotoğraflar kullanılır.

**Faturalandırma Aktif Etme:**
1. https://console.cloud.google.com adresine gidin
2. Sol menüden **"Billing"** seçin
3. Ödeme yöntemi ekleyin
4. Projenizi faturalandırma hesabına bağlayın

**Maliyet:** Görsel başına ~$0.04, Video (Veo) başına ~$0.25

---

### 3.2 — Pexels API (Ücretsiz — Önerilen)

Stok fotoğraf kaynağı. Gemini'ye alternatif, tamamen ücretsiz.

1. https://www.pexels.com/api/new/ adresine gidin
2. Hesap oluşturun
3. API anahtarınız otomatik oluşturulur
4. Kopyalayın

**Maliyet:** Ücretsiz, sınırsız

---

### 3.3 — ElevenLabs (Opsiyonel — Premium Ses)

Profesyonel seslendirme için. Yoksa Edge TTS (ücretsiz Microsoft seslendirme) kullanılır.

1. https://elevenlabs.io adresinde hesap oluşturun
2. Sağ üst profil ikonuna tıklayın → **"Profile + API key"**
3. API anahtarını kopyalayın

**Ücretsiz Plan:** Aylık 10.000 karakter (~8-10 kısa video)

**Ücretli Planlar:**
- Starter: $5/ay — 30.000 karakter
- Creator: $22/ay — 100.000 karakter

> **Dikkat:** VPN/proxy kullanıyorsanız ücretsiz plan engellenebilir. Bu durumda VPN'i kapatın veya ücretli plan alın.

**Ses Seçimi:**
Varsayılan ses: George (JBFqnCBsd6RMkjVDRZzb). Farklı ses istiyorsanız:
1. https://elevenlabs.io/voice-library adresinden ses seçin
2. Voice ID'yi config'e ekleyin:
```json
"VOICE_ID_EN": "seçtiğiniz_voice_id",
"VOICE_ID_TR": "turkce_voice_id"
```

---

### 3.4 — Anthropic Claude API (Opsiyonel)

Script üretimi için. Claude CLI (ücretsiz) veya API (ücretli) kullanabilirsiniz.

**Seçenek A: Claude CLI (Ücretsiz — Claude Max aboneliği ile)**

Claude Max aboneliğiniz varsa API anahtarına gerek yok:

```bash
npm install -g @anthropic-ai/claude-code
claude login
```

Tarayıcı açılacak, Anthropic hesabınızla giriş yapın. Bitti.

**Seçenek B: Claude API (Ücretli)**

1. https://console.anthropic.com/settings/keys adresine gidin
2. Hesap oluşturun
3. **"Create Key"** butonuna tıklayın
4. API anahtarını kopyalayın
5. Kredi yükleyin (sol menü → Plans & Billing)

**Maliyet:** ~$0.02 / video (Claude Sonnet)

---

## 4. YouTube OAuth Kurulumu

YouTube'a otomatik video yüklemek için OAuth 2.0 yetkilendirmesi gerekir.

### Adım 1: Google Cloud Console

1. https://console.cloud.google.com adresine gidin
2. Yeni proje oluşturun veya mevcut projeyi seçin
3. Sol menü → **"APIs & Services"** → **"Library"**
4. Arama: **"YouTube Data API v3"** → **"Enable"** tıklayın

### Adım 2: OAuth Credentials Oluşturma

1. **"APIs & Services"** → **"Credentials"**
2. **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**
3. Application type: **"Desktop app"**
4. İsim verin (örn: "RE-Tube Pipeline")
5. **"Create"** tıklayın
6. **JSON dosyasını indirin** ve proje klasörüne kaydedin

### Adım 3: OAuth Consent Screen

1. **"APIs & Services"** → **"OAuth consent screen"**
2. User type: **"External"** seçin
3. App name, email gibi zorunlu alanları doldurun
4. **"Save and Continue"**
5. Scopes ekranında bir şey eklemeyin, devam edin
6. Test users: **kendi Gmail adresinizi ekleyin**
7. **"Save"**

> **Önemli:** Publishing status'ü "Testing" modunda bırakın. Production'a almak Google review gerektirir.
> Test modunda sadece eklediğiniz hesaplar kullanabilir — kendi kanalınız için yeterli.

### Adım 4: Token Alma

```bash
python scripts/setup_youtube_oauth.py
```

Program `client_secret*.json` dosyasını otomatik bulacaktır. Tarayıcı açılacak:
1. Google hesabınızla giriş yapın
2. İzinleri onaylayın
3. Token otomatik kaydedilir: `~/.youtube-shorts-pipeline/youtube_token.json`

---

## 5. Yapılandırma (config.json)

Tüm ayarlar UI'dan (Ayarlar sayfası) veya doğrudan dosyadan düzenlenebilir.

**Dosya konumu:** `~/.youtube-shorts-pipeline/config.json`

### Örnek Yapılandırma

```json
{
  "ANTHROPIC_API_KEY": "",
  "ELEVENLABS_API_KEY": "sk_...",
  "GEMINI_API_KEY": "AIza...",
  "PEXELS_API_KEY": "LjWD...",
  "providers": {
    "script_ai": "claude_cli",
    "image": "pexels",
    "tts": "edge_tts"
  }
}
```

### Sağlayıcı Seçenekleri

| Kategori | Seçenek | Açıklama | Maliyet |
|----------|---------|----------|---------|
| **Script AI** | `claude_cli` | Claude CLI (Max abonelik) | Ücretsiz |
| | `claude_api` | Claude API | ~$0.02/video |
| | `gemini_script` | Gemini API | Ücretsiz kota var |
| **Görsel** | `pexels` | Pexels stok fotoğraf | Ücretsiz |
| | `gemini_imagen` | Gemini AI görsel üretimi | ~$0.04/görsel |
| | `veo` | Google Veo AI video üretimi | ~$0.25/klip |
| **Seslendirme** | `edge_tts` | Microsoft Edge TTS | Ücretsiz |
| | `elevenlabs` | ElevenLabs premium ses | ~$0.06/video |

---

## 6. Programı Çalıştırma

### Web Arayüzü (Önerilen)

```bash
cd youtube-shorts-pipeline-main
streamlit run app.py
```

Tarayıcıda http://localhost:8501 açılır. Tüm işlemleri buradan yapabilirsiniz.

### Komut Satırı

```bash
# Sadece taslak oluştur
python -m pipeline draft --news "konu başlığı" --lang tr

# Shorts üret (9:16, kısa)
python -m pipeline run --news "konu" --lang tr --format shorts --duration short

# 3 dakikalık video üret (16:9)
python -m pipeline run --news "konu" --lang tr --format video --duration 3min

# 5 dakikalık video üret
python -m pipeline run --news "konu" --lang tr --format video --duration 5min

# 10 dakikalık video üret
python -m pipeline run --news "konu" --lang tr --format video --duration 10min
```

### Manuel Üretim

Script ve görsel prompt'larınız hazırsa, web arayüzünde **"Manuel Üretim"** sayfasından:
1. Script'inizi yapıştırın
2. Her görsel için prompt girin
3. Format ve dil seçin
4. "Manuel Üretimi Başlat" tıklayın

---

## 7. Video Başına Tahmini Maliyet

### En Ucuz Senaryo (Hepsi Ücretsiz)

| Servis | Maliyet |
|--------|---------|
| Claude CLI (Max) | $0.00 |
| Pexels stok foto | $0.00 |
| Edge TTS | $0.00 |
| YouTube API | $0.00 |
| **Toplam** | **$0.00** |

### Orta Senaryo

| Servis | Maliyet |
|--------|---------|
| Claude API | ~$0.02 |
| Gemini Imagen (6 görsel) | ~$0.24 |
| ElevenLabs | ~$0.06 |
| **Toplam** | **~$0.32** |

### Premium Senaryo (AI Video)

| Servis | Maliyet |
|--------|---------|
| Claude API | ~$0.02 |
| Google Veo (6 video klip) | ~$1.50 |
| ElevenLabs | ~$0.06 |
| **Toplam** | **~$1.58** |

---

## 8. Sık Sorulan Sorular

**S: VPN açıkken ElevenLabs çalışmıyor?**
C: ElevenLabs ücretsiz planda VPN/proxy algıladığında hesabı kilitler. VPN'i kapatın veya ücretli plan alın.

**S: Gemini görsel üretmiyor, "quota exceeded" hatası veriyor?**
C: Google Cloud'da faturalandırma aktif değil. Billing ekleyin veya Pexels'i kullanın.

**S: YouTube yükleme başarısız oluyor?**
C: OAuth token süresi dolmuş olabilir. `python scripts/setup_youtube_oauth.py` ile yenileyin.

**S: Türkçe karakterler bozuk görünüyor?**
C: Terminal encoding sorunu. Program UTF-8 kullanır, Windows CMD yerine PowerShell veya Git Bash kullanın.

**S: Whisper çok yavaş çalışıyor?**
C: İlk çalıştırmada model indirilir (~1.5GB). GPU varsa otomatik kullanılır, yoksa CPU'da daha yavaş çalışır.

---

## 9. Dosya Yapısı

```
~/.youtube-shorts-pipeline/
├── config.json              ← API anahtarları ve sağlayıcı ayarları
├── youtube_token.json       ← YouTube OAuth token
├── drafts/                  ← Üretilen taslaklar (JSON)
│   ├── 1775142142.json
│   └── ...
├── media/                   ← Üretilen videolar (MP4)
│   ├── pipeline_1775142142_tr.mp4
│   └── ...
└── logs/                    ← Log dosyaları
```

---

## 10. Destek

Sorularınız için: **[t.me/reworar](https://t.me/reworar)**
