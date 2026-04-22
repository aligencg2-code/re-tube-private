@echo off
title RE-Tube
cd /d "%~dp0"
cls

echo.
echo  ========================================
echo    RE-Tube v2.0 - YouTube Otomasyon
echo  ========================================
echo.

set PYTHON=
where python >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=python
    goto found
)
where py >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=py
    goto found
)

echo  [HATA] Python bulunamadi!
echo  Lutfen once KURULUM.bat dosyasini calistirin.
pause
exit /b 1

:found
echo  Python: %PYTHON%

:: --- Streamlit kontrolu ---
%PYTHON% -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ========================================
    echo    [UYARI] Streamlit yuklu degil!
    echo  ========================================
    echo.
    echo  Program ilk kez calistiriliyor veya paketler eksik.
    echo  Su anda yuklemeyi deneyecegim...
    echo.
    %PYTHON% -m pip install streamlit edge-tts qrcode pandas
    if %errorlevel% neq 0 (
        echo.
        echo  [KRITIK HATA] Streamlit yuklenemedi!
        echo.
        echo  Muhtemel sebep: Python surumu uyumsuz ^(3.14/3.15^).
        echo  Cozum: Python 3.12 yukleyin ve tekrar deneyin.
        echo.
        echo  Surum kontrolu:
        %PYTHON% --version
        echo.
        echo  KURULUM.bat dosyasini yeniden calistirmayi deneyin.
        pause
        exit /b 1
    )
    %PYTHON% -m pip install -r requirements.txt
    echo.
    echo  Yukleme tamamlandi.
    echo.
)

:: --- Son dogrulama ---
%PYTHON% -c "import streamlit" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [HATA] Streamlit hala calismiyor!
    echo  KURULUM.bat dosyasini calistirin.
    pause
    exit /b 1
)

echo.
echo  Panel baslatiliyor... http://localhost:8501
echo  Kapatmak icin bu pencereyi kapatin.
echo.

timeout /t 3 /nobreak >nul
start http://localhost:8501

%PYTHON% -m streamlit run app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false

pause
