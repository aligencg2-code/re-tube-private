@echo off
title RE-Tube Kurulum
cd /d "%~dp0"
echo.
echo  RE-Tube Ilk Kurulum
echo  =====================
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
echo  [OK] Python: %PYTHON%
echo.
echo  Paketler yukleniyor...
%PYTHON% -m pip install --upgrade pip
%PYTHON% -m pip install -r requirements.txt
%PYTHON% -m pip install streamlit edge-tts
echo.
echo  Kurulum tamamlandi!
echo  RE-Tube.bat ile programi baslatin.
echo.
pause
