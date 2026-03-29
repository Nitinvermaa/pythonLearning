#!/bin/bash
# GStreamer Test Commands for Camera and WebRTC
# Run these commands step by step to debug camera streaming

CAMERA_DEVICE="${CAMERA_DEVICE:-/dev/video0}"
WIDTH="${WIDTH:-640}"
HEIGHT="${HEIGHT:-480}"
FPS="${FPS:-30}"

echo "=========================================="
echo "GStreamer Camera Test Commands"
echo "=========================================="
echo "Camera: $CAMERA_DEVICE"
echo "Resolution: ${WIDTH}x${HEIGHT}@${FPS}fps"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test 1: Check camera device
echo -e "${YELLOW}Test 1: Checking camera device...${NC}"
if [ -e "$CAMERA_DEVICE" ]; then
    echo -e "${GREEN}✓ Camera device exists: $CAMERA_DEVICE${NC}"
    ls -l "$CAMERA_DEVICE"
else
    echo -e "${RED}✗ Camera device not found: $CAMERA_DEVICE${NC}"
    echo "Available devices:"
    ls -l /dev/video* 2>/dev/null || echo "No video devices found"
    exit 1
fi
echo ""

# Test 2: Check camera capabilities
echo -e "${YELLOW}Test 2: Checking camera capabilities...${NC}"
if command -v v4l2-ctl &> /dev/null; then
    echo "Supported formats:"
    v4l2-ctl --device="$CAMERA_DEVICE" --list-formats 2>/dev/null || echo "Could not list formats"
    echo ""
    echo "Supported resolutions:"
    v4l2-ctl --device="$CAMERA_DEVICE" --list-formats-ext 2>/dev/null | head -20 || echo "Could not list resolutions"
else
    echo "v4l2-ctl not installed. Install with: sudo apt-get install v4l-utils"
fi
echo ""

# Test 3: Simple camera test (display)
echo -e "${YELLOW}Test 3: Testing camera capture (will open window)...${NC}"
echo "Command: gst-launch-1.0 v4l2src device=$CAMERA_DEVICE ! videoconvert ! autovideosink"
echo "Press Ctrl+C to stop"
read -p "Press Enter to run test 3, or Ctrl+C to skip..."
gst-launch-1.0 v4l2src device="$CAMERA_DEVICE" ! \
    videoconvert ! \
    autovideosink 2>&1 | head -20
echo ""

# Test 4: Test with specific format
echo -e "${YELLOW}Test 4: Testing with specific format (I420)...${NC}"
echo "Command: gst-launch-1.0 v4l2src ! videoconvert ! video/x-raw,format=I420 ! autovideosink"
read -p "Press Enter to run test 4, or Ctrl+C to skip..."
gst-launch-1.0 v4l2src device="$CAMERA_DEVICE" ! \
    videoconvert ! \
    video/x-raw,format=I420,width=$WIDTH,height=$HEIGHT,framerate=$FPS/1 ! \
    autovideosink 2>&1 | head -20
echo ""

# Test 5: Test VP8 encoding
echo -e "${YELLOW}Test 5: Testing VP8 encoding (saves to file)...${NC}"
OUTPUT_FILE="/tmp/test_vp8_$(date +%s).webm"
echo "Output file: $OUTPUT_FILE"
echo "Command: gst-launch-1.0 v4l2src ! videoconvert ! vp8enc ! webmmux ! filesink"
read -p "Press Enter to run test 5 (5 seconds), or Ctrl+C to skip..."
timeout 5 gst-launch-1.0 v4l2src device="$CAMERA_DEVICE" ! \
    videoconvert ! \
    video/x-raw,format=I420,width=$WIDTH,height=$HEIGHT,framerate=$FPS/1 ! \
    vp8enc target-bitrate=1000000 deadline=1 ! \
    webmmux ! \
    filesink location="$OUTPUT_FILE" 2>&1

if [ -f "$OUTPUT_FILE" ] && [ -s "$OUTPUT_FILE" ]; then
    echo -e "${GREEN}✓ VP8 encoding test passed${NC}"
    echo "File size: $(du -h "$OUTPUT_FILE" | cut -f1)"
    echo "Play with: gst-launch-1.0 playbin uri=file://$OUTPUT_FILE"
else
    echo -e "${RED}✗ VP8 encoding test failed${NC}"
fi
echo ""

# Test 6: Test RTP streaming (local)
echo -e "${YELLOW}Test 6: Testing RTP streaming (requires 2 terminals)...${NC}"
echo "Terminal 1 (sender):"
echo "  gst-launch-1.0 v4l2src device=$CAMERA_DEVICE ! \\"
echo "    videoconvert ! \\"
echo "    video/x-raw,format=I420,width=$WIDTH,height=$HEIGHT,framerate=$FPS/1 ! \\"
echo "    vp8enc ! rtpvp8pay ! udpsink host=127.0.0.1 port=5000"
echo ""
echo "Terminal 2 (receiver):"
echo "  gst-launch-1.0 udpsrc port=5000 ! \\"
echo "    application/x-rtp,media=video,clock-rate=90000,encoding-name=VP8 ! \\"
echo "    rtpvp8depay ! vp8dec ! videoconvert ! autovideosink"
echo ""
read -p "Press Enter to start sender (test 6), or Ctrl+C to skip..."
echo "Starting sender on port 5000 (Ctrl+C to stop)..."
gst-launch-1.0 v4l2src device="$CAMERA_DEVICE" ! \
    videoconvert ! \
    video/x-raw,format=I420,width=$WIDTH,height=$HEIGHT,framerate=$FPS/1 ! \
    vp8enc target-bitrate=1000000 deadline=1 ! \
    rtpvp8pay ! \
    udpsink host=127.0.0.1 port=5000 2>&1
echo ""

# Test 7: Check GStreamer plugins
echo -e "${YELLOW}Test 7: Checking required GStreamer plugins...${NC}"
REQUIRED_PLUGINS=("v4l2src" "videoconvert" "vp8enc" "webrtcbin" "rtpvp8pay" "udpsink")

for plugin in "${REQUIRED_PLUGINS[@]}"; do
    if gst-inspect-1.0 "$plugin" &> /dev/null; then
        echo -e "${GREEN}✓ $plugin${NC}"
    else
        echo -e "${RED}✗ $plugin NOT FOUND${NC}"
    fi
done
echo ""

# Test 8: WebRTC bin test (minimal)
echo -e "${YELLOW}Test 8: Testing WebRTC bin (minimal pipeline)...${NC}"
echo "This creates a webrtcbin but doesn't connect (just tests it exists)"
if gst-inspect-1.0 webrtcbin &> /dev/null; then
    echo -e "${GREEN}✓ webrtcbin plugin available${NC}"
    echo "WebRTC bin properties:"
    gst-inspect-1.0 webrtcbin | grep -A 5 "Properties"
else
    echo -e "${RED}✗ webrtcbin plugin NOT FOUND${NC}"
    echo "Install with: sudo apt-get install gstreamer1.0-plugins-bad"
fi
echo ""

echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "Camera device: $CAMERA_DEVICE"
echo "If all tests passed, you can proceed to:"
echo "  python3 janus_webrtc_client.py --camera $CAMERA_DEVICE"
echo ""
