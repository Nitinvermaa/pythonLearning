# Quick Debug Commands Reference

## 1. Test Camera with GStreamer

```bash
# Simple test - display camera
gst-launch-1.0 v4l2src device=/dev/video0 ! videoconvert ! autovideosink

# Test with encoding
gst-launch-1.0 v4l2src device=/dev/video0 ! \
    videoconvert ! \
    video/x-raw,width=640,height=480,framerate=30/1,format=I420 ! \
    vp8enc target-bitrate=1000000 ! \
    webmmux ! filesink location=test.webm
```

## 2. Start Janus Server

```bash
# Start Janus
janus --configs-folder=/etc/janus --debug-level=7 --stderr

# Or as service
sudo systemctl start janus
sudo systemctl status janus
```

## 3. Verify Janus API

```bash
# Check if running
curl http://localhost:8088/janus

# Create session
curl -X POST http://localhost:8088/janus \
  -H "Content-Type: application/json" \
  -d '{"janus":"create","transaction":"test"}'
```

## 4. Feed Camera to Janus

```bash
# Run Python client
python3 janus_webrtc_client.py \
    --janus-url http://localhost:8088/janus \
    --room-id 1234 \
    --camera /dev/video0
```

## 5. View Stream (Browser)

```bash
# Start Janus HTML client server
cd /usr/share/janus/html
python3 -m http.server 8080

# Open browser: http://localhost:8080/videoroomtest.html
# Enter room: 1234
```

## 6. Manual API Testing

```bash
# Run automated test script
./test_janus_manual.sh

# Or step by step:
SESSION_ID=$(curl -s -X POST http://localhost:8088/janus \
  -H "Content-Type: application/json" \
  -d '{"janus":"create","transaction":"test"}' | jq -r '.data.id')

HANDLE_ID=$(curl -s -X POST "http://localhost:8088/janus/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d '{"janus":"attach","plugin":"janus.plugin.videoroom","transaction":"test2"}' \
  | jq -r '.data.id')

# Join room
curl -X POST "http://localhost:8088/janus/$SESSION_ID/$HANDLE_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "janus":"message",
    "transaction":"test3",
    "body":{"request":"join","ptype":"publisher","room":1234}
  }'
```

## 7. Check Participants

```bash
# List participants in room
curl -s -X POST "http://localhost:8088/janus/$SESSION_ID/$HANDLE_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "janus":"message",
    "transaction":"list",
    "body":{"request":"listparticipants","room":1234}
  }' | jq '.plugindata.data.participants'
```

## 8. Monitor Network (UDP/RTP)

```bash
# Monitor WebRTC UDP traffic
sudo tcpdump -i any -n udp portrange 10000-20000 -v

# Check listening ports
ss -tulnp | grep -E '8088|10000'
```

## 9. Debug Logs

```bash
# Janus logs
tail -f /tmp/janus.log
# Or
journalctl -u janus -f

# Python client with debug
python3 -c "
import logging
logging.basicConfig(level=logging.DEBUG)
exec(open('janus_webrtc_client.py').read())
" --janus-url http://localhost:8088/janus
```

## 10. Extract SDP from Response

```bash
# Get SDP from Janus response
RESPONSE=$(curl -s -X POST ...)
echo "$RESPONSE" | jq -r '.jsep.sdp'

# Save to file
echo "$RESPONSE" | jq -r '.jsep.sdp' > sdp_answer.txt
```

## Complete Flow Diagram

```
┌─────────────┐
│   Camera    │
│ /dev/video0 │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ GStreamer   │
│  Pipeline   │
│ (v4l2src →  │
│  vp8enc)    │
└──────┬──────┘
       │
       ▼
┌─────────────┐      SDP Offer      ┌─────────────┐
│  WebRTC     │ ──────────────────> │   Janus     │
│   Client    │                      │   Server    │
│             │ <──────────────────  │             │
└──────┬──────┘      SDP Answer      └──────┬──────┘
       │                                     │
       │                                     │
       │         ICE Candidates (UDP)        │
       │ <─────────────────────────────────> │
       │                                     │
       │         RTP Media (UDP)             │
       │ <─────────────────────────────────> │
       │                                     │
       ▼                                     ▼
```

## Janus API Endpoints

```
POST /janus                          → Create session
POST /janus/{session_id}              → Attach plugin
POST /janus/{session_id}/{handle_id} → Send message
GET  /janus/{session_id}/{handle_id} → Long poll events
```

## Common Issues & Fixes

```bash
# Camera not found
ls -l /dev/video*
sudo usermod -a -G video $USER

# Janus not responding
ps aux | grep janus
netstat -tlnp | grep 8088

# GStreamer plugin missing
gst-inspect-1.0 webrtcbin
sudo apt-get install gstreamer1.0-plugins-bad

# Permission denied
sudo chmod 666 /dev/video0
# Or add to video group (better)
```
