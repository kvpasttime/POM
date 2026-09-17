@echo off
cd /d "D:\POM\backend"
start "POM-Backend-8000" "D:\POM\backend\.venv\Scripts\python.exe" -m uvicorn app.main:app --port 8000
cd /d "D:\POM\frontend"
start "POM-Frontend-5173" cmd /c "npm.cmd run dev"
exit /b 0
