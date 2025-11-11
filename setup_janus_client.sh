#!/bin/bash
# Setup script for Janus WebRTC Client

set -e

echo "=========================================="
echo "Janus WebRTC Client Setup"
echo "=========================================="
echo ""

# Check if running on WSL
if grep -qi microsoft /proc/version; then
    echo "✓ Detected WSL environment"
    WSL=true
else
    echo "ℹ Running on native Linux"
    WSL=false
fi

# Update package list
echo ""
echo "Step 1: Updating package list..."
sudo apt update

# Install GStreamer and dependencies
echo ""
echo "Step 2: Installing GStreamer and plugins..."
sudo apt install -y \
    gstreamer1.0-tools \
    gstreamer1.0-nice \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer-plugins-bad1.0-dev \
    gir1.2-gst-plugins-base-1.0 \
    gir1.2-gstreamer-1.0

# Install Video4Linux
echo ""
echo "Step 3: Installing Video4Linux utilities..."
sudo apt install -y v4l-utils

# Install Python GObject
echo ""
echo "Step 4: Installing Python GObject bindings..."
sudo apt install -y \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gtk-3.0 \
    python3-dev

# Install Python packages
echo ""
echo "Step 5: Installing Python dependencies..."
pip install -r requirements.txt

# Make scripts executable
echo ""
echo "Step 6: Making scripts executable..."
chmod +x janus_webrtc_client.py
chmod +x test_camera.py

# Verify installations
echo ""
echo "=========================================="
echo "Verifying Installation"
echo "=========================================="

# Check GStreamer
echo ""
echo "Checking GStreamer..."
if gst-launch-1.0 --version > /dev/null 2>&1; then
    echo "  ✓ GStreamer installed"
    gst-launch-1.0 --version | head -1
else
    echo "  ✗ GStreamer not found"
    exit 1
fi

# Check WebRTC plugin
echo ""
echo "Checking WebRTC plugin..."
if gst-inspect-1.0 webrtcbin > /dev/null 2>&1; then
    echo "  ✓ WebRTC plugin available"
else
    echo "  ✗ WebRTC plugin not found"
    exit 1
fi

# Check VP8 encoder
echo ""
echo "Checking VP8 encoder..."
if gst-inspect-1.0 vp8enc > /dev/null 2>&1; then
    echo "  ✓ VP8 encoder available"
else
    echo "  ✗ VP8 encoder not found"
fi

# Check Python GObject
echo ""
echo "Checking Python GObject..."
if python3 -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst, GstWebRTC" 2>/dev/null; then
    echo "  ✓ Python GObject bindings working"
else
    echo "  ✗ Python GObject bindings not working"
    exit 1
fi

# Check for video devices
echo ""
echo "Checking for video devices..."
if ls /dev/video* > /dev/null 2>&1; then
    echo "  ✓ Video devices found:"
    ls -la /dev/video* | awk '{print "    "$NF}'
else
    echo "  ⚠ No video devices found"
    if [ "$WSL" = true ]; then
        echo ""
        echo "  On WSL, you need to attach USB camera:"
        echo "  1. On Windows (PowerShell as Admin):"
        echo "     winget install --interactive --exact dorssel.usbipd-win"
        echo "     usbipd list"
        echo "     usbipd bind --busid <BUSID>"
        echo "     usbipd attach --wsl --busid <BUSID>"
        echo ""
        echo "  See: https://learn.microsoft.com/en-us/windows/wsl/connect-usb"
    fi
fi

# Check Janus
echo ""
echo "Checking Janus server..."
if curl -s http://localhost:8088/janus > /dev/null 2>&1; then
    echo "  ✓ Janus server is running"
elif command -v janus > /dev/null 2>&1; then
    echo "  ⚠ Janus is installed but not running"
    echo "    Start it with: janus"
else
    echo "  ⚠ Janus not found"
    echo "    Install from: https://github.com/meetecho/janus-gateway"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Make sure Janus server is running: janus"
echo "  2. Test your camera: python3 test_camera.py"
echo "  3. Run the client: python3 janus_webrtc_client.py"
echo ""
echo "For detailed instructions, see: JANUS_SETUP_GUIDE.md"
echo ""
