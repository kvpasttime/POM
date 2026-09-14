@echo off
title POM Quick Start
cd /d "%~dp0"

echo.
echo  ==== POM Procurement Quote System ====
echo.

rem ---------- backend venv ----------
if not exist "backend\.venv\Scripts\python.exe" (
  echo [1/4] First run: creating Python venv and installing deps...
  python -m venv backend\.venv || goto :error
  call backend\.venv\Scripts\python.exe -m pip install -q --upgrade pip
  call backend\.venv\Scripts\python.exe -m pip install -q -r backend\requirements.txt || goto :error
) else (
  echo [1/4] Python venv OK
)

rem ---------- frontend deps ----------
if not exist "frontend\node_modules" (
  echo [2/4] First run: installing frontend deps (about 1 min)...
  pushd frontend
  call npm.cmd install --no-audit --no-fund || goto :error
  popd
) else (
  echo [2/4] Frontend deps OK
)

rem ---------- seed admin if needed ----------
echo [3/4] Init database and admin seed...
pushd backend
call .venv\Scripts\python.exe -m app.seed
popd

rem ---------- start services ----------
echo [4/4] Starting services...
start "POM-Backend(8000)" /D "%~dp0backend" ".venv\Scripts\python.exe" -m uvicorn app.main:app --port 8000
start "POM-Frontend(5173)" /D "%~dp0frontend" cmd /c "npm.cmd run dev"

echo.
echo Waiting for services...
timeout /t 6 /nobreak >nul
start http://localhost:5173

echo.
echo  Running:
echo    Frontend  http://localhost:5173   (browser opened)
echo    Backend   http://localhost:8000/docs
echo    First login: if backend\pom.db was just created, admin password is printed above. CHANGE IT after login.
echo    Stop: close the two black windows "POM-Backend/POM-Frontend", or run stop.bat
echo.
pause
exit /b 0

:error
echo.
echo Startup failed, check errors above.
pause
exit /b 1
