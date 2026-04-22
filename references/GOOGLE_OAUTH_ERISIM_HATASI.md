# 🔐 "Erişim engellendi: Google doğrulama sürecini tamamlamadı"

Bu hatayı **Google Cloud Console'dan Test User eklemeden** OAuth yapmaya çalıştığında alırsın.

> ⚠️ **Google doğrulama süreci 4-6 hafta sürer ve sana gerekmez.** Doğru çözüm: uygulamanın kendisini "Test" modunda tutup kendi email'ini "Test User" olarak eklemek. Bu 2 dakika sürer.

---

## 🎯 Çözüm (2 dakika)

### Adım 1 — Google Cloud Console'u aç

https://console.cloud.google.com/apis/credentials/consent

### Adım 2 — Doğru projeyi seç

Sağ üstte proje seçici var. client_secret.json'ı indirdiğin projeyi seç.

Örnek: proje adı "YouTube Upload Test" veya benzeri.

### Adım 3 — App Status kontrolü

Sayfa açılınca şöyle bir şey göreceksin:

```
┌────────────────────────────────────────────┐
│ User Type: External                         │
│ Publishing status: ○ Testing  [Publish]    │  ← Testing modunda OLMALI
└────────────────────────────────────────────┘
```

**✅ Eğer "Testing" modundaysa** → Adım 4'e geç.

**❌ Eğer "In production" ise** → "BACK TO TESTING" butonuna bas. Testing moduna dönsün.

### Adım 4 — Test User ekle

Aynı sayfada biraz aşağı in. **"Test users"** bölümünü bul:

```
┌────────────────────────────────────────────┐
│  Test users                                 │
│  ┌──────────────────────────────────────┐  │
│  │ + ADD USERS                          │  │  ← bu butona bas
│  └──────────────────────────────────────┘  │
│                                             │
│  (henuz kullanici yok)                     │
└────────────────────────────────────────────┘
```

**"+ ADD USERS"** butonuna bas.

Açılan alana **YouTube kanalının bağlı olduğu Google hesabının email adresini** yaz:

```
ornek.kullanici@gmail.com
```

**"SAVE"** bas.

### Adım 5 — Tekrar OAuth dene

Terminale geri dön:

```cmd
python scripts/setup_youtube_oauth.py --channel ayaz
```

Tarayıcı açılınca:
1. Eklediğin email hesabıyla giriş yap
2. Google "Google hasn't verified this app" uyarısı gösterebilir
3. **"Advanced"** linkine tıkla
4. **"Go to [App Name] (unsafe)"** linkine tıkla
5. İzinler sayfasında **"Continue"** bas

Artık token başarıyla kaydedilecek ✅

---

## 🤔 Neden bu hata?

Google, OAuth uygulamalarının kötüye kullanılmasını önlemek için:
- **Yayınlanmış (Production)** uygulamalar için güvenlik doğrulaması ister (hassas scope'lar varsa)
- **Test** modundaki uygulamalar sadece sen tarafından eklenen **test user'lar** kullanabilir

RE-Tube kendi kanalın için çalıştığından **Test modunda kalması en mantıklısı**. Kimin kullanacağını sen belirlersin (Test Users listesi).

## 👥 Kaç test user ekleyebilirim?

**100 test user** (Google limiti). Ajans olarak farklı müşteri kanallarını yönetiyorsan hepsini ekleyebilirsin.

## 🔄 Test User ekledikten sonra da hata alıyor musum?

### Senaryo 1: "Google hasn't verified this app" uyarısı

Bu **hata değil, uyarı**. Normal. Şu adımlarla geç:

1. Uyarı ekranında **"Advanced"** (gelişmiş) linkine tıkla
2. Aşağıda **"Go to [app name] (unsafe)"** linki çıkar → tıkla
3. OAuth izin ekranı açılır → Continue → token kaydedilir

### Senaryo 2: "403: access_denied"

Test user ekledin ama **yanlış email** ile giriş yapıyorsun. Test user listesindeki emailinle login olduğundan emin ol.

### Senaryo 3: "redirect_uri_mismatch"

client_secret.json'u **"Desktop app"** olarak değil **"Web application"** olarak oluşturmuşsun.

Çözüm:
1. Google Cloud Console → Credentials
2. Eski OAuth Client ID'yi sil
3. **"+ CREATE CREDENTIALS"** → OAuth client ID → **"Desktop app"** seç
4. DOWNLOAD JSON → yeni client_secret.json kullan

### Senaryo 4: "This app is blocked"

App tamamen blocked — Google Cloud projenizi kapatmış. Çok nadir. Yeni proje oluştur:

1. https://console.cloud.google.com → yeni proje
2. APIs & Services → Library → "YouTube Data API v3" ara → ENABLE
3. OAuth consent screen → External → kendini test user ekle
4. Credentials → OAuth Client ID → Desktop app → JSON indir
5. Yeni client_secret.json ile tekrar dene

---

## 📺 Adım adım video rehberi

**Yakında:** Müşteri için tüm süreç video olarak da hazırlanacak.

## 📞 Takıldıysan destek

- Forum DM
- retube.rewmarket.com
- Log dosyası: `%USERPROFILE%\.youtube-shorts-pipeline\logs\`
