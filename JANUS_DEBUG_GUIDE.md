# Janus WebRTC Debugging Guide - Step by Step

Complete guide to manually test and debug Janus WebRTC streaming with GStreamer.

## Prerequisites Check

```bash
# 1. Check GStreamer installation
gst-launch-1.0 --version
gst-inspect-1.0 webrtcbin
gst-inspect-1.0 vp8enc
gst-inspect-1.0 v4l2src

# 2. Check camera
v4l2-ctl --list-devices
ls -l /dev/video*

# 3. Check Janus (if installed)
janus --version
# Or check if Janus is running
curl http://localhost:8088/janus
```

---

## Step 1: Test Camera with GStreamer

### 1.1 List Available Cameras

```bash
# List video devices
v4l2-ctl --list-devices

# Check camera capabilities
v4l2-ctl --device=/dev/video0 --list-formats
v4l2-ctl --device=/dev/video0 --list-formats-ext
```

### 1.2 Test Camera Capture (Local Display)

```bash
# Simple test - display camera in window
gst-launch-1.0 v4l2src device=/dev/video0 ! \
    videoconvert ! \
    video/x-raw,width=640,height=480,framerate=30/1 ! \
    autovideosink

# Test with specific format
gst-launch-1.0 v4l2src device=/dev/video0 ! \
    video/x-raw,format=YUY2,width=640,height=480,framerate=30/1 ! \
    videoconvert ! \
    autovideosink
```

### 1.3 Test Camera Encoding Pipeline

```bash
# Test VP8 encoding (what we'll use for WebRTC)
gst-launch-1.0 v4l2src device=/dev/video0 ! \
    videoconvert ! \
    video/x-raw,width=640,height=480,framerate=30/1,format=I420 ! \
    vp8enc target-bitrate=1000000 deadline=1 ! \
    webmmux ! \
    filesink location=test_camera.webm

# Play it back to verify
gst-launch-1.0 playbin uri=file://$(pwd)/test_camera.webm
```

### 1.4 Test RTP Streaming (Local Network)

```bash
# Terminal 1: Send RTP stream
gst-launch-1.0 v4l2src device=/dev/video0 ! \
    videoconvert ! \
    video/x-raw,width=640,height=480,framerate=30/1,format=I420 ! \
    vp8enc target-bitrate=1000000 deadline=1 ! \
    rtpvp8pay ! \
    udpsink host=127.0.0.1 port=5000

# Terminal 2: Receive and display
gst-launch-1.0 udpsrc port=5000 ! \
    application/x-rtp,media=video,clock-rate=90000,encoding-name=VP8 ! \
    rtpvp8depay ! \
    vp8dec ! \
    videoconvert ! \
    autovideosink
```

**Expected Output:**
- Camera window should appear
- Video should be smooth
- No errors in terminal

**Debug if fails:**
```bash
# Check camera permissions
ls -l /dev/video0
# Should show: crw-rw----+ 1 root video

# Add user to video group if needed
sudo usermod -a -G video $USER
# Log out and back in
```

---

## Step 2: Start Janus Server Manually

### 2.1 Check Janus Installation

```bash
# Check if Janus is installed
which janus
janus --version

# Check Janus config location
find /etc /usr/local -name "janus.jcfg" 2>/dev/null
find /etc /usr/local -name "janus.plugin.videoroom.jcfg" 2>/dev/null
```

### 2.2 Start Janus Server

```bash
# Option 1: Start with default config
janus --configs-folder=/etc/janus

# Option 2: Start with custom config (if you have one)
janus --configs-folder=/path/to/janus/configs

# Option 3: Start with debug logging
janus --configs-folder=/etc/janus --debug-level=7 --log-file=/tmp/janus.log

# Option 4: Start in foreground with verbose output
janus --configs-folder=/etc/janus --debug-level=7 --stderr
```

### 2.3 Verify Janus is Running

```bash
# Test HTTP API endpoint
curl http://localhost:8088/janus

# Expected response:
# {"janus":"success","transaction":"...","data":{"version_string":"...","version":...}}

# Test with info request
curl -X POST http://localhost:8088/janus \
  -H "Content-Type: application/json" \
  -d '{"janus":"info","transaction":"test123"}'

# Check Janus processes
ps aux | grep janus

# Check if ports are listening
netstat -tlnp | grep -E '8088|8188|8089|8189'
# Or with ss:
ss -tlnp | grep -E '8088|8188|8089|8189'
```

### 2.4 Janus Configuration Files

Typical locations:
- `/etc/janus/janus.jcfg` - Main config
- `/etc/janus/janus.transport.http.jcfg` - HTTP transport
- `/etc/janus/janus.plugin.videoroom.jcfg` - VideoRoom plugin

**Key settings to check:**
```json
// janus.jcfg
{
    "general": {
        "configs_folder": "/etc/janus",
        "plugins_folder": "/usr/lib/janus/plugins",
        "transports_folder": "/usr/lib/janus/transports"
    },
    "plugins": {
        "disable": "libjanus_voicemail.so,libjanus_recordplay.so"
    }
}

// janus.transport.http.jcfg
{
    "http": {
        "port": 8088,
        "interface": "0.0.0.0"
    }
}

// janus.plugin.videoroom.jcfg
{
    "general": {
        "string_ids": false
    }
}
```

---

## Step 3: Janus API Endpoints - Manual Testing

### 3.1 Create Session

```bash
# Create a Janus session
SESSION_RESPONSE=$(curl -s -X POST http://localhost:8088/janus \
  -H "Content-Type: application/json" \
  -d '{"janus":"create","transaction":"'$(date +%s)'"}')

echo $SESSION_RESPONSE | jq .

# Extract session ID
SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.data.id')
echo "Session ID: $SESSION_ID"
```

**Expected Response:**
```json
{
  "janus": "success",
  "session_id": 1234567890,
  "transaction": "...",
  "data": {
    "id": 1234567890
  }
}
```

### 3.2 Attach to VideoRoom Plugin

```bash
# Attach to VideoRoom plugin
ATTACH_RESPONSE=$(curl -s -X POST "http://localhost:8088/janus/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "janus":"attach",
    "plugin":"janus.plugin.videoroom",
    "transaction":"'$(date +%s)'"
  }')

echo $ATTACH_RESPONSE | jq .

# Extract handle ID
HANDLE_ID=$(echo $ATTACH_RESPONSE | jq -r '.data.id')
echo "Handle ID: $HANDLE_ID"
```

**Expected Response:**
```json
{
  "janus": "success",
  "session_id": 1234567890,
  "transaction": "...",
  "data": {
    "id": 9876543210
  }
}
```

### 3.3 Create/Join Room

```bash
# Create a room (as publisher)
JOIN_RESPONSE=$(curl -s -X POST "http://localhost:8088/janus/$SESSION_ID/$HANDLE_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "janus":"message",
    "transaction":"'$(date +%s)'",
    "body":{
      "request":"join",
      "ptype":"publisher",
      "room":1234,
      "display":"Test Publisher"
    }
  }')

echo $JOIN_RESPONSE | jq .
```

**Expected Response:**
```json
{
  "janus": "success",
  "session_id": 1234567890,
  "sender": 9876543210,
  "transaction": "...",
  "plugindata": {
    "plugin": "janus.plugin.videoroom",
    "data": {
      "videoroom": "joined",
      "room": 1234,
      "id": 12345
    }
  }
}
```

### 3.4 List Rooms

```bash
# List all rooms
curl -s -X POST "http://localhost:8088/janus/$SESSION_ID/$HANDLE_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "janus":"message",
    "transaction":"'$(date +%s)'",
    "body":{"request":"list"}
  }' | jq .
```

### 3.5 List Participants in Room

```bash
# List participants in room 1234
curl -s -X POST "http://localhost:8088/janus/$SESSION_ID/$HANDLE_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "janus":"message",
    "transaction":"'$(date +%s)'",
    "body":{
      "request":"listparticipants",
      "room":1234
    }
  }' | jq .
```

---

## Step 4: Feed Camera Stream to Janus (GStreamer → Janus)

### 4.1 Understanding the Flow

```
Camera → GStreamer → WebRTC Offer (SDP) → Janus API → Janus Answer (SDP) → GStreamer → WebRTC Connection (UDP)
```

### 4.2 Manual SDP Exchange Process

#### Step 4.2.1: Generate SDP Offer from GStreamer

Create a script to generate SDP offer:

```bash
# Save as: generate_sdp_offer.sh
cat > /tmp/generate_sdp_offer.sh << 'EOF'
#!/bin/bash
gst-launch-1.0 v4l2src device=/dev/video0 ! \
    videoconvert ! \
    video/x-raw,width=640,height=480,framerate=30/1,format=I420 ! \
    vp8enc target-bitrate=1000000 deadline=1 ! \
    rtpvp8pay ! \
    webrtcbin name=webrtcbin stun-server=stun://stun.l.google.com:19302 \
    webrtcbin. ! fakesink
EOF

chmod +x /tmp/generate_sdp_offer.sh
```

**Better: Use Python to get SDP offer programmatically** (see next section)

### 4.3 Using Python Client (Automated)

The `janus_webrtc_client.py` handles this automatically, but here's what happens:

1. **GStreamer creates WebRTC offer** (SDP)
2. **Send offer to Janus** via HTTP POST
3. **Janus returns answer** (SDP)
4. **Set answer in GStreamer**
5. **ICE candidates exchanged** (UDP)
6. **Media flows** (UDP RTP)

### 4.4 Manual Testing with Python Script

```bash
# Run the client (it does everything automatically)
python3 janus_webrtc_client.py \
    --janus-url http://localhost:8088/janus \
    --room-id 1234 \
    --camera /dev/video0 \
    --width 640 \
    --height 480 \
    --fps 30

# Enable debug to see SDP
python3 -c "
import logging
logging.basicConfig(level=logging.DEBUG)
exec(open('janus_webrtc_client.py').read())
" --janus-url http://localhost:8088/janus --room-id 1234
```

### 4.5 Verify Stream is Active

```bash
# In another terminal, check room participants
SESSION_ID=1234567890  # From step 3.1
HANDLE_ID=9876543210   # From step 3.2

curl -s -X POST "http://localhost:8088/janus/$SESSION_ID/$HANDLE_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "janus":"message",
    "transaction":"'$(date +%s)'",
    "body":{
      "request":"listparticipants",
      "room":1234
    }
  }' | jq '.plugindata.data.participants'
```

**Expected:** Should show your publisher with ID and display name.

---

## Step 5: View Stream from Another Client (Using SDP)

### 5.1 Subscribe to Room (Get SDP Offer from Janus)

```bash
# Create new session for viewer
VIEWER_SESSION=$(curl -s -X POST http://localhost:8088/janus \
  -H "Content-Type: application/json" \
  -d '{"janus":"create","transaction":"viewer1"}' | jq -r '.data.id')

# Attach to plugin
VIEWER_HANDLE=$(curl -s -X POST "http://localhost:8088/janus/$VIEWER_SESSION" \
  -H "Content-Type: application/json" \
  -d '{
    "janus":"attach",
    "plugin":"janus.plugin.videoroom",
    "transaction":"viewer2"
  }' | jq -r '.data.id')

# Join as subscriber (this will return SDP offer from Janus)
SUBSCRIBE_RESPONSE=$(curl -s -X POST "http://localhost:8088/janus/$VIEWER_SESSION/$VIEWER_HANDLE" \
  -H "Content-Type: application/json" \
  -d '{
    "janus":"message",
    "transaction":"viewer3",
    "body":{
      "request":"join",
      "ptype":"subscriber",
      "room":1234,
      "feed":12345
    }
  }')

echo $SUBSCRIBE_RESPONSE | jq .

# Extract SDP offer
SDP_OFFER=$(echo $SUBSCRIBE_RESPONSE | jq -r '.jsep.sdp')
echo "SDP Offer from Janus:"
echo "$SDP_OFFER"
```

**Note:** You need the `feed` ID from the publisher. Get it from `listparticipants`.

### 5.2 Create SDP Answer and Send to Janus

```bash
# Save SDP offer to file
echo "$SDP_OFFER" > /tmp/janus_sdp_offer.txt

# Create SDP answer using GStreamer (this is complex, better use Python)
# For now, we'll use a GStreamer pipeline that handles this
```

### 5.3 GStreamer Client to View Stream

Create a viewer script:

```bash
# Save as: view_janus_stream.sh
cat > /tmp/view_janus_stream.sh << 'EOF'
#!/bin/bash

# This is a simplified example
# In practice, you need to:
# 1. Get SDP offer from Janus (step 5.1)
# 2. Create SDP answer with GStreamer
# 3. Send answer back to Janus
# 4. Handle ICE candidates

# For a complete solution, use the Python client or Janus JavaScript client
EOF
```

**Better approach:** Use the Python client as a viewer, or use Janus's built-in HTML client.

### 5.4 Using Janus HTML Client (Easiest)

```bash
# Janus comes with example HTML clients
# Find them:
find /usr -name "videoroomtest.html" 2>/dev/null
find /usr -name "videoroom.html" 2>/dev/null

# Or download from Janus examples:
# https://github.com/meetecho/janus-gateway/tree/master/html

# Serve the HTML file
cd /path/to/janus/html
python3 -m http.server 8080

# Open browser: http://localhost:8080/videoroomtest.html
# Enter room ID: 1234
# Click "Watch" to subscribe
```

### 5.5 Python Viewer Client

Create a viewer client (simplified):

```python
# This would be similar to the publisher but as subscriber
# The main difference is:
# - Join as "subscriber" instead of "publisher"
# - Receive SDP offer from Janus (not send)
# - Create SDP answer
# - Send answer back to Janus
```

---

## Step 6: Complete Debug Workflow

### 6.1 Terminal 1: Start Janus

```bash
# Start Janus with verbose logging
janus --configs-folder=/etc/janus --debug-level=7 --stderr 2>&1 | tee /tmp/janus.log
```

### 6.2 Terminal 2: Verify Janus

```bash
# Test Janus API
curl http://localhost:8088/janus

# Create session and room
SESSION_ID=$(curl -s -X POST http://localhost:8088/janus \
  -H "Content-Type: application/json" \
  -d '{"janus":"create","transaction":"test"}' | jq -r '.data.id')

echo "Session ID: $SESSION_ID"
```

### 6.3 Terminal 3: Start Publisher (Camera Stream)

```bash
# Run Python client
python3 janus_webrtc_client.py \
    --janus-url http://localhost:8088/janus \
    --room-id 1234 \
    --camera /dev/video0

# Watch for:
# - "Created session: ..."
# - "Attached to plugin: ..."
# - "Joined room 1234"
# - "SDP Offer created"
# - "Received SDP answer from Janus"
# - "Connection state: connected"
# - "ICE connection state: connected"
```

### 6.4 Terminal 4: Verify Publisher in Room

```bash
# List participants
curl -s -X POST "http://localhost:8088/janus/$SESSION_ID/$HANDLE_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "janus":"message",
    "transaction":"list",
    "body":{"request":"listparticipants","room":1234}
  }' | jq '.plugindata.data.participants'
```

### 6.5 Terminal 5: Start Viewer (Browser or Another Client)

**Option A: Browser**
```bash
# Open Janus HTML client in browser
# http://localhost:8080/videoroomtest.html
# Join room 1234 as viewer
```

**Option B: Another Python Client (as subscriber)**
```bash
# Would need a subscriber version of the client
# For now, use browser or Janus admin UI
```

---

## Step 7: Debugging Common Issues

### 7.1 Camera Not Found

```bash
# Check devices
ls -l /dev/video*

# Check permissions
groups | grep video

# Test with v4l2
v4l2-ctl --device=/dev/video0 --all

# Try different device
python3 janus_webrtc_client.py --camera /dev/video1
```

### 7.2 Janus Connection Failed

```bash
# Check if Janus is running
ps aux | grep janus

# Check port
netstat -tlnp | grep 8088

# Test API
curl -v http://localhost:8088/janus

# Check Janus logs
tail -f /tmp/janus.log
# Or
journalctl -u janus -f  # if running as service
```

### 7.3 SDP Exchange Issues

```bash
# Enable debug logging in Python client
python3 -c "
import logging
logging.basicConfig(level=logging.DEBUG)
exec(open('janus_webrtc_client.py').read())
" --janus-url http://localhost:8088/janus

# Check SDP content
# Look for "SDP Offer created" and "SDP Answer from Janus" in logs
```

### 7.4 ICE Connection Failed

```bash
# Check STUN server
curl -v stun://stun.l.google.com:19302

# Check firewall
sudo ufw status
# May need to allow UDP ports

# Check NAT/firewall rules
# WebRTC uses UDP, may need TURN server for strict NATs
```

### 7.5 No Video in Viewer

```bash
# Verify publisher is in room
curl ... | jq '.plugindata.data.participants'

# Check Janus logs for errors
tail -f /tmp/janus.log | grep -i error

# Verify WebRTC connection state
# Should see "ICE connection state: connected" in publisher logs
```

---

## Step 8: Network Debugging (UDP/RTP)

### 8.1 Monitor UDP Traffic

```bash
# Monitor UDP traffic on WebRTC ports (typically 10000-20000)
sudo tcpdump -i any -n udp portrange 10000-20000 -v

# Or with Wireshark
sudo wireshark -i any -f "udp portrange 10000-20000"
```

### 8.2 Check RTP Packets

```bash
# Monitor RTP specifically
sudo tcpdump -i any -n "udp and portrange 10000-20000" -A

# Check for VP8 RTP packets
sudo tcpdump -i any -n "udp and portrange 10000-20000" -x | grep -i vp8
```

### 8.3 Verify Ports are Open

```bash
# Check listening ports
ss -tulnp | grep -E '10000|20000|8088'

# Test port connectivity
nc -u -v localhost 10000
```

---

## Step 9: Complete Test Script

Save this as `test_janus_complete.sh`:

```bash
#!/bin/bash
set -e

echo "=== Janus Complete Test ==="

# 1. Check Janus
echo "1. Checking Janus..."
curl -s http://localhost:8088/janus > /dev/null || {
    echo "ERROR: Janus not running!"
    exit 1
}
echo "✓ Janus is running"

# 2. Check camera
echo "2. Checking camera..."
[ -e /dev/video0 ] || {
    echo "ERROR: Camera not found!"
    exit 1
}
echo "✓ Camera found"

# 3. Create session
echo "3. Creating session..."
SESSION=$(curl -s -X POST http://localhost:8088/janus \
  -H "Content-Type: application/json" \
  -d '{"janus":"create","transaction":"test"}' | jq -r '.data.id')
echo "✓ Session created: $SESSION"

# 4. Attach plugin
echo "4. Attaching plugin..."
HANDLE=$(curl -s -X POST "http://localhost:8088/janus/$SESSION" \
  -H "Content-Type: application/json" \
  -d '{"janus":"attach","plugin":"janus.plugin.videoroom","transaction":"test2"}' \
  | jq -r '.data.id')
echo "✓ Plugin attached: $HANDLE"

# 5. List rooms
echo "5. Listing rooms..."
curl -s -X POST "http://localhost:8088/janus/$SESSION/$HANDLE" \
  -H "Content-Type: application/json" \
  -d '{"janus":"message","transaction":"test3","body":{"request":"list"}}' \
  | jq '.plugindata.data.list'

echo ""
echo "=== Test Complete ==="
echo "Session ID: $SESSION"
echo "Handle ID: $HANDLE"
echo ""
echo "Now run: python3 janus_webrtc_client.py --room-id 1234"
```

Make it executable:
```bash
chmod +x test_janus_complete.sh
./test_janus_complete.sh
```

---

## Summary: Complete Flow

```
1. Start Janus Server
   → janus --configs-folder=/etc/janus

2. Verify Janus
   → curl http://localhost:8088/janus

3. Test Camera
   → gst-launch-1.0 v4l2src device=/dev/video0 ! autovideosink

4. Start Publisher
   → python3 janus_webrtc_client.py --room-id 1234

5. Verify Publisher
   → curl ... listparticipants

6. Start Viewer
   → Browser: http://localhost:8080/videoroomtest.html
   → Or: Another WebRTC client

7. Debug Issues
   → Check logs, network, SDP, ICE
```

---

## Quick Reference: Janus API Endpoints

```
POST /janus                          → Create session
POST /janus/{session_id}              → Attach plugin, send message
POST /janus/{session_id}/{handle_id} → Send message to plugin
GET  /janus/{session_id}/{handle_id} → Long poll for events
```

All endpoints use JSON with:
- `janus`: Command type ("create", "attach", "message", "trickle")
- `transaction`: Unique ID
- `jsep`: SDP data (when present)
- `body`: Plugin-specific data
