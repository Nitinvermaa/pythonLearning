# Complete Windows PowerShell + WSL Janus Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Windows PowerShell                        │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │   Camera     │         │   Viewer     │                 │
│  │  Publisher   │         │   Client     │                 │
│  │  (GStreamer) │         │  (GStreamer) │                 │
│  └──────┬───────┘         └──────┬───────┘                 │
│         │                        │                          │
│         │ WebRTC/SDP/UDP         │ WebRTC/SDP/UDP           │
└─────────┼────────────────────────┼──────────────────────────┘
          │                        │
          │    HTTP API (8088)     │
          │    WebRTC (UDP)        │
          ▼                        ▼
┌─────────────────────────────────────────────────────────────┐
│              WSL Ubuntu (Janus Server)                      │
│  ┌──────────────────────────────────────────────┐          │
│  │         Janus WebRTC Gateway                 │          │
│  │  - Receives camera feed                      │          │
│  │  - Manages WebRTC sessions                   │          │
│  │  - Distributes via SDP/UDP                  │          │
│  └──────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## Step-by-Step Complete Workflow

### STEP 1: Start Janus in WSL

**WSL Terminal (Ubuntu):**

```bash
# Start Janus server
janus --configs-folder=/etc/janus --debug-level=7 --stderr

# Verify it's running
curl http://localhost:8088/janus
```

**Expected Output:**
```json
{"janus":"success","transaction":"...","data":{"version_string":"..."}}
```

---

### STEP 2: Test Camera in Windows PowerShell

**Windows PowerShell:**

```powershell
# List available cameras
gst-device-monitor-1.0 Video

# Test camera (opens window)
gst-launch-1.0 dshowvideosrc device-index=0 ! `
    videoconvert ! `
    video/x-raw,width=640,height=480,framerate=30/1 ! `
    autovideosink
```

**Expected:** Camera window opens showing video

---

### STEP 3: Stream Camera to Janus (Publisher)

**Windows PowerShell:**

```powershell
# Option A: Using Python Client (Recommended)
python janus_webrtc_client_windows.py `
    --janus-url http://localhost:8088/janus `
    --room-id 1234 `
    --camera-device 0 `
    --width 640 `
    --height 480 `
    --fps 30
```

**What happens:**
1. Connects to Janus (HTTP API)
2. Creates session
3. Attaches to VideoRoom plugin
4. Joins room as publisher
5. GStreamer captures camera
6. Creates SDP offer
7. Sends offer to Janus
8. Receives SDP answer
9. Exchanges ICE candidates (UDP)
10. Streams RTP video (UDP)

**Expected Output:**
```
Created session: 1234567890
Attached to plugin: 9876543210
Joined room 1234
SDP Offer created
Received SDP answer from Janus
Connection state: connected
ICE connection state: connected
Pipeline started, streaming camera feed...
```

---

### STEP 4: Verify Publisher in Room

**Windows PowerShell:**

```powershell
# Create session for API calls
$sessionResponse = Invoke-RestMethod -Uri "http://localhost:8088/janus" `
    -Method Post -ContentType "application/json" `
    -Body '{"janus":"create","transaction":"verify"}'
$sessionId = $sessionResponse.data.id

# Attach plugin
$attachResponse = Invoke-RestMethod -Uri "http://localhost:8088/janus/$sessionId" `
    -Method Post -ContentType "application/json" `
    -Body '{"janus":"attach","plugin":"janus.plugin.videoroom","transaction":"verify2"}'
$handleId = $attachResponse.data.id

# List participants
$body = @{
    janus = "message"
    transaction = "verify3"
    body = @{
        request = "listparticipants"
        room = 1234
    }
} | ConvertTo-Json -Depth 10

$response = Invoke-RestMethod -Uri "http://localhost:8088/janus/$sessionId/$handleId" `
    -Method Post -ContentType "application/json" -Body $body

$response.plugindata.data.participants | ConvertTo-Json
```

**Expected:** Shows publisher with ID and display name

---

### STEP 5: Receive Stream (Viewer)

**Windows PowerShell:**

```powershell
# Option A: Using Python Viewer Client (Recommended)
python janus_viewer_client_windows.py `
    --janus-url http://localhost:8088/janus `
    --room-id 1234

# Option B: Specify feed ID explicitly
python janus_viewer_client_windows.py `
    --janus-url http://localhost:8088/janus `
    --room-id 1234 `
    --feed-id 12345
```

**What happens:**
1. Connects to Janus (HTTP API)
2. Creates session
3. Attaches to VideoRoom plugin
4. Lists participants to find publisher
5. Subscribes to publisher feed
6. Receives SDP offer from Janus
7. Creates SDP answer
8. Sends answer to Janus
9. Exchanges ICE candidates (UDP)
10. Receives RTP video (UDP)
11. Decodes and displays video

**Expected Output:**
```
Created session: 1234567890
Attached to plugin: 9876543210
Found publisher feed ID: 12345
Received SDP offer from Janus
SDP Answer created
SDP answer sent successfully
Connection state: connected
ICE connection state: connected
Viewing active. Press Ctrl+C to stop.
```

**Expected:** Video window opens showing stream from camera

---

## Complete Command Reference

### Windows PowerShell Commands

#### 1. Test Camera
```powershell
gst-launch-1.0 dshowvideosrc device-index=0 ! videoconvert ! autovideosink
```

#### 2. Test Janus Connection
```powershell
Invoke-RestMethod -Uri "http://localhost:8088/janus" `
    -Method Post -ContentType "application/json" `
    -Body '{"janus":"info","transaction":"test"}'
```

#### 3. Start Publisher (Camera → Janus)
```powershell
python janus_webrtc_client_windows.py `
    --janus-url http://localhost:8088/janus `
    --room-id 1234 `
    --camera-device 0
```

#### 4. Start Viewer (Janus → Display)
```powershell
python janus_viewer_client_windows.py `
    --janus-url http://localhost:8088/janus `
    --room-id 1234
```

#### 5. List Participants (PowerShell)
```powershell
$sessionId = "YOUR_SESSION_ID"
$handleId = "YOUR_HANDLE_ID"
$body = @{
    janus = "message"
    transaction = "list"
    body = @{
        request = "listparticipants"
        room = 1234
    }
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "http://localhost:8088/janus/$sessionId/$handleId" `
    -Method Post -ContentType "application/json" -Body $body
```

### WSL Ubuntu Commands

#### 1. Start Janus
```bash
janus --configs-folder=/etc/janus --debug-level=7 --stderr
```

#### 2. Test Janus API
```bash
curl http://localhost:8088/janus
```

#### 3. Create Session (Bash)
```bash
SESSION_ID=$(curl -s -X POST http://localhost:8088/janus \
  -H "Content-Type: application/json" \
  -d '{"janus":"create","transaction":"test"}' | jq -r '.data.id')
echo "Session: $SESSION_ID"
```

---

## Python Code Examples

### Publisher Client Usage

```python
# File: janus_webrtc_client_windows.py
# Usage from PowerShell:
python janus_webrtc_client_windows.py --janus-url http://localhost:8088/janus --room-id 1234

# Or in Python:
from janus_webrtc_client_windows import JanusWebRTCClientWindows
import asyncio

async def main():
    client = JanusWebRTCClientWindows(
        janus_url="http://localhost:8088/janus",
        room_id=1234,
        camera_device=0
    )
    await client.run()

asyncio.run(main())
```

### Viewer Client Usage

```python
# File: janus_viewer_client_windows.py
# Usage from PowerShell:
python janus_viewer_client_windows.py --janus-url http://localhost:8088/janus --room-id 1234

# Or in Python:
from janus_viewer_client_windows import JanusViewerClientWindows
import asyncio

async def main():
    client = JanusViewerClientWindows(
        janus_url="http://localhost:8088/janus",
        room_id=1234
    )
    await client.run()

asyncio.run(main())
```

---

## Data Flow Explanation

### 1. Camera Feed → Janus

```
Windows Camera (dshowvideosrc)
    ↓
GStreamer Pipeline
    ├─ videoconvert
    ├─ videoscale
    ├─ vp8enc (VP8 encoding)
    └─ rtpvp8pay (RTP packaging)
    ↓
webrtcbin
    ├─ Creates SDP Offer
    ├─ Sends to Janus (HTTP POST)
    ├─ Receives SDP Answer
    └─ Exchanges ICE (UDP)
    ↓
RTP Stream (UDP) → Janus Server
```

### 2. Janus → Viewer

```
Janus Server
    ├─ Receives RTP from Publisher
    ├─ Creates SDP Offer for Viewer
    └─ Sends via HTTP API
    ↓
Viewer Client
    ├─ Receives SDP Offer
    ├─ Creates SDP Answer
    ├─ Sends to Janus
    └─ Exchanges ICE (UDP)
    ↓
webrtcbin (receives RTP)
    ├─ rtpvp8depay
    ├─ vp8dec
    └─ videoconvert
    ↓
autovideosink (displays video)
```

### 3. SDP Exchange

```
Publisher:
  GStreamer creates SDP Offer
    → HTTP POST to Janus /janus/{session}/{handle}
    ← HTTP Response with SDP Answer
    → Set remote description
    → Start streaming

Viewer:
  Subscribe to room
    ← HTTP Response with SDP Offer
    → Create SDP Answer
    → HTTP POST to Janus
    ← HTTP Response (success)
    → Start receiving
```

### 4. UDP Traffic (WebRTC)

```
STUN: UDP to stun.l.google.com:19302 (NAT traversal)
ICE: UDP candidates exchanged (port range 10000-20000)
RTP: UDP video data (port range 10000-20000)
DTLS: UDP encryption handshake
```

---

## Network Configuration

### Windows to WSL

- **Windows 11**: Use `localhost` (automatic port forwarding)
- **Windows 10**: May need WSL IP address

```powershell
# Get WSL IP
wsl hostname -I

# Use in commands
--janus-url http://172.x.x.x:8088/janus
```

### Ports Used

- **8088**: Janus HTTP API
- **8188**: Janus WebSocket (if enabled)
- **10000-20000**: WebRTC UDP (dynamic)

### Firewall

```powershell
# Allow WSL through firewall (if needed)
New-NetFirewallRule -DisplayName "WSL" `
    -Direction Inbound `
    -InterfaceAlias "vEthernet (WSL)" `
    -Action Allow
```

---

## Troubleshooting

### Issue: Camera not found

```powershell
# List cameras
gst-device-monitor-1.0 Video

# Try different index
python janus_webrtc_client_windows.py --camera-device 1
```

### Issue: Janus not accessible

```powershell
# Test connectivity
Test-NetConnection -ComputerName localhost -Port 8088

# Check WSL is running
wsl --list --running

# Try WSL IP
wsl hostname -I
```

### Issue: No video in viewer

1. Check publisher is in room (list participants)
2. Check connection states (should be "connected")
3. Check firewall allows UDP
4. Check Janus logs in WSL

### Issue: GStreamer errors

```powershell
# Check plugins
gst-inspect-1.0 webrtcbin
gst-inspect-1.0 dshowvideosrc
gst-inspect-1.0 vp8enc

# Reinstall if missing
# Download from: https://gstreamer.freedesktop.org/download/
```

---

## Quick Start Script

Save as `start_janus_streaming.ps1`:

```powershell
# Quick Start Script

Write-Host "=== Janus Streaming Setup ===" -ForegroundColor Green

# Check Janus
Write-Host "`n1. Checking Janus..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8088/janus" `
        -Method Post -ContentType "application/json" `
        -Body '{"janus":"info","transaction":"test"}'
    Write-Host "✓ Janus is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Start Janus in WSL first: janus --configs-folder=/etc/janus" -ForegroundColor Red
    exit 1
}

# Start Publisher
Write-Host "`n2. Starting Publisher..." -ForegroundColor Yellow
Write-Host "Run in new terminal:"
Write-Host "  python janus_webrtc_client_windows.py --room-id 1234" -ForegroundColor Cyan
Start-Sleep -Seconds 2

# Start Viewer
Write-Host "`n3. Starting Viewer..." -ForegroundColor Yellow
Write-Host "Run in new terminal:"
Write-Host "  python janus_viewer_client_windows.py --room-id 1234" -ForegroundColor Cyan

Write-Host "`n=== Setup Complete ===" -ForegroundColor Green
```

Run:
```powershell
.\start_janus_streaming.ps1
```

---

## Summary

1. **Start Janus** (WSL): `janus --configs-folder=/etc/janus`
2. **Test Camera** (PowerShell): `gst-launch-1.0 dshowvideosrc ! autovideosink`
3. **Start Publisher** (PowerShell): `python janus_webrtc_client_windows.py --room-id 1234`
4. **Start Viewer** (PowerShell): `python janus_viewer_client_windows.py --room-id 1234`

All files are ready to use!
