@echo off
title RE-Tube
cd /d "%~dp0"

echo.
echo  RE-Tube - YouTube Otomasyon
echo  ===========================
echo.

:: Find Python - try python, then py, then python3
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
    echo  2. Kurulumda "Add to PATH" secenegini isaretleyin
    echo  3. Bilgisayari yeniden baslatin
    echo  4. Bu dosyayi tekrar calistirin
    echo.
    pause
    exit /b 1
)

echo  Python bulundu: %PYTHON%

:: Install missing packages
%PYTHON% -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo  Ilk calistirma - paketler yukleniyor, bu birkaC dakika surebilir...
    echo.
    %PYTHON% -m pip install streamlit edge-tts
    %PYTHON% -m pip install -r requirements.txt
    echo.
    echo  Paketler yuklendi.
    echo.
)

echo  Program baslatiliyor...
echo  Tarayicide acilacak: http://localhost:8501
echo  Kapatmak icin bu pencereyi kapatin.
echo.

timeout /t 4 /nobreak >nul
start http://localhost:8501

%PYTHON% -m streamlit run app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false

if %errorlevel% neq 0 (
    echo.
    echo  [HATA] Program baslatilamadi.
    echo  Lutfen KURULUM.bat dosyasini once calistirin.
    pause
)
