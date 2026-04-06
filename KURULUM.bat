@echo off
title RE-Tube - Kurulum
cd /d "%~dp0"

echo.
echo  RE-Tube - Ilk Kurulum
echo  =====================
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [HATA] Python bulunamadi!
    echo.
    echo  1. https://www.python.org/downloads/ adresinden Python 3.10+ indirin
    echo  2. Kurulumda "Add to PATH" kutusunu isaretleyin
    echo  3. Bilgisayari yeniden baslatin
    echo  4. Bu dosyayi tekrar calistirin
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo  [OK] %%i bulundu.

where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo  [UYARI] FFmpeg bulunamadi - video uretimi icin gerekli.
) else (
    echo  [OK] FFmpeg bulundu.
)

echo.
echo  Paketler yukleniyor...
echo.

pip install -r requirements.txt
pip install streamlit edge-tts

echo.
echo  =====================
echo  Kurulum tamamlandi!
echo  =====================
echo.
echo  Simdi yapmaniz gerekenler:
echo.
echo  1. RE-Tube.bat dosyasina cift tiklayarak programi baslatin
echo  2. Tarayicida Ayarlar sayfasindan API anahtarlarinizi girin
echo  3. YouTube yuklemesi icin asagidaki komutu calistirin:
echo     python scripts\setup_youtube_oauth.py
echo.
echo  Detayli bilgi: KURULUM_REHBERI.md dosyasini okuyun
echo  Destek: t.me/reworar
echo.
pause
