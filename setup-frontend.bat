@echo off
echo ========================================
echo Video Vault - Web Frontend Setup
echo ========================================
echo.

echo Step 1: Creating Vue 3 project with Vite...
call npm create vite@latest frontend -- --template vue

echo.
echo Step 2: Installing dependencies...
cd frontend
call npm install

echo.
echo Step 3: Installing UI libraries...
call npm install axios element-plus @element-plus/icons-vue
call npm install vue-router@4 pinia

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Create the necessary files as described in WEB_DEPLOYMENT.md
echo 2. Start backend: python backend/app.py
echo 3. Start frontend: cd frontend ^&^& npm run dev
echo.
pause
