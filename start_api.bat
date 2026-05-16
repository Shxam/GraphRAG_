@echo off
echo ========================================
echo PostMortemIQ API Starter
echo ========================================
echo.

echo Checking for processes on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    echo Found process %%a using port 8000
    echo Killing process %%a...
    taskkill /F /PID %%a >nul 2>&1
    if errorlevel 1 (
        echo Failed to kill process %%a
    ) else (
        echo Process %%a killed successfully
    )
)

echo.
echo Starting API server...
echo.
python main.py
