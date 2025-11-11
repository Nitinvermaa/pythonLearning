# Janus WebRTC Camera Streaming Setup Guide

This guide will help you set up and use the Python GStreamer WebRTC client to stream your camera feed to a Janus WebRTC server.

## Prerequisites

### 1. WSL Ubuntu Setup
Since you're running Ubuntu on WSL, you need to ensure proper camera access:

```bash
# Check if your camera is accessible in WSL
ls -la /dev/video*
```

If no camera devices are found, you need to attach your USB camera to WSL:

#### Attach USB Camera to WSL (Windows 11)
1. Install usbipd on Windows (PowerShell as Administrator):
   ```powershell
   winget install --interactive --exact dorssel.usbipd-win
   ```

2. List USB devices (PowerShell as Administrator):
   ```powershell
   usbipd list
   ```

3. Attach your camera (replace BUSID with your camera's bus ID):
   ```powershell
   usbipd bind --busid <BUSID>
   usbipd attach --wsl --busid <BUSID>
   ```

### 2. Install GStreamer and Dependencies

```bash
# Update package list
sudo apt update

# Install GStreamer with all required plugins
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

# Install Video4Linux utilities
sudo apt install -y v4l-utils

# Install Python GObject bindings
sudo apt install -y python3-gi python3-gi-cairo gir1.2-gtk-3.0

# Install Python development headers
sudo apt install -y python3-dev
```

### 3. Install Python Dependencies

```bash
# Install Python packages
pip install -r requirements.txt
```

### 4. Verify Janus Server is Running

Check if Janus is running on your system:

```bash
# Check if Janus WebSocket is accessible
curl -i http://localhost:8088/janus

# Check WebSocket endpoint (should not give connection refused)
curl -i http://localhost:8188
```

If Janus is not running, start it:

```bash
# Start Janus server
janus

# Or run in verbose mode for debugging
janus -d 6
```

## Testing Your Setup

### Step 1: Test Camera Access

```bash
# Make the test script executable
chmod +x test_camera.py

# Run camera test
python3 test_camera.py
```

This will:
- List available video devices
- Test if GStreamer can access your camera
- Display camera feed in a window (if X11/display is available)

### Step 2: Test GStreamer WebRTC

```bash
# Test basic GStreamer functionality
gst-inspect-1.0 webrtcbin

# Test VP8 encoder
gst-inspect-1.0 vp8enc

# Test Opus encoder
gst-inspect-1.0 opusenc

# Test V4L2 source
gst-inspect-1.0 v4l2src
```

### Step 3: Create Video Room in Janus

You can create a video room using Janus Admin API or use the demo HTML interface:

#### Option A: Using curl (Command Line)

```bash
# Create a video room
curl -X POST http://localhost:8088/janus \
  -H "Content-Type: application/json" \
  -d '{
    "janus": "create",
    "transaction": "create"
  }'

# Note the session_id from response, then attach to videoroom plugin
# Replace SESSION_ID with actual value
curl -X POST http://localhost:8088/janus/SESSION_ID \
  -H "Content-Type: application/json" \
  -d '{
    "janus": "attach",
    "plugin": "janus.plugin.videoroom",
    "transaction": "attach"
  }'

# Note the handle_id, then create room
# Replace SESSION_ID and HANDLE_ID
curl -X POST http://localhost:8088/janus/SESSION_ID/HANDLE_ID \
  -H "Content-Type: application/json" \
  -d '{
    "janus": "message",
    "transaction": "create",
    "body": {
      "request": "create",
      "room": 1234,
      "description": "Python GStreamer Room",
      "publishers": 6
    }
  }'
```

#### Option B: Using Janus Demo (Easier)

1. Open browser and go to: `http://localhost:8088/demos/videoroomtest.html`
2. Click "Start" to create/join a room
3. Note the room ID (default is usually 1234)

## Running the WebRTC Client

### Basic Usage

```bash
# Make the client executable
chmod +x janus_webrtc_client.py

# Run with default settings (localhost:8188, room 1234, /dev/video0)
python3 janus_webrtc_client.py

# Run with custom settings
python3 janus_webrtc_client.py \
  --janus-url ws://localhost:8188 \
  --room-id 1234 \
  --camera /dev/video0 \
  --verbose
```

### Command Line Options

- `--janus-url`: Janus WebSocket URL (default: ws://localhost:8188)
- `--room-id`: Video room ID to join (default: 1234)
- `--camera`: Camera device path (default: /dev/video0)
- `--verbose`: Enable verbose logging for debugging

### Example Commands

```bash
# Use different camera
python3 janus_webrtc_client.py --camera /dev/video2

# Connect to remote Janus server
python3 janus_webrtc_client.py --janus-url ws://192.168.1.100:8188

# Join different room with verbose logging
python3 janus_webrtc_client.py --room-id 5678 --verbose
```

## Configuration File

You can customize settings in `janus_config.json`:

```json
{
  "janus": {
    "websocket_url": "ws://localhost:8188",
    "http_url": "http://localhost:8088/janus"
  },
  "videoroom": {
    "room_id": 1234,
    "publishers": 6,
    "bitrate": 128000,
    "videocodec": "vp8",
    "audiocodec": "opus"
  },
  "camera": {
    "device": "/dev/video0",
    "width": 640,
    "height": 480,
    "framerate": 30
  }
}
```

## Troubleshooting

### Camera Not Found

```bash
# List video devices
v4l2-ctl --list-devices

# Check camera capabilities
v4l2-ctl -d /dev/video0 --all

# Test camera with GStreamer
gst-launch-1.0 v4l2src device=/dev/video0 ! videoconvert ! autovideosink
```

### WSL Camera Issues

If camera doesn't work in WSL:

1. Make sure USB is attached to WSL (see Prerequisites section)
2. Check USB connection:
   ```bash
   lsusb
   ```
3. Install USB video drivers:
   ```bash
   sudo apt install -y linux-modules-extra-$(uname -r)
   ```

### Janus Connection Issues

```bash
# Check if Janus is running
ps aux | grep janus

# Check Janus logs
journalctl -u janus -f

# Test WebSocket connection
wscat -c ws://localhost:8188
```

### GStreamer Errors

```bash
# Check GStreamer version
gst-launch-1.0 --version

# Verify all plugins are installed
gst-inspect-1.0 | grep -E "(webrtc|vp8|opus|v4l2)"

# Enable GStreamer debug logs
export GST_DEBUG=3
python3 janus_webrtc_client.py --verbose
```

### Python ImportError

If you get `ImportError: cannot import name 'GstWebRTC'`:

```bash
# Install GObject introspection
sudo apt install -y python3-gi gir1.2-gstreamer-1.0

# Verify installation
python3 -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst; print('Success!')"
```

## How It Works

### WebRTC Signaling Flow

1. **Client connects to Janus** via WebSocket
2. **Creates session** and gets session_id
3. **Attaches to VideoRoom plugin** and gets handle_id
4. **Joins room** as a publisher
5. **Negotiation**:
   - Client creates SDP offer
   - Sends offer to Janus
   - Receives SDP answer from Janus
   - Sets remote description
6. **ICE Candidates** are exchanged (for NAT traversal)
7. **Media streaming** begins via WebRTC

### GStreamer Pipeline

```
v4l2src (camera) 
  → videoconvert 
  → vp8enc (encode to VP8) 
  → rtpvp8pay (RTP packetization)
  → webrtcbin (WebRTC handling)
  
audiotestsrc (silence) 
  → audioconvert 
  → opusenc 
  → rtpopuspay 
  → webrtcbin
```

## Viewing the Stream

### Option 1: Janus Demo Page
1. Open: `http://localhost:8088/demos/videoroomtest.html`
2. Click "Start" and join the same room ID
3. You should see the stream from the Python client

### Option 2: Custom HTML Client
Create a simple HTML page that subscribes to the stream (see Janus documentation)

## Advanced Configuration

### Changing Video Codec to H.264

Edit `janus_webrtc_client.py` and change the pipeline to:

```python
pipeline_str = f"""
v4l2src device={self.camera_device} ! 
videoconvert ! 
x264enc tune=zerolatency bitrate=1000 ! 
rtph264pay config-interval=1 ! 
application/x-rtp,media=video,encoding-name=H264,payload=96 ! 
webrtcbin name=sendrecv
"""
```

### Adding Real Audio Input

Replace `audiotestsrc` with `alsasrc` or `pulsesrc`:

```python
# For ALSA
alsasrc ! audioconvert ! audioresample ! opusenc ! rtpopuspay ! sendrecv.

# For PulseAudio
pulsesrc ! audioconvert ! audioresample ! opusenc ! rtpopuspay ! sendrecv.
```

### Using TURN Server

For NAT traversal, configure TURN server in the code:

```python
self.webrtcbin.set_property('turn-server', 'turn://user:pass@turnserver.com:3478')
```

## References

- [Janus WebRTC Server](https://github.com/meetecho/janus-gateway)
- [GStreamer WebRTC Documentation](https://gstreamer.freedesktop.org/documentation/webrtc/index.html)
- [WSL USB Device Setup](https://learn.microsoft.com/en-us/windows/wsl/connect-usb)
- [WebRTC Signaling](https://webrtc.org/getting-started/overview)

## Need Help?

Check logs with verbose mode:
```bash
python3 janus_webrtc_client.py --verbose 2>&1 | tee client.log
```

And check Janus logs:
```bash
janus -d 6 2>&1 | tee janus.log
```
