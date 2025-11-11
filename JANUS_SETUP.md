# Janus WebRTC Camera Streaming Setup Guide

This guide explains how to set up and use the Python client to stream your camera feed to a Janus WebRTC server.

## Prerequisites

### 1. Install GStreamer and Python Bindings

On Ubuntu/WSL:

```bash
# Update package list
sudo apt-get update

# Install GStreamer core libraries
sudo apt-get install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev

# Install GStreamer WebRTC plugin
sudo apt-get install -y \
    gstreamer1.0-plugins-bad \
    libgstreamer-plugins-bad1.0-dev

# Install Python GObject bindings
sudo apt-get install -y \
    python3-gi \
    python3-gi-cairo \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-plugins-base-1.0 \
    gir1.2-gst-plugins-bad-1.0

# Install Python dependencies
pip install aiohttp PyGObject
```

### 2. Verify Camera Access

Check if your camera is accessible:

```bash
# List video devices
ls -l /dev/video*

# Test camera with v4l2
v4l2-ctl --list-devices

# Test with GStreamer
gst-launch-1.0 v4l2src device=/dev/video0 ! videoconvert ! autovideosink
```

### 3. Janus Server Configuration

Ensure your Janus server is running and accessible. The default configuration expects:
- Janus HTTP API: `http://localhost:8088/janus`
- VideoRoom plugin enabled
- Room ID: `1234` (or specify your own)

## Usage

### Basic Usage

```bash
python3 janus_webrtc_client.py
```

### Advanced Usage with Options

```bash
# Custom Janus server and room
python3 janus_webrtc_client.py \
    --janus-url http://your-janus-server:8088/janus \
    --room-id 5678 \
    --camera /dev/video0 \
    --width 1280 \
    --height 720 \
    --fps 30
```

### Command Line Arguments

- `--janus-url`: Janus server URL (default: `http://localhost:8088/janus`)
- `--room-id`: VideoRoom room ID (default: `1234`)
- `--camera`: Camera device path (default: `/dev/video0`)
- `--width`: Video width in pixels (default: `640`)
- `--height`: Video height in pixels (default: `480`)
- `--fps`: Video framerate (default: `30`)

## How It Works

1. **Session Creation**: Creates a session with Janus server
2. **Plugin Attachment**: Attaches to the VideoRoom plugin
3. **Room Join**: Joins the specified room as a publisher
4. **GStreamer Pipeline**: Creates a pipeline that:
   - Captures video from camera (`v4l2src`)
   - Converts and scales video
   - Encodes with VP8
   - Packages as RTP
   - Sends via WebRTC
5. **SDP Exchange**: 
   - Creates WebRTC offer
   - Sends to Janus
   - Receives answer
   - Sets remote description
6. **Streaming**: Camera feed is streamed to Janus

## Pipeline Structure

```
v4l2src → videoconvert → videoscale → videorate → capsfilter → 
vp8enc → rtpvp8pay → webrtcbin → Janus Server
```

## Troubleshooting

### Camera Not Found

```bash
# Check available cameras
v4l2-ctl --list-devices

# Try different device
python3 janus_webrtc_client.py --camera /dev/video1
```

### GStreamer Errors

```bash
# Check GStreamer plugins
gst-inspect-1.0 webrtcbin
gst-inspect-1.0 vp8enc
gst-inspect-1.0 v4l2src

# Test pipeline manually
gst-launch-1.0 v4l2src device=/dev/video0 ! \
    videoconvert ! \
    video/x-raw,width=640,height=480,framerate=30/1,format=I420 ! \
    vp8enc ! \
    webmmux ! \
    filesink location=test.webm
```

### Janus Connection Issues

- Verify Janus is running: `curl http://localhost:8088/janus`
- Check firewall settings
- Verify VideoRoom plugin is enabled in Janus config
- Check Janus logs for errors

### Permission Issues

```bash
# Add user to video group (if needed)
sudo usermod -a -G video $USER
# Log out and back in for changes to take effect
```

## Testing the Stream

Once streaming, you can:

1. **View in Janus Admin UI**: Access Janus admin interface to see the stream
2. **Connect a Viewer**: Use another client to join the same room as a viewer
3. **Browser Viewer**: Use Janus JavaScript client to view in a browser

## Example: Complete Test

```bash
# Terminal 1: Start Janus (if not already running)
# Terminal 2: Start the Python client
python3 janus_webrtc_client.py --room-id 1234

# Terminal 3: View the stream (using Janus example HTML client)
# Or use another WebRTC client to join room 1234 as a viewer
```

## Notes

- The client uses VP8 encoding for video
- Audio is disabled by default (can be added if needed)
- STUN server is set to Google's public STUN server
- For production, consider using TURN server for NAT traversal
- Adjust bitrate in code if needed (currently set to 1 Mbps)
