# Complete Step-by-Step Workflow

## Terminal Setup

Open **5 terminals** for this workflow:

- **Terminal 1**: Janus Server
- **Terminal 2**: Janus API Testing
- **Terminal 3**: Camera Publisher (Python Client)
- **Terminal 4**: Verification/Monitoring
- **Terminal 5**: Viewer (Browser or another client)

---

## STEP 1: Test Camera with GStreamer

**Terminal 1:**

```bash
# List cameras
v4l2-ctl --list-devices

# Test camera (should open window)
gst-launch-1.0 v4l2src device=/dev/video0 ! \
    videoconvert ! \
    video/x-raw,width=640,height=480,framerate=30/1 ! \
    autovideosink
```

**Expected:** Camera window opens, video displays

**If fails:**
```bash
# Check permissions
ls -l /dev/video0
groups | grep video

# Add to video group
sudo usermod -a -G video $USER
# Log out and back in
```

---

## STEP 2: Start Janus Server

**Terminal 1:**

```bash
# Start Janus with debug logging
janus --configs-folder=/etc/janus --debug-level=7 --stderr 2>&1 | tee /tmp/janus.log
```

**Expected:** Janus starts, shows "JANUS WebRTC Server" and version

**Verify:**
```bash
# In another terminal, test API
curl http://localhost:8088/janus
```

**Expected Response:**
```json
{"janus":"success","transaction":"...","data":{"version_string":"..."}}
```

---

## STEP 3: Test Janus API Manually

**Terminal 2:**

```bash
# Run automated test
./test_janus_manual.sh

# OR manually:

# 3.1 Create session
SESSION_ID=$(curl -s -X POST http://localhost:8088/janus \
  -H "Content-Type: application/json" \
  -d '{"janus":"create","transaction":"test"}' | jq -r '.data.id')
echo "Session: $SESSION_ID"

# 3.2 Attach to VideoRoom plugin
HANDLE_ID=$(curl -s -X POST "http://localhost:8088/janus/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"janus":"attach","plugin":"janus.plugin.videoroom","transaction":"test2"}' \
  | jq -r '.data.id')
echo "Handle: $HANDLE_ID"

# 3.3 List rooms
curl -s -X POST "http://localhost:8088/janus/$SESSION_ID/$HANDLE_ID" \
  -H "Content-Type: application/json" \
  -d '{"janus":"message","transaction":"test3","body":{"request":"list"}}' \
  | jq '.plugindata.data.list'
```

**Expected:** Session and handle IDs are numbers, rooms list (may be empty)

---

## STEP 4: Start Camera Publisher

**Terminal 3:**

```bash
# Start Python client to stream camera
python3 janus_webrtc_client.py \
    --janus-url http://localhost:8088/janus \
    --room-id 1234 \
    --camera /dev/video0 \
    --width 640 \
    --height 480 \
    --fps 30
```

**Watch for these messages:**
```
✓ Created session: 1234567890
✓ Attached to plugin: 9876543210
✓ Joined room 1234
✓ SDP Offer created
✓ Received SDP answer from Janus
✓ Connection state: connected
✓ ICE connection state: connected
✓ Pipeline started, streaming camera feed...
```

**If you see errors:**
- "Failed to create session" → Check Janus is running (Terminal 1)
- "Failed to attach plugin" → Check VideoRoom plugin is enabled
- "Failed to join room" → Room might not exist (will be created automatically)
- "Failed to start pipeline" → Check camera permissions/device

---

## STEP 5: Verify Publisher is Active

**Terminal 4:**

```bash
# Get session and handle (from Terminal 2, or create new)
SESSION_ID=1234567890  # Replace with actual
HANDLE_ID=9876543210   # Replace with actual

# List participants in room 1234
curl -s -X POST "http://localhost:8088/janus/$SESSION_ID/$HANDLE_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "janus":"message",
    "transaction":"check",
    "body":{
      "request":"listparticipants",
      "room":1234
    }
  }' | jq '.plugindata.data.participants'
```

**Expected:** Should show your publisher:
```json
[
  {
    "id": 12345,
    "display": "Python Client",
    "publisher": true,
    "talking": false
  }
]
```

---

## STEP 6: View Stream (Browser)

**Terminal 5:**

```bash
# Find Janus HTML client
find /usr -name "videoroomtest.html" 2>/dev/null

# Or download from GitHub
# https://github.com/meetecho/janus-gateway/tree/master/html

# Serve HTML files
cd /path/to/janus/html
python3 -m http.server 8080
```

**Browser:**
1. Open: `http://localhost:8080/videoroomtest.html`
2. Enter room ID: `1234`
3. Click "Watch" or "Join"
4. Video should appear!

---

## STEP 7: Monitor Network Traffic

**Terminal 4 (new window):**

```bash
# Monitor UDP traffic (WebRTC uses UDP)
sudo tcpdump -i any -n udp portrange 10000-20000 -v

# You should see:
# - STUN packets (to stun.l.google.com)
# - RTP packets (video data)
# - DTLS packets (encryption)
```

**Expected:** Continuous UDP packets on ports 10000-20000

---

## STEP 8: Extract and View SDP

**Terminal 4:**

```bash
# Get SDP from Janus response (if you saved it)
cat janus_response.json | jq -r '.jsep.sdp'

# Or use the Python helper
python3 get_sdp_from_janus.py --example 2

# SDP will show:
# - v=0 (version)
# - o=... (origin)
# - m=video (media)
# - a=ice-ufrag (ICE username)
# - a=ice-pwd (ICE password)
# - a=fingerprint (DTLS)
# - a=candidate (ICE candidates)
```

---

## Complete Flow Summary

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: Test Camera                                          │
│   gst-launch-1.0 v4l2src ! autovideosink                     │
└─────────────────────────────────────────────────────────────┘
                          ✓
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: Start Janus                                          │
│   janus --configs-folder=/etc/janus                         │
└─────────────────────────────────────────────────────────────┘
                          ✓
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: Test Janus API                                       │
│   curl http://localhost:8088/janus                           │
│   Create session, attach plugin                              │
└─────────────────────────────────────────────────────────────┘
                          ✓
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 4: Start Publisher                                      │
│   python3 janus_webrtc_client.py --room-id 1234             │
│                                                              │
│   Flow:                                                      │
│   1. Create session → Janus                                  │
│   2. Attach plugin → Janus                                   │
│   3. Join room → Janus                                       │
│   4. GStreamer creates SDP offer                            │
│   5. Send offer → Janus                                      │
│   6. Receive SDP answer ← Janus                              │
│   7. Exchange ICE candidates (UDP)                           │
│   8. Stream RTP video (UDP)                                 │
└─────────────────────────────────────────────────────────────┘
                          ✓
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: Verify Publisher                                     │
│   curl ... listparticipants                                  │
└─────────────────────────────────────────────────────────────┘
                          ✓
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: View Stream                                          │
│   Browser: http://localhost:8080/videoroomtest.html          │
│   Room: 1234                                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Debugging Checklist

- [ ] Camera works: `gst-launch-1.0 v4l2src ! autovideosink`
- [ ] Janus running: `curl http://localhost:8088/janus`
- [ ] Can create session: API returns session ID
- [ ] Can attach plugin: API returns handle ID
- [ ] Can join room: API returns success
- [ ] Publisher shows in participants list
- [ ] SDP exchange happens (check logs)
- [ ] ICE connection established (check logs)
- [ ] UDP traffic visible (tcpdump)
- [ ] Viewer can connect (browser)

---

## Quick Test Script

Run this to test everything at once:

```bash
#!/bin/bash
# Quick test all components

echo "1. Testing camera..."
gst-launch-1.0 v4l2src device=/dev/video0 ! fakesink num-buffers=1 2>&1 | grep -q "Setting pipeline" && echo "✓ Camera OK" || echo "✗ Camera FAIL"

echo "2. Testing Janus..."
curl -s http://localhost:8088/janus | jq -e '.janus == "success"' > /dev/null && echo "✓ Janus OK" || echo "✗ Janus FAIL"

echo "3. Testing Python client..."
python3 -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst; Gst.init(None); print('✓ GStreamer OK')" || echo "✗ GStreamer FAIL"

echo "Done!"
```

---

## Next Steps After Success

1. **Adjust video quality**: Change `--width`, `--height`, `--fps`
2. **Add audio**: Modify pipeline to include audio source
3. **Multiple viewers**: Connect multiple browsers/clients
4. **Recording**: Use Janus recording plugin
5. **Production**: Configure TURN server for NAT traversal
