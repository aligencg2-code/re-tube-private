@echo off
title RE-Tube
cd /d "%~dp0"

echo.
echo  RE-Tube - YouTube Otomasyon
echo  ===========================
echo.

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [HATA] Python bulunamadi!
    echo  https://www.python.org/downloads/ adresinden Python 3.10+ yukleyin.
    echo  Kurulumda "Add to PATH" secenegini isaretleyin.
    pause
    exit /b 1
)

python -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo  Ilk calistirma - paketler yukleniyor...
    pip install streamlit edge-tts -q
    pip install -r requirements.txt -q
    echo  Paketler yuklendi.
)

echo  Program baslatiliyor...
echo  Tarayicide acilacak: http://localhost:8501
echo  Kapatmak icin bu pencereyi kapatin.
echo.

timeout /t 3 /nobreak >nul
start http://localhost:8501

python -m streamlit run app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false
