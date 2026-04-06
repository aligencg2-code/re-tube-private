@echo off
chcp 65001 >nul 2>&1
title RE-Tube - YouTube Otomasyon
color 0A

echo.
echo  ╔═══════════════════════════════════════╗
echo  ║                                       ║
echo  ║   R E - T U B E                       ║
echo  ║   YouTube Otomasyon Pipeline           ║
echo  ║                                       ║
echo  ╚═══════════════════════════════════════╝
echo.

:: Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo  [HATA] Python bulunamadi!
    echo  Python 3.10+ yukleyin: https://www.python.org/downloads/
    echo  Kurulumda "Add to PATH" kutusunu isaretleyin.
    pause
    exit /b 1
)

:: Check FFmpeg
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    echo  [UYARI] FFmpeg bulunamadi. Video uretimi icin gerekli.
    echo  Indirin: https://www.gyan.dev/ffmpeg/builds/
    echo.
)

:: Navigate to script directory
cd /d "%~dp0"

:: Check dependencies
echo  Bagimliliklar kontrol ediliyor...
python -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo  Streamlit kuruluyor...
    pip install streamlit edge-tts >nul 2>&1
)
python -c "import anthropic" >nul 2>&1
if %errorlevel% neq 0 (
    echo  Pipeline bagimliliklari kuruluyor...
    pip install -r requirements.txt >nul 2>&1
)

echo  Bagimliliklar tamam.
echo.
echo  ════════════════════════════════════════
echo   RE-Tube baslatiliyor...
echo   Tarayicida acilacak: http://localhost:8501
echo   Kapatmak icin bu pencereyi kapatin.
echo  ════════════════════════════════════════
echo.

:: Open browser after 3 seconds
start "" cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:8501"

:: Start Streamlit
python -m streamlit run app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false
