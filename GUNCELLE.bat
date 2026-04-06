@echo off
title RE-Tube Guncelleme
cd /d "%~dp0"
echo.
echo  RE-Tube Guncelleme Kontrol
echo  =========================
echo.
where git >/dev/null 2>&1
if %errorlevel% neq 0 (
    echo  [HATA] Git bulunamadi!
    pause
    exit /b 1
)
echo  Kontrol ediliyor...
git fetch origin main >/dev/null 2>&1
git status
echo.
git pull origin main
echo.
echo  Bitti. RE-Tube.bat ile programi baslatin.
echo.
pause
