@echo off
title RE-Tube v2.0 - Kurulum
cd /d "%~dp0"
cls

echo.
echo  ========================================
echo    RE-Tube v2.0 Enterprise Pack
echo    Kurulum Sihirbazi
echo  ========================================
echo.

:: --- Python kontrolu ---
set PYTHON=
where python >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=python
    goto python_found
)
where py >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=py
    goto python_found
)

echo  [HATA] Python bulunamadi!
echo.
echo  Lutfen Python 3.10, 3.11, 3.12 veya 3.13 yukleyin:
echo    https://www.python.org/downloads/
echo.
echo  KURULUMDA "Add Python to PATH" kutucugunu MUTLAKA isaretleyin.
echo.
echo  UYARI: Python 3.14 veya 3.15 KULLANMAYIN - henuz desteklenmiyor.
echo         Stabil surum: Python 3.12 onerilir.
echo.
pause
exit /b 1

:python_found
echo  [OK] Python bulundu: %PYTHON%
%PYTHON% --version
echo.

:: --- Python surum kontrolu (3.10-3.13 arasi desteklenir) ---
%PYTHON% -c "import sys; exit(0 if (3,10) <= sys.version_info[:2] <= (3,13) else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ========================================
    echo    [KRITIK UYARI] PYTHON SURUMU UYUMSUZ
    echo  ========================================
    echo.
    %PYTHON% -c "import sys; print(f'  Mevcut surum: Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
    echo  Desteklenen: Python 3.10, 3.11, 3.12, 3.13
    echo.
    echo  Python 3.14 ve 3.15 HENUZ Streamlit tarafindan desteklenmiyor.
    echo.
    echo  COZUM: Python 3.12 yukleyin (en stabil surum):
    echo    1. https://www.python.org/downloads/release/python-3127/
    echo    2. Kurulumda "Add Python to PATH" isaretleyin
    echo    3. Mevcut 3.14/3.15 kalabilir (ikisi yan yana yasayabilir)
    echo    4. Bilgisayari yeniden baslatin
    echo    5. KURULUM.bat tekrar calistirin
    echo.
    echo  Yine de devam etmek icin E tusuna basin (basariszlik riski yuksek),
    echo  iptal icin N tusuna basin.
    echo.
    set /p FORCE="Devam edilsin mi? (E/N): "
    if /i not "%FORCE%"=="E" (
        echo  Iptal edildi. Lutfen Python 3.12 yukleyin.
        pause
        exit /b 1
    )
    echo  UYARI: Kendi sorumlulugunuzda devam ediyorsunuz.
    echo.
)

:: --- FFmpeg kontrolu ---
where ffmpeg >nul 2>&1
if %errorlevel%==0 (
    echo  [OK] FFmpeg bulundu
) else (
    echo  [UYARI] FFmpeg bulunamadi
    echo          Video birlestirme icin FFmpeg gerekli.
    echo          Indirme: https://www.gyan.dev/ffmpeg/builds/
)
echo.

:: --- pip yukselt ---
echo  [1/3] pip guncelleniyor...
%PYTHON% -m pip install --upgrade pip
if %errorlevel% neq 0 (
    echo  [HATA] pip guncelleme basarisiz
    echo  Internet baglantisi sorunu olabilir.
    pause
    exit /b 1
)
echo.

:: --- Ana paketler (hizli, kucuk paketler) ---
echo  [2/2] Paketler yukleniyor (1-2 dakika)...
echo.
%PYTHON% -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo  [HATA] Paket yukleme basarisiz!
    echo  Yukaridaki hata mesajini inceleyin.
    echo  Sik rastlanan sebepler:
    echo    - Python surumu uyumsuz (3.10-3.13 kullanin)
    echo    - Internet baglantisi yok
    pause
    exit /b 1
)
echo.

:: --- Streamlit import testi ---
echo  Kurulum dogrulaniyor...
%PYTHON% -c "import streamlit; print('  Streamlit surumu:', streamlit.__version__)"
if %errorlevel% neq 0 (
    echo  [HATA] Streamlit import edilemiyor!
    pause
    exit /b 1
)

echo.
echo  ========================================
echo    KURULUM BASARIYLA TAMAMLANDI
echo  ========================================
echo.
echo  Sonraki adimlar:
echo    1. MUSTERI_OKU.md dosyasini acin ve okuyun
echo    2. RE-Tube.bat ile programi baslatin
echo    3. Tarayici acildiginda Ayarlar - API Anahtarlari
echo       bolumunden kendi API key'lerinizi girin
echo.
echo  ALTYAZI (isteginize bagli):
echo    Altyazilar icin ucretsiz Groq API key onerilir:
echo      https://console.groq.com/keys
echo    Alternatif: OpenAI API, Deepgram, veya lokal whisper
echo    Hic altyazi istemiyorsaniz: degisiklik yapmayin, video
echo    altyazisiz uretilir, upload calismaya devam eder.
echo.
echo  Yardim:
echo    Log klasoru: %%USERPROFILE%%\.youtube-shorts-pipeline\logs
echo    Destek:      retube.rewmarket.com
echo.
pause
