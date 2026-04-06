@echo off
chcp 65001 >nul 2>&1
title RE-Tube - Ilk Kurulum
color 0E

echo.
echo  ╔═══════════════════════════════════════╗
echo  ║                                       ║
echo  ║   R E - T U B E  K U R U L U M       ║
echo  ║   Ilk Kurulum Sihirbazi               ║
echo  ║                                       ║
echo  ╚═══════════════════════════════════════╝
echo.

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [HATA] Python bulunamadi!
    echo.
    echo  1. https://www.python.org/downloads/ adresinden Python 3.10+ indirin
    echo  2. Kurulumda "Add to PATH" kutusunu MUTLAKA isaretleyin
    echo  3. Kurulum bittikten sonra bu dosyayi tekrar calistirin
    echo.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  [OK] Python %PYVER% bulundu.

:: Check FFmpeg
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo  [UYARI] FFmpeg bulunamadi.
    echo  Video uretimi icin FFmpeg gerekli.
    echo  https://www.gyan.dev/ffmpeg/builds/ adresinden indirin
    echo  ve C:\ffmpeg\bin klasorunu PATH'e ekleyin.
    echo.
) else (
    echo  [OK] FFmpeg bulundu.
)

:: Navigate to script directory
cd /d "%~dp0"

echo.
echo  ════════════════════════════════════════
echo   Python paketleri yukleniyor...
echo  ════════════════════════════════════════
echo.

pip install -r requirements.txt
pip install streamlit edge-tts

echo.
echo  ════════════════════════════════════════
echo   Kurulum tamamlandi!
echo  ════════════════════════════════════════
echo.
echo  Simdi yapmaniz gerekenler:
echo.
echo  1. RE-Tube.bat dosyasini cift tiklayarak programi baslatin
echo  2. Tarayicida Ayarlar sayfasindan API anahtarlarinizi girin
echo  3. YouTube OAuth icin asagidaki komutu calistirin:
echo     python scripts\setup_youtube_oauth.py
echo.
echo  Detayli bilgi: KURULUM_REHBERI.md dosyasini okuyun
echo.
echo  Destek: t.me/reworar
echo.
pause
