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

:: --- .git klasoru var mi VE saglikli mi? ---
if exist ".git" (
    :: Remote tanimli mi kontrol et - eski bozuk repo'ya karsi koruma
    git remote get-url origin >nul 2>&1
    if errorlevel 1 (
        echo  [UYARI] .git klasoru var ama bozuk - remote tanimli degil.
        echo          Otomatik onariliyor...
        echo.
        goto repair_repo
    )
    echo  [OK] Git reposu bulundu, guncelleme cekiliyor...
    goto git_update
)

:: --- Yok, ilk kez guncelliyor - repo'yu baglayalim ---
echo  Bu ilk guncelleme. Git reposu kuruluyor...
echo.
echo  Mevcut dosyalar KORUNACAK, yeni sadece yeni dosyalari ekleyecek.
echo.
pause

:repair_repo
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

echo  Son surum indiriliyor (birkac dakika surebilir)...
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
git pull origin main 2>nul
if %errorlevel% neq 0 (
    echo.
    echo  [UYARI] git pull basarisiz oldu.
    echo          Repo bozuk olabilir, otomatik onarim deneniyor...
    echo.

    :: Remote'u sifirla, fetch + reset
    git remote remove origin >nul 2>&1
    git remote add origin https://github.com/aligencg2-code/re-tube-private.git

    git fetch origin main --depth=1
    if errorlevel 1 (
        echo.
        echo  [HATA] Repo'ya erisilemiyor.
        echo  Muhtemel sebepler:
        echo    - Internet baglantisi yok
        echo    - GitHub credentials gerekli
        echo    - Repo erisim izni yok ^(yoneticiye yazin^)
        pause
        exit /b 1
    )

    echo  Dosyalar zorla guncelleniyor ^(yerel degisiklikler korunmuyor^)...
    git reset --hard origin/main
    if errorlevel 1 (
        echo  [HATA] Hard reset basarisiz!
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
