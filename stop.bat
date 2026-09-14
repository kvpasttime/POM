@echo off
title POM Stop Services
echo Stopping POM services...

setlocal enabledelayedexpansion
for %%P in (8000 5173 5174) do (
  for /f "tokens=5" %%F in ('netstat -ano ^| findstr ":%%P " ^| findstr "LISTENING"') do (
    echo Stopping port %%P PID=%%F
    taskkill /F /PID %%F >nul 2>&1
  )
)
echo Stopped.
pause
