@echo off
echo ======================================================
echo 🚀  BLUMI GIT REPO CLEANER — Secret Purge Utility
echo ======================================================

:: Ensure git-filter-repo is installed
pip show git-filter-repo >nul 2>&1
if %errorlevel% neq 0 (
    echo 🔧 Installing git-filter-repo...
    pip install git-filter-repo
)

echo.
echo 🧹 Cleaning repository history (removing secret files)...
git filter-repo ^
    --path backend/bots/scheduler/utils/env.py ^
    --path backend/bots/scheduler/platforms/client_secret.json ^
    --path backend/bots/scheduler/platforms/token.pickle ^
    --path backend/bots/postbot/utils/env.py ^
    --invert-paths ^
    --force

echo.
echo 🔗 Reconnecting remote...
git remote remove origin 2>nul
git remote add origin https://github.com/1blumi444eva-sys/blumi.git

echo.
echo 🧱 Adding .gitignore rules to protect future secrets...
(
    echo # Sensitive files
    echo *.env
    echo token.pickle
    echo backend/bots/**/utils/env.py
    echo backend/bots/**/platforms/client_secret.json
) > .gitignore

git add .gitignore
git commit -m "Add .gitignore for sensitive files" >nul 2>&1

echo.
echo 🚀 Pushing clean repo to GitHub (force overwrite)...
git push -u origin main --force

echo.
echo ✅ Done! Your repository history is now clean.
pause
