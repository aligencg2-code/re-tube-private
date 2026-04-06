@echo off
chcp 65001 >nul 2>&1
title RE-Tube - Guncelleme
color 0B

echo.
echo  ╔═══════════════════════════════════════╗
echo  ║                                       ║
echo  ║   R E - T U B E  G U N C E L L E M E ║
echo  ║                                       ║
echo  ╚═══════════════════════════════════════╝
echo.

cd /d "%~dp0"

echo  Guncellemeler kontrol ediliyor...
echo.
python updater.py check

echo.
set /p CONFIRM=Guncellemek istiyor musunuz? (E/H):
if /i "%CONFIRM%"=="E" (
    echo.
    echo  Guncelleme uygulanıyor...
    python updater.py update
    echo.
    echo  Tamamlandi! RE-Tube.bat ile programi yeniden baslatin.
) else (
    echo  Guncelleme iptal edildi.
)

echo.
pause
