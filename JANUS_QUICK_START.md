# Janus WebRTC Camera Streaming - Quick Start

## Quick Setup (Ubuntu/WSL)

```bash
# 1. Install GStreamer and dependencies
sudo apt-get update
sudo apt-get install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-plugins-base-1.0 \
    gir1.2-gst-plugins-bad-1.0 \
    v4l-utils

# 2. Install Python packages
pip install aiohttp PyGObject

# 3. Test your setup
python3 test_janus_setup.py

# 4. Start streaming
python3 janus_webrtc_client.py
```

## Basic Usage

```bash
# Default settings (localhost:8088, room 1234, /dev/video0)
python3 janus_webrtc_client.py

# Custom settings
python3 janus_webrtc_client.py \
    --janus-url http://your-server:8088/janus \
    --room-id 5678 \
    --camera /dev/video0 \
    --width 1280 \
    --height 720 \
    --fps 30
```

## What It Does

1. **Connects to Janus**: Creates a session and attaches to VideoRoom plugin
2. **Joins Room**: Joins the specified room as a publisher
3. **Captures Camera**: Uses GStreamer to capture from your camera
4. **Encodes Video**: Encodes with VP8 codec
5. **WebRTC Streaming**: Streams via WebRTC using SDP offer/answer exchange
6. **ICE Handling**: Handles ICE candidates for NAT traversal

## Troubleshooting

### Camera not found?
```bash
# List cameras
v4l2-ctl --list-devices

# Try different device
python3 janus_webrtc_client.py --camera /dev/video1
```

### GStreamer errors?
```bash
# Check plugins
gst-inspect-1.0 webrtcbin
gst-inspect-1.0 vp8enc
```

### Janus connection failed?
- Verify Janus is running: `curl http://localhost:8088/janus`
- Check firewall settings
- Verify VideoRoom plugin is enabled

## Files

- `janus_webrtc_client.py` - Main streaming client
- `test_janus_setup.py` - Setup verification script
- `JANUS_SETUP.md` - Detailed setup guide

## Next Steps

1. Run the test script to verify setup
2. Start your Janus server
3. Run the client to start streaming
4. View the stream using Janus admin UI or another WebRTC client
