# Windows PowerShell + WSL Janus Setup Guide

Complete guide for streaming from Windows camera to Janus in WSL and viewing on Windows.

## Architecture

```
Windows PowerShell (Camera) → WSL Ubuntu (Janus) → Windows PowerShell (Viewer)
     GStreamer                    Janus Server          GStreamer
```

## Prerequisites

### Windows Side:
1. Install GStreamer for Windows
   - Download from: https://gstreamer.freedesktop.org/download/
   - Install: `gstreamer-1.0-msvc-x86_64-1.x.x.msi`
   - Add to PATH: `C:\gstreamer\1.0\msvc_x86_64\bin`

2. Verify installation:
```powershell
gst-launch-1.0 --version
gst-inspect-1.0 dshowvideosrc
```

### WSL Side:
1. Janus server installed and running
2. Python client dependencies installed

---

## Step 1: Start Janus in WSL

**WSL Terminal (Ubuntu):**

```bash
# Start Janus server
janus --configs-folder=/etc/janus --debug-level=7 --stderr

# Or if running as service
sudo systemctl start janus
```

**Get WSL IP address:**
```bash
# In WSL, get IP address
hostname -I | awk '{print $1}'
# Or
ip addr show eth0 | grep "inet " | awk '{print $2}' | cut -d/ -f1
```

**Note:** WSL IP changes on restart. For static IP, use `localhost` or configure WSL networking.

---

## Step 2: Test Janus from Windows

**Windows PowerShell:**

```powershell
# Test Janus API (replace with WSL IP if needed)
$wslIp = "localhost"  # Or use WSL IP from above
Invoke-RestMethod -Uri "http://$wslIp`:8088/janus" -Method Post -ContentType "application/json" -Body '{"janus":"info","transaction":"test"}'
```

---

## Step 3: Stream Camera from Windows to Janus

### Option A: Using GStreamer Command (PowerShell)

**Windows PowerShell:**

```powershell
# Set variables
$janusUrl = "http://localhost:8088/janus"  # Or WSL IP
$roomId = 1234
$cameraDevice = 0  # Usually 0 for first camera

# Note: This is a simplified example
# Full WebRTC requires SDP exchange (use Python client instead)
```

**For full WebRTC, use Python client (see below)**

### Option B: Using Python Client (Recommended)

**Windows PowerShell:**

```powershell
# Run Python publisher client
python janus_webrtc_client_windows.py `
    --janus-url http://localhost:8088/janus `
    --room-id 1234 `
    --camera-device 0
```

---

## Step 4: Receive Stream in Windows (GStreamer)

**Windows PowerShell:**

```powershell
# This requires SDP from Janus - see Python client below for full implementation
# Simplified example (requires manual SDP):

# After getting SDP answer from Janus, use it in GStreamer pipeline
# (Full example in Python client)
```

---

## Step 5: Python Client to Get Feed from Janus

See `janus_viewer_client_windows.py` below for complete implementation.

---

## Network Configuration

### WSL Networking Notes:

1. **From Windows to WSL:**
   - Use `localhost` (Windows 11) or WSL IP
   - Port forwarding is automatic in Windows 11

2. **From WSL to Windows:**
   - Use `localhost` or Windows host IP

3. **Find WSL IP:**
```powershell
# In PowerShell
wsl hostname -I
```

4. **Find Windows IP from WSL:**
```bash
# In WSL
cat /etc/resolv.conf | grep nameserver | awk '{print $2}'
```

---

## Troubleshooting

### Camera not found in Windows:
```powershell
# List DirectShow video sources
gst-device-monitor-1.0 Video
```

### Janus not accessible:
```powershell
# Test connectivity
Test-NetConnection -ComputerName localhost -Port 8088
```

### Firewall issues:
```powershell
# Allow WSL through firewall (if needed)
New-NetFirewallRule -DisplayName "WSL" -Direction Inbound -InterfaceAlias "vEthernet (WSL)" -Action Allow
```
