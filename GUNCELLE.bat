@echo off
title RE-Tube Guncelleme
cd /d "%~dp0"
cls

echo.
echo  ========================================
echo    RE-Tube Guncelleme Kontrol
echo  ========================================
echo.

:: --- Git kontrolu ---
where git >nul 2>&1
if errorlevel 1 goto no_git

:: --- .git klasoru ve durum tespiti ---
if exist ".git" goto check_remote
goto first_install

:check_remote
:: Remote tanimli mi?
git remote get-url origin >nul 2>&1
if errorlevel 1 goto repair_repo
goto try_pull

:try_pull
echo  Son surum kontrol ediliyor...
git fetch origin main >nul 2>&1
echo.
echo  Yeni surum indiriliyor...
git pull origin main
if errorlevel 1 goto repair_repo
goto update_done

:first_install
echo  Bu ilk guncelleme. Git reposu kuruluyor...
echo.
echo  Mevcut dosyalar KORUNACAK.
echo.
pause
goto repair_repo

:repair_repo
echo.
echo  Repo onariliyor / kuruluyor...
git init >nul 2>&1
git remote remove origin >nul 2>&1
git remote add origin https://github.com/aligencg2-code/re-tube-private.git
echo  Son surum indiriliyor...
git fetch origin main --depth=1
if errorlevel 1 goto fetch_failed
echo  Dosyalar guncelleniyor...
git reset --hard origin/main >nul
if errorlevel 1 goto reset_failed
goto update_done

:no_git
echo  [HATA] Git bulunamadi!
echo.
echo  Git'i indirip yukleyin:
echo    https://git-scm.com/download/win
echo.
pause
exit /b 1

:fetch_failed
echo.
echo  [HATA] Repo'ya erisilemiyor.
echo  Muhtemel sebepler:
echo    - Internet baglantisi yok
echo    - GitHub credentials gerekli
echo    - Repo erisim izni yok (yoneticiye yazin)
pause
exit /b 1

:reset_failed
echo.
echo  [HATA] Dosyalar guncellenemedi!
pause
exit /b 1

:update_done
echo.
echo  ========================================
echo    GUNCELLEME TAMAMLANDI
echo  ========================================
echo.

if exist "version.json" (
    echo  Mevcut surum:
    type version.json | findstr current_version
    echo.
)

echo  Programi baslatmak icin: RE-Tube.bat
echo.
echo  NOT: Yeni paketler gelmis olabilir.
echo  Ilk kez calistirmadan once KURULUM.bat tavsiye edilir.
echo.
pause
