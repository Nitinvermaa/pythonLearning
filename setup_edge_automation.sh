#!/bin/bash

# Edge Browser Automation Setup Script
# This script helps you set up everything needed for Edge automation

set -e  # Exit on error

echo "=========================================="
echo "Edge Browser Automation Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "✅ Found Python $PYTHON_VERSION"

# Check if pip is available
echo ""
echo "Checking pip..."
if ! $PYTHON_CMD -m pip --version &> /dev/null; then
    echo "❌ pip is not installed. Please install pip first."
    exit 1
fi
echo "✅ pip is available"

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
echo "This may take a few minutes..."
$PYTHON_CMD -m pip install -q --upgrade pip
$PYTHON_CMD -m pip install -q playwright pandas openpyxl matplotlib

if [ $? -eq 0 ]; then
    echo "✅ Python dependencies installed successfully"
else
    echo "❌ Failed to install Python dependencies"
    exit 1
fi

# Install Playwright browsers
echo ""
echo "Installing Playwright browsers..."
echo "This may take a few minutes (downloading ~100-200 MB)..."
$PYTHON_CMD -m playwright install msedge

if [ $? -eq 0 ]; then
    echo "✅ Microsoft Edge for Playwright installed successfully"
else
    echo "❌ Failed to install Microsoft Edge"
    exit 1
fi

# Run verification tests
echo ""
echo "=========================================="
echo "Running Verification Tests"
echo "=========================================="
echo ""
$PYTHON_CMD test_edge_setup.py

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Review EDGE_AUTOMATION_README.md for usage guide"
echo "2. Check EDGE_PROFILE_GUIDE.md for detailed documentation"
echo "3. Try the examples:"
echo "   python launch_edge_with_profile.py --url 'https://example.com'"
echo "   python edge_profile_example.py"
echo ""
echo "Happy automating! 🚀"
