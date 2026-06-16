@echo off
REM ============================================================
REM  Mise a jour du menu Archi- (pyRevit) pour Revit 2025
REM  A placer/lancer depuis la racine du depot clone.
REM  Double-cliquer sur ce fichier suffit.
REM ============================================================

setlocal
cd /d "%~dp0"

echo ===============================================
echo   Mise a jour du menu Archi-
echo ===============================================
echo.

REM Verifie que git est installe
where git >nul 2>nul
if errorlevel 1 (
    echo [ERREUR] Git n'est pas installe ou pas dans le PATH.
    echo Telecharger Git ici : https://git-scm.com/download/win
    pause
    exit /b 1
)

echo Verification du depot...
git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
    echo [ERREUR] Ce dossier n'est pas un depot Git.
    echo Assurez-vous d'avoir clone le depot via "git clone".
    pause
    exit /b 1
)

echo Recuperation des dernieres modifications...
git fetch origin
if errorlevel 1 (
    echo [ERREUR] Impossible de contacter le depot distant.
    echo Verifiez votre connexion internet.
    pause
    exit /b 1
)

REM Sauvegarde toute modification locale non commitee, pour eviter les conflits
git stash --include-untracked >nul 2>nul

git pull origin main
if errorlevel 1 (
    echo.
    echo [ATTENTION] Le "pull" a echoue. Tentative avec la branche "master"...
    git pull origin master
)

echo.
echo ===============================================
echo   Mise a jour terminee.
echo   Fermez Revit s'il est ouvert, puis relancez-le
echo   (ou faites "Reload" depuis l'onglet pyRevit).
echo ===============================================
echo.
pause
