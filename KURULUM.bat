@echo off
title RE-Tube - Kurulum
cd /d "%~dp0"

echo.
echo  RE-Tube - Ilk Kurulum
echo  =====================
echo.

:: Find Python
set PYTHON=
where python >nul 2>&1 && set PYTHON=python
if not defined PYTHON (
    where py >nul 2>&1 && set PYTHON=py
)
if not defined PYTHON (
    where python3 >nul 2>&1 && set PYTHON=python3
)
if not defined PYTHON (
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

echo  [OK] Python bulundu: %PYTHON%

where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo  [UYARI] FFmpeg bulunamadi - video uretimi icin gerekli.
) else (
    echo  [OK] FFmpeg bulundu.
)

where git >nul 2>&1
if %errorlevel% neq 0 (
    echo  [UYARI] Git bulunamadi - otomatik guncelleme icin gerekli.
) else (
    echo  [OK] Git bulundu.
)

echo.
echo  Paketler yukleniyor...
echo.

%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install -r requirements.txt
%PYTHON% -m pip install streamlit edge-tts

echo.
echo  =====================
echo  Kurulum tamamlandi!
echo  =====================
echo.
echo  Simdi RE-Tube.bat dosyasina cift tiklayarak programi baslatin.
echo.
echo  Destek: t.me/reworar
echo.
pause
