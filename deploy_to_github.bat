@echo off
title SolveHub - Push to GitHub
echo ============================================================
echo           SolveHub: Automated GitHub Deployment
echo ============================================================
echo.

where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Git is not installed or not found in system PATH.
    echo.
    echo To push your code, Git for Windows is required:
    echo 1. Download official installer: https://git-scm.com/download/win
    echo 2. Run the installer and keep the default options.
    echo 3. Re-run this script or use VS Code's 'Publish to GitHub' button!
    echo.
    echo Opening Git download page in your browser...
    start https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

echo [OK] Git is installed on your computer.
echo.

if not exist ".git" (
    echo [*] Initializing local Git repository...
    git init
) else (
    echo [*] Local Git repository already initialized.
)

echo [*] Staging all project files...
git add .

echo [*] Creating commit...
git commit -m "Initial commit: SolveHub Civic Problem-Solving Platform" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Changes committed successfully.
) else (
    echo [*] Working directory is up to date.
)

git branch -M main

echo.
echo [*] Repository URL is pre-configured to:
echo     https://github.com/shadintk/solvehub.git
echo [*] Branch: main
echo.
git remote remove origin >nul 2>&1
git remote add origin https://github.com/shadintk/solvehub.git

echo [*] Pushing code to GitHub (main branch)...
echo (If prompted for Password, use your GitHub Personal Access Token)
echo.
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo [SUCCESS] Your SolveHub project is now deployed on GitHub!
    echo Visit: https://github.com/shadintk/solvehub
    echo ============================================================
) else (
    echo.
    echo [!] Push encountered an issue. Check your internet connection or GitHub credentials.
)

echo.
pause
