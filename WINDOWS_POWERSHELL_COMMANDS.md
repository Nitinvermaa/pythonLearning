# Windows PowerShell Commands for Janus Streaming

Complete command reference for Windows PowerShell to work with Janus in WSL.

## Prerequisites

### Install GStreamer on Windows

1. Download: https://gstreamer.freedesktop.org/download/
2. Install: `gstreamer-1.0-msvc-x86_64-1.x.x.msi`
3. Add to PATH (PowerShell):
```powershell
$env:Path += ";C:\gstreamer\1.0\msvc_x86_64\bin"
[Environment]::SetEnvironmentVariable("Path", $env:Path, [EnvironmentVariableTarget]::User)
```

### Verify Installation

```powershell
gst-launch-1.0 --version
gst-inspect-1.0 dshowvideosrc
gst-device-monitor-1.0 Video
```

---

## Step 1: Test Camera in Windows

### List Available Cameras

```powershell
# List DirectShow video sources
gst-device-monitor-1.0 Video

# Or check camera index
gst-inspect-1.0 dshowvideosrc
```

### Test Camera Capture

```powershell
# Test camera (device index 0)
gst-launch-1.0 dshowvideosrc device-index=0 ! `
    videoconvert ! `
    video/x-raw,width=640,height=480,framerate=30/1 ! `
    autovideosink

# Test with specific format
gst-launch-1.0 dshowvideosrc device-index=0 ! `
    videoconvert ! `
    video/x-raw,format=I420,width=640,height=480,framerate=30/1 ! `
    autovideosink
```

### Test Camera Encoding

```powershell
# Test VP8 encoding
gst-launch-1.0 dshowvideosrc device-index=0 ! `
    videoconvert ! `
    video/x-raw,format=I420,width=640,height=480,framerate=30/1 ! `
    vp8enc target-bitrate=1000000 deadline=1 ! `
    webmmux ! `
    filesink location=test_camera.webm
```

---

## Step 2: Test Janus Connection from Windows

### Get WSL IP Address

```powershell
# Get WSL IP
wsl hostname -I

# Or use localhost (Windows 11)
$janusUrl = "http://localhost:8088/janus"
```

### Test Janus API

```powershell
# Test Janus is running
$janusUrl = "http://localhost:8088/janus"
Invoke-RestMethod -Uri $janusUrl -Method Post -ContentType "application/json" -Body '{"janus":"info","transaction":"test"}'

# Create session
$response = Invoke-RestMethod -Uri $janusUrl -Method Post -ContentType "application/json" -Body '{"janus":"create","transaction":"test123"}'
$sessionId = $response.data.id
Write-Host "Session ID: $sessionId"
```

---

## Step 3: Stream Camera to Janus (Python Client)

### Using Python Publisher Client

```powershell
# Run publisher client
python janus_webrtc_client_windows.py `
    --janus-url http://localhost:8088/janus `
    --room-id 1234 `
    --camera-device 0 `
    --width 640 `
    --height 480 `
    --fps 30
```

### Verify Publisher is Active

```powershell
# Get session and handle IDs first, then:
$sessionId = "1234567890"  # Replace with actual
$handleId = "9876543210"   # Replace with actual
$janusUrl = "http://localhost:8088/janus"

$body = @{
    janus = "message"
    transaction = "check"
    body = @{
        request = "listparticipants"
        room = 1234
    }
} | ConvertTo-Json -Depth 10

$response = Invoke-RestMethod -Uri "$janusUrl/$sessionId/$handleId" `
    -Method Post -ContentType "application/json" -Body $body

$response.plugindata.data.participants | ConvertTo-Json
```

---

## Step 4: Receive Stream in Windows (Python Viewer)

### Using Python Viewer Client

```powershell
# Run viewer client (auto-detects publisher)
python janus_viewer_client_windows.py `
    --janus-url http://localhost:8088/janus `
    --room-id 1234

# Or specify feed ID
python janus_viewer_client_windows.py `
    --janus-url http://localhost:8088/janus `
    --room-id 1234 `
    --feed-id 12345
```

---

## Step 5: GStreamer Command to Receive Stream (Manual)

### Note: Full WebRTC requires SDP exchange

For a complete GStreamer command-line solution, you need to:
1. Get SDP offer from Janus (via API)
2. Create SDP answer with GStreamer
3. Send answer back to Janus
4. Handle ICE candidates

This is complex, so use the Python client instead. However, here's a simplified example:

### Get SDP from Janus (PowerShell)

```powershell
# Create session
$sessionResponse = Invoke-RestMethod -Uri "http://localhost:8088/janus" `
    -Method Post -ContentType "application/json" `
    -Body '{"janus":"create","transaction":"test"}'
$sessionId = $sessionResponse.data.id

# Attach plugin
$attachResponse = Invoke-RestMethod -Uri "http://localhost:8088/janus/$sessionId" `
    -Method Post -ContentType "application/json" `
    -Body '{"janus":"attach","plugin":"janus.plugin.videoroom","transaction":"test2"}'
$handleId = $attachResponse.data.id

# Subscribe to room (get SDP offer)
$subscribeBody = @{
    janus = "message"
    transaction = "test3"
    body = @{
        request = "join"
        ptype = "subscriber"
        room = 1234
        feed = 12345  # Publisher feed ID
    }
} | ConvertTo-Json -Depth 10

$subscribeResponse = Invoke-RestMethod `
    -Uri "http://localhost:8088/janus/$sessionId/$handleId" `
    -Method Post -ContentType "application/json" -Body $subscribeBody

# Extract SDP offer
$sdpOffer = $subscribeResponse.jsep.sdp
$sdpOffer | Out-File -FilePath "janus_sdp_offer.txt" -Encoding utf8
Write-Host "SDP Offer saved to janus_sdp_offer.txt"
```

### Use SDP with GStreamer (Complex - Use Python Instead)

The SDP needs to be processed by a WebRTC client. For command-line, use the Python client.

---

## Complete Workflow Script

Save as `janus_windows_workflow.ps1`:

```powershell
# Janus Windows Workflow Script

$janusUrl = "http://localhost:8088/janus"
$roomId = 1234

Write-Host "=== Janus Windows Workflow ===" -ForegroundColor Green

# Step 1: Test Janus
Write-Host "`n1. Testing Janus connection..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri $janusUrl -Method Post `
        -ContentType "application/json" -Body '{"janus":"info","transaction":"test"}'
    Write-Host "✓ Janus is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Janus not accessible: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Test camera
Write-Host "`n2. Testing camera..." -ForegroundColor Yellow
Write-Host "Run: gst-launch-1.0 dshowvideosrc device-index=0 ! autovideosink"
$testCamera = Read-Host "Did camera test work? (y/n)"
if ($testCamera -ne "y") {
    Write-Host "Fix camera issues first" -ForegroundColor Red
    exit 1
}

# Step 3: Start publisher
Write-Host "`n3. Starting publisher..." -ForegroundColor Yellow
Write-Host "Command: python janus_webrtc_client_windows.py --janus-url $janusUrl --room-id $roomId"
Write-Host "Press Enter to continue (start publisher in another terminal)..."
Read-Host

# Step 4: Start viewer
Write-Host "`n4. Starting viewer..." -ForegroundColor Yellow
Write-Host "Command: python janus_viewer_client_windows.py --janus-url $janusUrl --room-id $roomId"
Write-Host "Press Enter to continue (start viewer in another terminal)..."
Read-Host

Write-Host "`n=== Workflow Complete ===" -ForegroundColor Green
```

---

## Quick Reference

### Publisher (Send Camera)

```powershell
python janus_webrtc_client_windows.py `
    --janus-url http://localhost:8088/janus `
    --room-id 1234 `
    --camera-device 0
```

### Viewer (Receive Stream)

```powershell
python janus_viewer_client_windows.py `
    --janus-url http://localhost:8088/janus `
    --room-id 1234
```

### Test Camera

```powershell
gst-launch-1.0 dshowvideosrc device-index=0 ! videoconvert ! autovideosink
```

### Test Janus

```powershell
Invoke-RestMethod -Uri "http://localhost:8088/janus" `
    -Method Post -ContentType "application/json" `
    -Body '{"janus":"info","transaction":"test"}'
```

---

## Troubleshooting

### Camera Not Found

```powershell
# List cameras
gst-device-monitor-1.0 Video

# Try different device index
python janus_webrtc_client_windows.py --camera-device 1
```

### Janus Connection Failed

```powershell
# Test connectivity
Test-NetConnection -ComputerName localhost -Port 8088

# Try WSL IP instead of localhost
wsl hostname -I
# Use that IP in --janus-url
```

### GStreamer Not Found

```powershell
# Check PATH
$env:Path -split ';' | Select-String "gstreamer"

# Add to PATH if missing
$env:Path += ";C:\gstreamer\1.0\msvc_x86_64\bin"
```

---

## Network Notes

- **Windows 11**: Use `localhost` to access WSL
- **Windows 10**: May need WSL IP address
- **Port forwarding**: Usually automatic, but check firewall
- **Firewall**: May need to allow WSL through Windows Firewall
