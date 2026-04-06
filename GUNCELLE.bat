@echo off
title RE-Tube - Guncelleme
cd /d "%~dp0"

echo.
echo  RE-Tube - Guncelleme
echo  ====================
echo.

where git >nul 2>&1
if %errorlevel% neq 0 (
    echo  [HATA] Git bulunamadi!
    echo  https://git-scm.com/downloads adresinden Git yukleyin.
    pause
    exit /b 1
)

echo  Guncellemeler kontrol ediliyor...
echo.

git fetch origin main >nul 2>&1

for /f "tokens=*" %%a in ('git rev-parse HEAD 2^>nul') do set LOCAL=%%a
for /f "tokens=*" %%a in ('git rev-parse origin/main 2^>nul') do set REMOTE=%%a

if "%LOCAL%"=="%REMOTE%" (
    echo  Program guncel. Yapilacak bir sey yok.
    echo.
    pause
    exit /b 0
)

echo  Yeni guncelleme mevcut!
echo.

set /p CONFIRM=Guncellemek istiyor musunuz? (E/H):
if /i not "%CONFIRM%"=="E" (
    echo  Guncelleme iptal edildi.
    pause
    exit /b 0
)

echo.
echo  Guncelleme uygulanıyor...

git stash >nul 2>&1
git pull origin main >nul 2>&1

if %errorlevel% neq 0 (
    git reset --hard origin/main >nul 2>&1
)

pip install -r requirements.txt -q >nul 2>&1

echo.
echo  Guncelleme tamamlandi!
echo  RE-Tube.bat ile programi yeniden baslatin.
echo.
pause
