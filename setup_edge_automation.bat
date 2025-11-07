@echo off
REM Edge Browser Automation Setup Script for Windows
REM This script helps you set up everything needed for Edge automation

echo ==========================================
echo Edge Browser Automation Setup
echo ==========================================
echo.

REM Check Python
echo Checking Python installation...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [31mPython is not installed or not in PATH.[0m
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

python --version
echo [32mPython found[0m
echo.

REM Check pip
echo Checking pip...
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [31mpip is not available.[0m
    pause
    exit /b 1
)
echo [32mpip is available[0m
echo.

REM Install Python dependencies
echo Installing Python dependencies...
echo This may take a few minutes...
python -m pip install --upgrade pip
python -m pip install playwright pandas openpyxl matplotlib

if %errorlevel% neq 0 (
    echo [31mFailed to install Python dependencies[0m
    pause
    exit /b 1
)
echo [32mPython dependencies installed successfully[0m
echo.

REM Install Playwright browsers
echo Installing Playwright browsers...
echo This may take a few minutes (downloading ~100-200 MB)...
python -m playwright install msedge

if %errorlevel% neq 0 (
    echo [31mFailed to install Microsoft Edge[0m
    pause
    exit /b 1
)
echo [32mMicrosoft Edge for Playwright installed successfully[0m
echo.

REM Run verification tests
echo ==========================================
echo Running Verification Tests
echo ==========================================
echo.
python test_edge_setup.py

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo Next steps:
echo 1. Review EDGE_AUTOMATION_README.md for usage guide
echo 2. Check EDGE_PROFILE_GUIDE.md for detailed documentation
echo 3. Try the examples:
echo    python launch_edge_with_profile.py --url "https://example.com"
echo    python edge_profile_example.py
echo.
echo Happy automating! 🚀
echo.
pause
