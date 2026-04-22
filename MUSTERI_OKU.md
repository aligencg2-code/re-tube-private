# 🎬 RE-Tube'a Hoş Geldin!

**Satın aldığın için teşekkürler.** Bu rehber 10 dakikada kurulumu bitirir ve ilk videonu üretmeni sağlar.

> 💡 **Hiçbir kod yazmak zorunda değilsin.** Aşağıdaki adımları sırayla takip et yeterli.

---

## 📦 Paket İçeriği

| Dosya | Açıklama |
|---|---|
| `KURULUM.bat` | Kurulum başlatıcı — buraya çift tıkla |
| `RE-Tube.bat` | Program başlatıcı — her kullanım için |
| `GUNCELLE.bat` | Güncelleme çekmek için |
| `app.py`, `pipeline/` | Programın kendisi (değiştirme) |
| `references/` | Detaylı teknik doküman |

---

## ⚡ 5 Adımda Kurulum

### Adım 1 — Python'u yükle (5 dakika)

1. https://www.python.org/downloads/ adresine git
2. **"Download Python 3.12"** butonuna bas
3. İndirdiğin `.exe` dosyasını çalıştır
4. **⚠️ ÖNEMLİ:** Kurulum ekranında **"Add Python to PATH"** kutusunu işaretle (yoksa program çalışmaz)
5. "Install Now" → bekle → "Close"

**Kontrol:** Başlat menüsüne "cmd" yaz → `python --version` → "Python 3.12.x" yazmalı

### Adım 2 — FFmpeg'i yükle (3 dakika)

Video birleştirme için gerekli. İki seçenek:

**Kolay yol (Windows):**
1. https://www.gyan.dev/ffmpeg/builds/ → "release full" → `ffmpeg-release-full.7z` indir
2. 7-Zip ile aç, içindeki `bin` klasörünü `C:\ffmpeg\bin` olarak kopyala
3. Başlat menü → "environment variables" → **Path** değişkenine `C:\ffmpeg\bin` ekle
4. Terminal'i kapat yeniden aç, `ffmpeg -version` ile kontrol et

**Otomatik yol (eğer winget varsa):**
```
winget install ffmpeg
```

### Adım 3 — Programı kur

1. Sana gönderdiğim `RE-Tube.zip` dosyasını **masaüstüne** çıkar
2. Çıkan klasörün içinde `KURULUM.bat` dosyasına **çift tıkla**
3. Siyah ekran açılır, otomatik paketler yüklenir (~2 dakika)
4. "Kurulum tamamlandi" yazınca pencereyi kapat

### Adım 4 — API anahtarlarını gir

RE-Tube, AI sağlayıcıların API'lerini kullanır. **En az 2 key gerekli**, diğerleri opsiyonel.

**🔴 Zorunlu:**

| Sağlayıcı | Ücretsiz kredi | Nereden alınır |
|---|---|---|
| **Anthropic Claude** | $5 | https://console.anthropic.com/settings/keys |
| **Google Gemini** | Ücretsiz tier | https://aistudio.google.com/apikey |

**🟡 Önerilir (seçmeli):**

| Sağlayıcı | Ne için | Link |
|---|---|---|
| **Pexels** | Stok fotoğraf (ücretsiz) | https://www.pexels.com/api/new/ |
| **ElevenLabs** | Premium seslendirme | https://elevenlabs.io/ |
| **Voixor** | Türkçe TTS (uygun fiyat) | https://voixor.com |
| **OpenAI** | GPT-4o + DALL-E + Whisper | https://platform.openai.com/api-keys |

### Adım 5 — Programı başlat

1. Klasörde `RE-Tube.bat` dosyasına **çift tıkla**
2. Siyah terminal açılır, tarayıcın otomatik `http://localhost:8501` sayfasını açar
3. Sol menüden **"Ayarlar"** → **"API Anahtarları"** → 2. adımda aldığın key'leri gir → **"Kaydet"**
4. **YouTube bağlantısı**: Ayarlar → "Kanallar" → "Yeni Kanal Ekle" → kanalının adını gir → sana verilen komutu çalıştır → tarayıcıda YouTube girişi yap

**İlk video için:**
1. Sol menü → **"Pipeline"**
2. Konu yaz: örnek "*NASA Artemis 3 Ay görevi hakkında bilinmeyen 5 gerçek*"
3. Kanal seç, dil "Türkçe", süre "Short (~70 sn)"
4. **"Kuyruğa Ekle (Arka Planda Üret)"** butonuna bas
5. **"Kuyruk"** sayfasında ilerlemeyi izle (3-5 dakika sürer)
6. Tamamlandığında video YouTube'da (senin belirlediğin gizlilikle)

---

## 🎯 İlk hafta yapman gerekenler

- [ ] Kurulumu tamamla + API key'leri gir
- [ ] YouTube kanalını bağla (en az 1 kanal)
- [ ] İlk test videosunu üret
- [ ] Dashboard'daki **Maliyet** bölmesine bak — ne kadar harcadığını takip et
- [ ] **Ayarlar → Kanallar → Preset** kısmından kanalın için tercihlerini sakla
- [ ] **Araçlar → Haber Watcher** ile otomatik RSS takibi aç (isteğe bağlı)

---

## 🧰 Panel Haritası

| Sayfa | Ne yapar |
|---|---|
| **Dashboard** | Özet · aktif sağlayıcılar · son üretimler · kanal istatistikleri · harcama grafiği |
| **Pipeline** | Yeni video üret (konu yaz → kuyruğa ekle) |
| **Kuyruk** | Çalışan + bekleyen işler · ilerleme · iptal · tekrar dene |
| **Draftlar** | AI'nın ürettiği script'leri düzenle · yeniden üret |
| **Yorumlar** | YouTube yorumlarını AI ile sınıflandır · spam'i gizle |
| **🧰 Araçlar** | Viral skor · rakip takibi · haber watcher · ses klon · LoRA · çoklu dil · watermark · demo · zamanlayıcı · gelir tahmini · QR · Telegram bot |
| **Ayarlar** | API key'ler · kanallar · preset · sağlayıcı seçimi · multi-tenant · white-label · billing · audit log |

---

## 💡 Sık Karşılaşılan Sorular

**S: Python ile terminal komutu yazmak istemiyorum — başka yolu var mı?**
C: Yok çünkü RE-Tube Python tabanlı. Ama `KURULUM.bat` ve `RE-Tube.bat` dışında hiçbir komut yazmana gerek yok.

**S: Ücretsiz mi kullanabilirim?**
C: RE-Tube kendisi senin lisansınla gelir. AI sağlayıcıları (Claude, Gemini, ElevenLabs…) kendi fiyatlandırmasıyla çalışır. Ücretsiz stack için: Edge TTS + Pexels + Claude ücretsiz kredi → video başı ~$0.02.

**S: Maliyet ne kadar?**
C: Sağlayıcı seçimine bağlı. Ücretsiz stack: $0.02/video. Premium (ElevenLabs + Imagen 4 + Claude Sonnet): $0.20/video. **Ayarlar → Maliyet Hesaplayıcı** ile kendi kombinasyonunu test et.

**S: YouTube kanalım banlanır mı?**
C: Hayır. RE-Tube resmi YouTube Data API'sini kullanır. Upload'lar normal yoldan, kendi kanalının adına yapılır. Tek risk: içerik politikası ihlali (telif, yanıltıcı bilgi) — bunu önlemek için anti-halüsinasyon guard var.

**S: Aynı anda kaç video üretebilirim?**
C: Kuyruğa sınırsız ekleyebilirsin. Worker sırayla işler. Pratik limit: API rate-limit'leri (Claude dk'da 5, Gemini 15 vb.). Günde 50-100 video sürdürülebilir.

**S: Güncelleme nasıl gelir?**
C: `GUNCELLE.bat` dosyasına çift tıkla. Git üzerinden otomatik yeni sürüm gelir. Verilerin (drafts, config, kanallar) hiç etkilenmez.

---

## 🆘 Destek

Bir sorun yaşarsan:

1. **Log dosyasını aç:** `C:\Users\<kullanıcı adın>\.youtube-shorts-pipeline\logs\`
2. **Forum'da / bana yaz:** Hata mesajını ve log'un son 30 satırını ekle
3. **Acil durum:** `GUNCELLE.bat` ile son sürüme gel, genelde sorun gider

**İletişim:**
- Forum DM
- destek@retube.rewmarket.com
- retube.rewmarket.com

---

## 📜 Lisans

Satın aldığın lisansla kendi kullanımın için sınırsız video üretebilirsin.
- ✅ Kendi YouTube kanal(lar)ında kullan
- ✅ Ajans olarak müşterilerin için kullan (Agency plan)
- ❌ Programı başkasına satma / paylaşma (lisans devredilemez)
- ❌ Kaynak kodu public repo'ya koyma

Detaylı lisans metni: `LICENSE.txt`

---

## ✨ Özel İpuçları

1. **Maliyet tasarrufu:** Araçlar → Viral Skoru ile **her konuyu skorla**, düşük puanlıları kuyruğa ekleme. Ayda $100+ tasarruf.

2. **Çok dilli strateji:** 1 Türkçe video çek → Araçlar → Çoklu Dil → 5 dile çevir → 5 farklı kanala yükle. **5× gelir**.

3. **Gece modu:** Araçlar → Zamanlayıcı → "Burst 5" → gece yatmadan 5 konu bırak, sabah 5 video hazır. Pasif gelir için ideal.

4. **Rakip analizi:** Araçlar → Rakip Takibi → 3 rakip kanal ekle → topic gap'leri otomatik çıkar. Haftada 10 yeni konu fırsatı.

5. **A/B thumbnail:** Kanal preset'inde thumbnail A/B'yi aç. 3 varyant üretir, 24 saat sonra CTR'si en yüksek olanı kazanır. **%30-50 daha fazla izlenme**.

---

**İyi üretimler! 🎬**

*RE-Tube v2.0 · Enterprise Pack*
