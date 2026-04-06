@echo off
title RE-Tube
cd /d "%~dp0"
echo.
echo  RE-Tube - YouTube Otomasyon
echo  ===========================
echo.
set PYTHON=
where python >/dev/null 2>&1
if %errorlevel%==0 (set PYTHON=python& goto found)
where py >/dev/null 2>&1
if %errorlevel%==0 (set PYTHON=py& goto found)
echo  [HATA] Python bulunamadi!
pause
exit /b 1
:found
echo  Python: %PYTHON%
%PYTHON% -c "import streamlit" >/dev/null 2>&1
if %errorlevel% neq 0 (
    echo  Paketler yukleniyor...
    %PYTHON% -m pip install streamlit edge-tts
    %PYTHON% -m pip install -r requirements.txt
    echo  Yuklendi.
)
echo  Baslatiliyor... http://localhost:8501
echo  Kapatmak icin bu pencereyi kapatin.
echo.
timeout /t 4 /nobreak >NUL
start http://localhost:8501
%PYTHON% -m streamlit run app.py --server.port 8501 --server.headless true --browser.gatherUsageStats false
pause
