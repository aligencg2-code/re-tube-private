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
if %errorlevel% neq 0 (
    echo  [HATA] Git bulunamadi!
    echo.
    echo  Git'i indirip yukleyin:
    echo    https://git-scm.com/download/win
    echo.
    echo  Alternatif: Yeni ZIP'i tekrar indirip klasoru degistirin.
    pause
    exit /b 1
)

:: --- .git klasoru var mi? ---
if exist ".git" (
    echo  [OK] Git reposu bulundu, guncelleme cekiliyor...
    goto git_update
)

:: --- Yok, ilk kez guncelliyor - repo'yu baglayalim ---
echo  Bu ilk guncelleme. Git reposu kuruluyor...
echo.
echo  Mevcut dosyalar KORUNACAK, yeni sadece yeni dosyalari ekleyecek.
echo.
pause

:: Git init + remote ekle + hard reset to main
git init >nul 2>&1
git remote remove origin >nul 2>&1
git remote add origin https://github.com/aligencg2-code/re-tube-private.git
if %errorlevel% neq 0 (
    echo  [HATA] Repo remote eklenmedi!
    echo  Internet baglantinizi kontrol edin.
    pause
    exit /b 1
)

echo  Son surum indiriliyor (bu birkaç dakika surebilir)...
git fetch origin main --depth=1
if %errorlevel% neq 0 (
    echo  [HATA] Indirme basarisiz!
    echo  Muhtemel sebepler:
    echo    - Internet baglantisi yok
    echo    - Private repo erisim izni yok (yoneticiye yazin)
    pause
    exit /b 1
)

echo  Dosyalar guncelleniyor...
git reset --hard origin/main
if %errorlevel% neq 0 (
    echo  [HATA] Dosyalar guncellenemedi!
    pause
    exit /b 1
)
goto update_done

:git_update
:: --- Normal guncelleme ---
echo  Son surum kontrol ediliyor...
git fetch origin main >nul 2>&1

echo.
echo  Mevcut durum:
git status --short
echo.

echo  Yeni surum indiriliyor...
git pull origin main
if %errorlevel% neq 0 (
    echo.
    echo  [HATA] Guncelleme basarisiz!
    echo  Olasi sebep: Yerel degisiklikleriniz var.
    echo.
    echo  Cozum: git reset --hard origin/main
    echo  ^(Uyari: Yerel degisiklikler SILINECEK^)
    echo.
    set /p FORCE="Hard reset yapilsin mi? (E/N): "
    if /i "%FORCE%"=="E" (
        git reset --hard origin/main
    ) else (
        pause
        exit /b 1
    )
)

:update_done
echo.
echo  ========================================
echo    GUNCELLEME TAMAMLANDI
echo  ========================================
echo.

:: Mevcut versiyon
if exist "version.json" (
    echo  Mevcut surum:
    type version.json | findstr current_version
    echo.
)

echo  Yeni ozellikleri gormek icin: CHANGELOG.md
echo  Programi baslatmak icin:      RE-Tube.bat
echo.

:: Eger KURULUM.bat son degiskenliyse uyari
echo  NOT: Yeni paketler gelmis olabilir.
echo  Ilk kez calistirmadan once bir kez KURULUM.bat calistirmaniz
echo  tavsiye edilir (eksik paket varsa yukler).
echo.
pause
